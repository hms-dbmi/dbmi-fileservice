from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group
from django.test import Client
from filemaster.models import Bucket, ArchiveFile

import json
from django.conf import settings

User = get_user_model()

userlist=['rootuser','poweruser','regularuser']
userlistemail=['rootuser@thebeatles.com','poweruser@thebeatles.com','regularuser@thebeatles.com']
groups_for_regular=['udntest__DOWNLOADERS','udntest__UPLOADERS','udntest__READERS','udntest__WRITERS']
fileuuid = None

HYPATIO_TOKEN='TEST1234'


# Permissions is the name of the group.
file_data = {
             "permissions":["hypatio_group"],
             "description": "This is a test file.",
             "metadata":
                 {
                     "filesize":"26",
                     "some_attribute": "stuff"
                 },
                "filename":"test2.txt",
                "tags":["tag1","tag5"]
            }


class ServiceConnectionTest(TestCase):
    def setUp(self):
        super(ServiceConnectionTest, self).setUp()

        bucket = Bucket(name="hypatio-test")
        bucket.save()

        print("[TEST][ServiceConnectionTest][setUp] - Create Hypatio Account")
        hypatio_user = User.objects.create_superuser('hypatio_account', 'hypatio_account', '')

        print("[TEST][ServiceConnectionTest][setUp] - Create Hypatio Groups")
        hypatio_group = Group.objects.create(name="hypatio_group__UPLOADERS")
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__DOWNLOADERS")
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__READERS")
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__WRITERS")
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__ADMINS")
        hypatio_user.groups.add(hypatio_group)

        settings.HYPATIO_FILESERVICE_TOKEN = HYPATIO_TOKEN

        self.file_uuid = None

    def test_wrong_token(self):
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'HYPATIO ' + 'TEST123'

        returned_post = c.post('/filemaster/groups/', data='{"name":"udntest","users":[]}',
                               content_type='application/json')

        self.assertEqual(returned_post.status_code, 403)

    def test_file(self):

        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'HYPATIO ' + HYPATIO_TOKEN
        res = c.post('/filemaster/api/file/', data=json.dumps(file_data),content_type='application/json')
        self.file_uuid = json.loads(res.content)["uuid"]
        self.assertEqual(res.status_code, 201)

        c.defaults['HTTP_AUTHORIZATION'] = 'HYPATIO ' + HYPATIO_TOKEN
        res = c.get('/filemaster/api/file/%s/' % self.file_uuid, content_type='application/json')
        self.assertEqual(res.status_code, 200)

        res = c.get('/filemaster/api/file/%s/download/' % self.file_uuid, content_type='application/json')
        self.assertEqual(res.status_code, 200)

