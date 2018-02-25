from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
import jwt,base64,requests,json
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import CustomUser

import logging
log = logging.getLogger(__name__)


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

        log.debug("[authenticate][Auth0Authentication][authenticate] - Starting authn.")

        auth = None
        user = None
        User = get_user_model()

        if 'HTTP_AUTHORIZATION' in request.META:
            log.debug("[authenticate][Auth0Authentication][authenticate] - HTTP_AUTHORIZATION Found in META.")
            authstring = request.META['HTTP_AUTHORIZATION']
            if authstring.startswith('JWT '):
                auth = authstring[4:]
            else:
                return None
        elif request.COOKIES.has_key( 'DBMI_JWT' ):
            log.debug("[authenticate][Auth0Authentication][authenticate] - DBMI_JWT.")
            auth = request.COOKIES[ 'DBMI_JWT' ]
        else:
            return None

        try:
            payload = jwt.decode(auth,
                                 base64.b64decode(settings.AUTH0_SECRET, '-_'),
                                 algorithms=['HS256'],
                                 audience=settings.AUTH0_CLIENT_ID)
        except jwt.ExpiredSignature:
            log.debug("[authenticate][Auth0Authentication][authenticate] - JWT Expired.")
            return None
        except jwt.DecodeError:
            log.debug("[authenticate][Auth0Authentication][authenticate] - JWT DecodeError.")
            return None
        except Exception as e:
            log.debug("[authenticate][Auth0Authentication][authenticate] - Other error %s" % e)

        log.debug("[authenticate][Auth0Authentication][authenticate] - JWT Valid.")

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

        log.debug("[authenticate][ServiceAuthentication][authenticate] - Starting authn.")

        if 'HTTP_AUTHORIZATION' in request.META:

            log.debug("[authenticate][ServiceAuthentication][authenticate] - HTTP_AUTHORIZATION.")

            authstring = request.META['HTTP_AUTHORIZATION']

            if authstring.startswith('HYPATIO '):
                auth = authstring[8:]
                if auth == settings.HYPATIO_TOKEN:
                    try:
                        service_user = CustomUser.objects.get(email="hypatio_account")
                        log.debug("[authenticate][ServiceAuthentication][authenticate] - Hypatio logged in.")
                        return (service_user, None)
                    except Exception, e:
                        log.debug("[authenticate][ServiceAuthentication][authenticate] - Error fetching service user."
                                  "%s" % e)
                else:
                    return None
        else:
            return None