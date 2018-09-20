from django.test import TestCase
from filemaster.models import ArchiveFile,Bucket
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from rest_framework.authtoken.models import Token
from django.test import Client
from django.test.utils import override_settings
from django.core.management import call_command
import json,uuid,requests,urllib.request,urllib.parse,urllib.error
from guardian.shortcuts import get_objects_for_user
from boto.s3.connection import S3Connection
from django.conf import settings

User = get_user_model()        

userlist=['rootuser','poweruser','regularuser']
userlistemail=['rootuser@thebeatles.com','poweruser@thebeatles.com','regularuser@thebeatles.com']
groups_for_regular=['udntest__DOWNLOADERS','udntest__UPLOADERS','udntest__READERS','udntest__WRITERS']
fileuuid = None


class ArchiveFileTest(TestCase):
    fileuuid=None
    aws_key=settings.TEST_AWS_KEY
    aws_secret=settings.TEST_AWS_SECRET
    c = Client()

    def setUp(self):
        print("setup")
        super(ArchiveFileTest, self).setUp()
        User = get_user_model()
        User.objects.create_superuser('rootuser', 'rootuser@thebeatles.com', 'password')
        poweruser = User.objects.create_user('poweruser', 'poweruser@thebeatles.com', 'password')
        User.objects.create_user('regularuser', 'regularuser@thebeatles.com', 'password')
        User.objects.create_user('denyuser', 'denyuser@thebeatles.com', 'password')
        add_group_permission = Permission.objects.get(codename='add_group')
        bucket=Bucket(name="cbmi-fileservice-test")
        bucket.save()
        poweruser.user_permissions.add(add_group_permission)

        r = add_user_group(success=True)
        t = get_token('poweruser@thebeatles.com')

        #add regular user to groups
        
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        for g in groups_for_regular:
            gr = Group.objects.get(name=g)
            res = self.c.put('/filemaster/groups/%s/' % gr.id, data='{"users":[{"email":"regularuser@thebeatles.com"}],"buckets":[{"name":"cbmi-fileservice-test"}]}',content_type='application/json')
            self.assertEqual(res.status_code, 200)

        for g in groups_for_regular:
            gr = Group.objects.get(name=g)
            res = self.c.put('/filemaster/groups/%s/' % gr.name, data='{"users":[{"email":"regularuser@thebeatles.com"}],"buckets":[{"name":"cbmi-fileservice-test"}]}',content_type='application/json')
            self.assertEqual(res.status_code, 200)


        u = User.objects.get(email='rootuser@thebeatles.com')
        t = Token.objects.get(user=u)
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = c.post('/filemaster/user/', data='{"users":["test@test.com"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
                        

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

        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        j = json.loads(res.content)["uuid"]
        self.assertTrue(uuid.UUID(j).hex)
        
        t = get_token('denyuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 404)

        t = get_token('regularuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 200)

        
        t = get_token('denyuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.patch('/filemaster/api/file/%s/' % j, data='{"tags":["test4444"]}',content_type='application/json')
        self.assertEqual(res.status_code, 404)

        t = get_token('regularuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.patch('/filemaster/api/file/%s/' % j, data='{"tags":["test4444"]}',content_type='application/json')
        self.assertEqual(res.status_code, 200)

        t = get_token('regularuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.get('/filemaster/api/file/%s/' % j, content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"test4444",status_code=200)

    def test_e_add_user_to_group_and_file_and_s3(self):
        t = get_token('poweruser@thebeatles.com')

        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.post('/filemaster/api/file/', data='{"expirationdate":"2020-10-5","permissions":["udntest"],"description":"this is a long description","metadata":{"coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2","tag3"]}',content_type='application/json')
        j = json.loads(res.content)["uuid"]
        
        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.parse.quote(self.aws_secret,''))
        res = self.c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)
        url = json.loads(res.content)["url"]
        locationid = json.loads(res.content)["locationid"]
        
        res = requests.put(url,data=open('test2.txt'))
        
        self.assertEqual(res.status_code, 200)
        url = '/filemaster/api/file/%s/uploadcomplete/?location=%s&aws_key=%s&aws_secret=%s' % (j,locationid,self.aws_key,urllib.parse.quote(self.aws_secret,''))
        res = self.c.get(url,content_type='application/json')

        url = '/filemaster/api/file/%s/' % (j)
        res = self.c.get(url,content_type='application/json')

        #get link and upload file
        
        #then download
        url = '/filemaster/api/file/%s/download/?aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.parse.quote(self.aws_secret,''))
        res = self.c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)

        #then destroy
        cleanup_bucket(self.aws_key, self.aws_secret)

    def test_f_denyuser(self):
        t = get_token('regularuser@thebeatles.com')

        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag2","tag4"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        j = json.loads(res.content)["uuid"]
        call_command('rebuild_index', interactive=False, verbosity=1)
        
        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.parse.quote(self.aws_secret,''))
        res = self.c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 200)
        url = json.loads(res.content)["url"]

        t = get_token('denyuser@thebeatles.com')
        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t

        url = '/filemaster/api/file/%s/upload/?bucket=cbmi-fileservice-test&aws_key=%s&aws_secret=%s' % (j,self.aws_key,urllib.parse.quote(self.aws_secret,''))
        res = self.c.get(url,content_type='application/json')
        self.assertEqual(res.status_code, 403)
        cleanup_bucket(self.aws_key, self.aws_secret)

    def test_g_listfile(self):
        t = get_token('regularuser@thebeatles.com')

        self.c.defaults['HTTP_AUTHORIZATION'] = 'Token %s' % t
        res = self.c.post('/filemaster/api/file/', data='{"permissions":["udntest"],"description":"this is a long description","metadata":{"filesize":"26","coverage":"30","patientid":"1234-123-123-123","otherinfo":"info"},"filename":"test2.txt","tags":["tag1","tag5"]}',content_type='application/json')
        self.assertEqual(res.status_code, 201)
        call_command('rebuild_index', interactive=False, verbosity=1)

        url = '/filemaster/api/file/' % ()
        res = self.c.get(url,{"filename":"test2.txt"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res,"udntest",status_code=200)

        #test filter
        url = '/filemaster/api/file/' % ()
        res = self.c.get(url,{"min_creationdate":"2000-05-07"},content_type='application/json')
        self.assertContains(res,"patientid",status_code=200)
        self.assertEqual(res.status_code, 200)

        #test filter with no response
        url = '/filemaster/api/file/' % ()
        res = self.c.get(url,{"max_creationdate":"2000-05-07"},content_type='application/json')
        self.assertEqual(res.content,"[]")

        
        url = '/filemaster/api/file/' % ()
        res = self.c.get(url,{"filename":"asdfasdfdsafdsafas.txt"},content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content,"[]")
    
    def tearDown(self):
        print("Tear Down")
        #call_command('clear_index', interactive=False, verbosity=1)
        
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
    