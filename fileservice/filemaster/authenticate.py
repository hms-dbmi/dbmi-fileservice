from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
import jwt,base64,requests,json
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

        if 'HTTP_AUTHORIZATION' in request.META: 
            authstring = request.META['HTTP_AUTHORIZATION']
            if authstring.startswith('JWT '):
                auth = authstring[4:]
            else: 
                return None
        elif request.COOKIES.has_key( 'Authorization' ):
            auth = request.COOKIES[ 'Authorization' ]
        else:
            return None
        
        try:
            payload = jwt.decode(
                                 auth,
                                 #key=base64.b64decode(settings.AUTH0_CLIENT_SECRET.replace("_","/").replace("-","+")),
                                 key=settings.AUTH0_CLIENT_SECRET,
                                 audience=settings.AUTH0_CLIENT_ID,
                leeway=10
        )
        except jwt.ExpiredSignature:
            print "Expired"
            return None
        except jwt.DecodeError:
            print "bad decode"
            return None        
        
        
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
    
 