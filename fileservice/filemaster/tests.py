from django.test import TestCase
from filemaster.models import ArchiveFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from rest_framework.authtoken.models import Token
from django.test import Client
from django.test.utils import override_settings
import haystack 
from django.core.management import call_command
import json,uuid,requests,urllib
from guardian.shortcuts import get_objects_for_user
from boto.s3.connection import S3Connection


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
    aws_key="AKIAJTRKJN7J2V3FBK5Q"
    aws_secret="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"

    def setUp(self):
        haystack.connections.reload('default')
        User = get_user_model()
        rootuser = User.objects.create_superuser('rootuser', 'rootuser@thebeatles.com', 'password')        
        poweruser = User.objects.create_user('poweruser', 'poweruser@thebeatles.com', 'password')
        regularuser = User.objects.create_user('regularuser', 'regularuser@thebeatles.com', 'password')
        denyuser = User.objects.create_user('denyuser', 'denyuser@thebeatles.com', 'password')
        add_group_permission = Permission.objects.get(codename='add_group')
        poweruser.user_permissions.add(add_group_permission)

        r = add_user_group(success=True)
        t = get_token('poweruser@thebeatles.com')

        #add regular user to groups
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        for g in groups_for_regular:
            gr = Group.objects.get(name=g)
            res = c.put('/filemaster/groups/%s/' % gr.id, data='{"users":[{"email":"regularuser@thebeatles.com"}]}',content_type='application/json')
            self.assertEqual(res.status_code, 200)
                        

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
        t = get_token('poweruser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        j = json.loads(res.content)["uuid"]
        
        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.quote(self.aws_secret,''))
        res = c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)
        url = json.loads(res.content)["url"]
        
        res = requests.put(url,data=open('test2.txt'))
        self.assertEqual(res.status_code, 200)
        #get link and upload file
        
        #then download
        url = '/filemaster/api/file/%s/download/?aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.quote(self.aws_secret,''))
        res = c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)

        #then destroy
        cleanup_bucket(self.aws_key, self.aws_secret)

    def test_f_denyuser(self):
        t = get_token('regularuser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        j = json.loads(res.content)["uuid"]
        
        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.quote(self.aws_secret,''))
        res = c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)
        url = json.loads(res.content)["url"]

        t = get_token('denyuser@thebeatles.com')

        c = Client()
        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.quote(self.aws_secret,''))
        res = c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 403)
        cleanup_bucket(self.aws_key, self.aws_secret)

    def test_g_listfile(self):
        t = get_token('regularuser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)

        url = '/filemaster/api/file/' % ()
        res = c.get(url,{"filename":"test2.txt"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"udntest",status_code=200)

        #test filter
        url = '/filemaster/api/file/' % ()
        res = c.get(url,{"min_creationdate":"2000-05-07"},content_type='application/json')
        self.assertContains(res,"patientid",status_code=200)
        self.assertEqual(res.status_code, 200)

        #test filter with no response
        url = '/filemaster/api/file/' % ()
        res = c.get(url,{"max_creationdate":"2000-05-07"},content_type='application/json')
        self.assertEqual(res.content,"[]")

        
        url = '/filemaster/api/file/' % ()
        res = c.get(url,{"filename":"asdfasdfdsafdsafas.txt"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content,"[]")

    def test_h_searchfile(self):
        t = get_token('regularuser@thebeatles.com')

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)

        url = '/filemaster/api/search/' % ()
        res = c.get(url,{"q":"test2","fields":"filename"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"test2.txt",status_code=200)

        url = '/filemaster/api/search/' % ()
        res = c.get(url,{"q":"description","fields":"description"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"test2.txt",status_code=200)

        url = '/filemaster/api/search/' % ()
        res = c.get(url,{"q":"test2"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"test2.txt",status_code=200)

        url = '/filemaster/api/search/' % ()
        res = c.get(url,{"q":"test2","fields":"uuid"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content,"[]")

        url = '/filemaster/api/search/' % ()
        res = c.get(url,{"q":"testasdfasdfasdfa","fields":"filename"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content,"[]")


    
    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)

def cleanup_bucket(aws_key,aws_secret):
            #then destroy
        import boto
        conn = boto.connect_s3(aws_key,aws_secret)
        full_bucket = conn.get_bucket('cbmi-fileservice-test')
        for key in full_bucket.list():
            key.delete()                        

            
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
    