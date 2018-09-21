import jwt
import requests
import json
import jwcrypto.jwk as jwk

from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
from django.contrib.auth import get_user_model

from filemaster.models import CustomUser


import logging
log = logging.getLogger(__name__)


def get_public_keys_from_auth0():
    jwks_return = requests.get("https://" + settings.AUTH0_DOMAIN + "/.well-known/jwks.json")
    jwks = jwks_return.json()

    return jwks


def retrieve_public_key(jwt_string):

    jwks = get_public_keys_from_auth0()

    unverified_header = jwt.get_unverified_header(str(jwt_string))

    rsa_key = {}

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }

    return rsa_key


class Auth0Authentication(authentication.BaseAuthentication):
    def authenticate(self, request):

        auth = None
        user = None
        User = get_user_model()

        if 'HTTP_AUTHORIZATION' in request.META:
            log.debug("HTTP_AUTHORIZATION Found in META.")
            authstring = request.META['HTTP_AUTHORIZATION']
            if authstring.startswith('JWT '):
                auth = authstring[4:]
            else:
                return None
        elif 'DBMI_JWT' in request.COOKIES:
            log.debug("DBMI_JWT")
            auth = request.COOKIES[ 'DBMI_JWT' ]
        else:
            return None

        rsa_pub_key = retrieve_public_key(auth)
        payload = None
        jwk_key = jwk.JWK(**rsa_pub_key)

        try:
            payload = jwt.decode(auth,
                                 jwk_key.export_to_pem(private_key=False),
                                 algorithms=['RS256'],
                                 leeway=120,
                                 audience=settings.AUTH0_CLIENT_ID)
        except jwt.ExpiredSignature:
            log.debug("JWT Expired.")
            return None
        except jwt.DecodeError:
            log.debug("JWT DecodeError.")
            return None
        except Exception as e:
            log.debug("Other error %s" % e)

        log.debug("JWT Valid.")

        try:
            try:
                user = User.objects.get(email=payload["email"])
            except:
                headers = {"Content-Type": "application/json"}
                r = requests.post("https://%s/tokeninfo" %
                                  (settings.AUTH0_DOMAIN),
                                  headers=headers,
                                  data=json.dumps({"id_token":auth}))
                user = User.objects.get(email=r.json()["email"])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')
        except Exception as e:
            log.error("error %s" % e)

        return (user, None)   


class ServiceAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        log.debug("Starting service auth")

        if 'HTTP_AUTHORIZATION' in request.META:
            log.debug("HTTP_AUTHORIZATION.")

            # Get the token
            auth_string = request.META['HTTP_AUTHORIZATION']
            if auth_string.startswith('SERVICE '):
                log.debug('Service account...')

                # Get the token
                auth_token = auth_string[8:]

                # Get the service accounts
                for account, token in settings.SERVICE_ACCOUNTS.items():

                    # Compare tokens
                    if token == auth_token:
                        log.debug("Service account matched: {}".format(account))

                        try:
                            service_user = CustomUser.objects.get(email=account)
                            log.debug("{} logged in.".format(account))
                            return service_user, None

                        except Exception as e:
                            log.debug("Error fetching service user: {}".format(e))

                log.warning('Service account not found')
                return None
            else:
                return None
        else:
            return None