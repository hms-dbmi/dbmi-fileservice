from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
import jwt,base64
from django.conf import settings
from django.contrib.auth import get_user_model


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
        auth = None
        user = None
        User = get_user_model()        
        if request.COOKIES.has_key( 'Authorization' ):
            auth = request.COOKIES[ 'Authorization' ]
        else:
            return None        
        try:
            payload = jwt.decode(
                                 auth,
                                 base64.b64decode(settings.AUTH0_CLIENT_SECRET.replace("_","/").replace("-","+"))
        )
        except jwt.ExpiredSignature:
            return None
        except jwt.DecodeError:
            return None        
        
        try:
            user = User.objects.get(email=payload["email"])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')
        except Exception,e:
            print "error %s" % e

        return (user, None)    