from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
import jwt,base64,requests,json
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import CustomUser

import logging
logger = logging.getLogger(__name__)


class ExampleAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        username = request.META.get('HTTP_X_USERNAME')
        if not username:
            return None
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        return (user, None)
    
class Auth0Authentication(authentication.BaseAuthentication):
    def authenticate(self, request):

        logger.debug("[authenticate][Auth0Authentication][authenticate] - Starting authn.")

        auth = None
        user = None
        User = get_user_model()

        if 'HTTP_AUTHORIZATION' in request.META:
            logger.debug("[authenticate][Auth0Authentication][authenticate] - HTTP_AUTHORIZATION Found in META.")
            authstring = request.META['HTTP_AUTHORIZATION']
            if authstring.startswith('JWT '):
                auth = authstring[4:]
            else:
                return None
        elif request.COOKIES.has_key( 'DBMI_JWT' ):
            logger.debug("[authenticate][Auth0Authentication][authenticate] - DBMI_JWT.")
            auth = request.COOKIES[ 'DBMI_JWT' ]
        else:
            return None

        try:
            payload = jwt.decode(auth,
                                 base64.b64decode(settings.AUTH0_SECRET, '-_'),
                                 algorithms=['HS256'],
                                 audience=settings.AUTH0_CLIENT_ID)
        except jwt.ExpiredSignature:
            logger.debug("[authenticate][Auth0Authentication][authenticate] - JWT Expired.")
            return None
        except jwt.DecodeError:
            logger.debug("[authenticate][Auth0Authentication][authenticate] - JWT DecodeError.")
            return None
        except Exception as e:
            logger.debug("[authenticate][Auth0Authentication][authenticate] - Other error %s" % e)

        logger.debug("[authenticate][Auth0Authentication][authenticate] - JWT Valid.")

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
        except Exception,e:
            print "error %s" % e

        return (user, None)   


class ServiceAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        logger.debug("Starting service auth")

        if 'HTTP_AUTHORIZATION' in request.META:
            logger.debug("HTTP_AUTHORIZATION.")

            # Get the token
            auth_string = request.META['HTTP_AUTHORIZATION']
            if auth_string.startswith('SERVICE '):
                logger.debug('Service account...')

                # Get the token
                auth_token = auth_string[8:]

                # Get the service accounts
                for account, token in settings.SERVICE_ACCOUNTS.iteritems():

                    # Compare tokens
                    if token == auth_token:
                        logger.debug("Service account matched: {}".format(account))

                        try:
                            service_user = CustomUser.objects.get(email=account)
                            logger.debug("{} logged in.".format(account))
                            return service_user, None

                        except Exception, e:
                            logger.debug("Error fetching service user: {}".format(e))

                logger.warning('Service account not found')
                return None
            else:
                return None
        else:
            return None