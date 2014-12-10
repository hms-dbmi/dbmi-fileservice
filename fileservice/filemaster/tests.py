from django.test import TestCase
from filemaster.models import ArchiveFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from rest_framework.authtoken.models import Token
from django.test import Client
from django.test.utils import override_settings
import haystack 
from django.core.management import call_command
import json,uuid
from guardian.shortcuts import get_objects_for_user


User = get_user_model()        

userlist=['rootuser','poweruser','regularuser']
userlistemail=['rootuser@thebeatles.com','poweruser@thebeatles.com','regularuser@thebeatles.com']
groups_for_regular=['udntest__DOWNLOADERS','udntest__UPLOADERS','udntest__READERS','udntest__WRITERS']
fileuuid = None

TEST_INDEX = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'TIMEOUT': 60 * 10,
        'INDEX_NAME': 'test_index',
    },
}

@override_settings(HAYSTACK_CONNECTIONS=TEST_INDEX)
class ArchiveFileTest(TestCase):
    fileuuid=None
    def setUp(self):
        haystack.connections.reload('default')
        User = get_user_model()
        rootuser = User.objects.create_superuser('rootuser', 'rootuser@thebeatles.com', 'password')        
        poweruser = User.objects.create_user('poweruser', 'poweruser@thebeatles.com', 'password')
        regularuser = User.objects.create_user('regularuser', 'regularuser@thebeatles.com', 'password')
        denyuser = User.objects.create_user('denyuser', 'denyuser@thebeatles.com', 'password')
        add_group_permission = Permission.objects.get(codename='add_group')
        poweruser.user_permissions.add(add_group_permission)
                        

    def test_a_user_tokens(self):
        for email in userlistemail:
            u = User.objects.get(email=email)
            t = Token.objects.get(user=u)
            self.assertTrue(t)
    
    def test_b_add_group_success(self):
        response = add_user_group(success=True)
        self.assertContains(response,"udntest__ADMINS",status_code=201)

    def test_c_add_group_failure(self):
        response = add_user_group(success=False)
        self.assertEqual(response.status_code, 403)
        
    def test_d_add_user_to_group_and_file(self):
        r = add_user_group(success=True)
        t = get_token('poweruser@thebeatles.com')

        #add regular user to groups
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        for g in groups_for_regular:
            gr = Group.objects.get(name=g)
            res = c.put('/filemaster/groups/%s/' % gr.id, data='{"users":[{"email":"regularuser@thebeatles.com"}]}',content_type='application/json')
            self.assertEqual(res.status_code, 200)

        r = add_user_group(success=True)
        t = get_token('regularuser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        j = json.loads(res.content)["uuid"]
        self.assertTrue(uuid.UUID(j).hex)
        
        t = get_token('denyuser@thebeatles.com')
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 404)

        t = get_token('regularuser@thebeatles.com')
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 200)

        
        t = get_token('denyuser@thebeatles.com')
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.patch('/filemaster/api/file/%s/' % j, data='{"tags":["test4444"]}',content_type='application/json')
        self.assertEqual(res.status_code, 404)

        t = get_token('regularuser@thebeatles.com')
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.patch('/filemaster/api/file/%s/' % j, data='{"tags":["test4444"]}',content_type='application/json')
        self.assertEqual(res.status_code, 200)

        t = get_token('regularuser@thebeatles.com')
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"test4444",status_code=200)

    def test_e_add_user_to_group_and_file_and_s3(self):
        r = add_user_group(success=True)
        t = get_token('poweruser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        j = json.loads(res.content)["uuid"]
        self.assertTrue(uuid.UUID(j).hex)

        res = c.get('/filemaster/api/file/%s/upload/?bucket=testbucket' % j,content_type='application/json')
        print res
        #get link and upload file
        #then download
        #then destroy
                        
    
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)
        #s3 cleanup

def get_token(email):
    u = User.objects.get(email=email)
    return Token.objects.get(user=u)

def add_user_group(success=True):
    u = User.objects.get(email='poweruser@thebeatles.com')
    if success:
        t = Token.objects.get(user=u)
    else:
        t="asdfasdfasfsdaf"
    c = Client()
    c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
    return  c.post('/filemaster/groups/', data='{"name":"udntest","users":[]}',content_type='application/json')
    