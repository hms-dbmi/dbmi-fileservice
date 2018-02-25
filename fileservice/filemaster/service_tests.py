from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, Permission
from django.test import Client
from filemaster.models import Bucket
from guardian.shortcuts import assign_perm
import json

User = get_user_model()

userlist=['rootuser','poweruser','regularuser']
userlistemail=['rootuser@thebeatles.com','poweruser@thebeatles.com','regularuser@thebeatles.com']
groups_for_regular=['udntest__DOWNLOADERS','udntest__UPLOADERS','udntest__READERS','udntest__WRITERS']
fileuuid = None

HYPATIO_TOKEN='HYPATIO TEST1234'

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

        print("[TEST][ServiceConnectionTest][setUp] - Create Hypatio Group")
        hypatio_group = Group.objects.create(name="hypatio_group__UPLOADERS")
        assign_perm('filemaster.write_bucket', hypatio_group, bucket)
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__DOWNLOADERS")
        assign_perm('filemaster.write_bucket', hypatio_group, bucket)
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__READERS")
        assign_perm('filemaster.write_bucket', hypatio_group, bucket)
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__WRITERS")
        assign_perm('filemaster.write_bucket', hypatio_group, bucket)
        hypatio_user.groups.add(hypatio_group)

        hypatio_group = Group.objects.create(name="hypatio_group__ADMINS")
        assign_perm('filemaster.write_bucket', hypatio_group, bucket)
        hypatio_user.groups.add(hypatio_group)

        # Enable bucket for group.

    def test_wrong_token(self):
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = 'HYPATIO TEST123'

        returned_post = c.post('/filemaster/groups/', data='{"name":"udntest","users":[]}',
                               content_type='application/json')

        self.assertEqual(returned_post.status_code, 403)

    def test_register_file(self):
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = HYPATIO_TOKEN
        res = c.post('/filemaster/api/file/', data=json.dumps(file_data),content_type='application/json')
        self.file_uuid = json.loads(res.content)["uuid"]
        self.assertEqual(res.status_code, 201)

    def test_list_file(self):
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = HYPATIO_TOKEN

    def test_download_url(self):
        c = Client()
        c.defaults['HTTP_AUTHORIZATION'] = HYPATIO_TOKEN

        # returned_post = c.post('/filemaster/groups/', data='{"name":"udntest","users":[]}', content_type='application/json')

        # self.assertEqual(returned_post.status_code, 200)
