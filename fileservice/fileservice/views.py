from django.shortcuts import render
from django.db import models
from django.http import Http404,HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import logout,authenticate, login
from django.contrib.sites.models import Site
from django.core.files.storage import default_storage

from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib.admin.sites import site
from django.template import RequestContext, loader
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

import jwt,base64

import requests,json
import random,string


def id_generator(size=18, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

#auth0 callback
def callback(request):
    code = request.GET.get('code')
    
    json_header = {'content-type': 'application/json'}
    token_url = "https://{domain}/oauth/token".format(domain=settings.AUTH0_DOMAIN)
    
    token_payload = {
        'client_id' : settings.AUTH0_CLIENT_ID, 
        'client_secret' : settings.AUTH0_CLIENT_SECRET, 
        'redirect_uri' : settings.AUTH0_CALLBACK_URL, 
        'code' : str(code), 
        'grant_type': 'authorization_code' 
    }
    
    token_info = requests.post(token_url, data=json.dumps(token_payload), headers = json_header).json()

    user_url = "https://{domain}/userinfo?access_token={access_token}".format(domain=settings.AUTH0_DOMAIN, access_token=token_info['access_token'])
    
    user_info = requests.get(user_url).json()

    try:
        User = get_user_model()
        User.objects.create_user(id_generator(16), email=user_info["email"], password=id_generator(16))
    except Exception,e:
        print "ERROR %s" % e
        pass
    
    #response = HttpResponse(json.dumps(user_info), content_type="application/json")
    response = redirect('/filemaster/api/')
    response.set_cookie( 'Authorization', token_info["id_token"] )
        
    return response
