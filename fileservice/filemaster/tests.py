import json
import boto3
import io
from datetime import datetime
from datetime import timedelta

from mock import patch
from moto import mock_s3
from moto import mock_s3_deprecated # Needed until boto library is removed

from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_perms

from rest_framework.authtoken.models import Token

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.test import override_settings
from django.test import TestCase

from filemaster.models import ArchiveFile
from filemaster.models import Bucket
from filemaster.models import DownloadLog

# The super user account represents an application (like UDN or Hypatio) that is
# accessing fileservice and can do anything.
SUPERUSER_USERNAME = 'root_user'
SUPERUSER_EMAIL = 'root_user@example.com'

NOPERMISSIONS_USER_USERNAME = 'noperms_user'
NOPERMISSIONS_USER_EMAIL = 'noperms_user@example.com'

READONLY_USER_USERNAME = 'readonly_user'
READONLY_USER_EMAIL = 'readyonly_user@example.com'

WRITEONLY_USER_USERNAME = 'writeonly_user'
WRITEONLY_USER_EMAIL = 'writeonly_user@example.com'

READ_AND_WRITE_USER_USERNAME = 'readandwrite_user'
READ_AND_WRITE_USER_EMAIL = 'readandwrite_user@example.com'

EVERYTHING_BUT_ADMIN_USER = 'everythingbutadmin_user'
EVERYTHING_BUT_ADMIN_EMAIL = 'everythingbutadmin_user@example.com'

ALLOWED_BUCKET_NAME = 'allowedbucket'
BLOCKED_BUCKET_NAME = 'blockedbucket'

GROUP_PREFIX = 'test'
ADMIN_GROUP = GROUP_PREFIX + '__ADMINS'
DOWNLOADERS_GROUP = GROUP_PREFIX + '__DOWNLOADERS'
UPLOADERS_GROUP = GROUP_PREFIX + '__UPLOADERS'
READERS_GROUP = GROUP_PREFIX + '__READERS'
WRITERS_GROUP = GROUP_PREFIX + '__WRITERS'
GROUPS = [DOWNLOADERS_GROUP, UPLOADERS_GROUP, READERS_GROUP, WRITERS_GROUP, ADMIN_GROUP]

ACCESSIBLE_FILE_NAME = "accessible-file.pdf"

FILE_INSIDE_GROUP_INFO = {
    "permissions": [GROUP_PREFIX],
    "description": "This is a test file.",
    "metadata": {
        "filesize": "26",
        "some_attribute": "stuff"
    },
    "filename": ACCESSIBLE_FILE_NAME,
    "tags":["tag1", "tag5"]
}


INACCESSIBLE_FILE_NAME = "inaccessible-file.pdf"

FILE_OUTSIDE_GROUP_INFO = {
    "permissions": [],
    "description": "This is a test file that non-superusers should not be able to access.",
    "metadata": {
        "filesize": "99",
        "some_attribute": "stuff"
    },
    "filename": INACCESSIBLE_FILE_NAME,
    "tags":["tag1", "tag5"]
}

FAKE_AWS_KEY_ID = 'xxx'
FAKE_AWS_SECRET = 'yyy'

# To override the django settings variable where we define the buckets we accept.
BUCKETS_SETTING = {
    ALLOWED_BUCKET_NAME: {
        'type': 's3',
        'glaciertype': 'lifecycle',
        'AWS_KEY_ID': FAKE_AWS_KEY_ID,
        'AWS_SECRET': FAKE_AWS_SECRET
    }, 
    BLOCKED_BUCKET_NAME: {
        'type': 's3',
        'glaciertype': 'lifecycle',
        'AWS_KEY_ID': FAKE_AWS_KEY_ID,
        'AWS_SECRET': FAKE_AWS_SECRET
    }
}

# Create some fake classes to later mock STS calls.
class FakeStsCredentials():
    def __init__(self, access_key, secret_key, session_token):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token

class FakeStsFederationToken():
    def __init__(self, credentials):
        self.credentials = credentials


@mock_s3_deprecated
@mock_s3
class FileserviceTests(TestCase):

    noperms_user = None
    noperms_user_token = None

    readonly_user = None
    readonly_user_token = None

    writeonly_user = None
    writeonly_user_token = None

    read_and_write_user = None
    read_and_write_user_token = None

    everything_but_admin_user = None
    everything_but_admin_user_token = None

    super_user = None
    super_user_token = None

    readers_group = None
    writers_group = None
    downloaders_group = None
    uploaders_group = None

    allowed_bucket = None
    blocked_bucket = None

    accessible_file_uuid = None
    inaccessible_file_uuid = None

    fake_federation_token = None

    def setUp(self):

        User = get_user_model()

        # Create some buckets.
        self.allowed_bucket = Bucket.objects.create(name=ALLOWED_BUCKET_NAME)
        self.blocked_bucket = Bucket.objects.create(name=BLOCKED_BUCKET_NAME)

        # Create some users.
        self.super_user = User.objects.create_superuser(SUPERUSER_USERNAME, SUPERUSER_EMAIL, 'password')
        self.noperms_user = User.objects.create_user(NOPERMISSIONS_USER_USERNAME, NOPERMISSIONS_USER_EMAIL, 'password')
        self.readonly_user = User.objects.create_user(READONLY_USER_USERNAME, READONLY_USER_EMAIL, 'password')
        self.writeonly_user = User.objects.create_user(WRITEONLY_USER_USERNAME, WRITEONLY_USER_EMAIL, 'password')
        self.read_and_write_user = User.objects.create_user(READ_AND_WRITE_USER_USERNAME, READ_AND_WRITE_USER_EMAIL, 'password')
        self.everything_but_admin_user = User.objects.create_user(EVERYTHING_BUT_ADMIN_USER, EVERYTHING_BUT_ADMIN_EMAIL, 'password')

        # Grab their tokens for later.
        self.super_user_token = Token.objects.get(user=self.super_user)
        self.noperms_user_token = Token.objects.get(user=self.noperms_user)
        self.readonly_user_token = Token.objects.get(user=self.readonly_user)
        self.writeonly_user_token = Token.objects.get(user=self.writeonly_user)
        self.read_and_write_user_token = Token.objects.get(user=self.read_and_write_user)
        self.everything_but_admin_user_token = Token.objects.get(user=self.everything_but_admin_user)

        # Create the groups.
        for group in GROUPS:
            Group.objects.create(name=group)

        self.readers_group = Group.objects.get(name=READERS_GROUP)
        self.writers_group = Group.objects.get(name=WRITERS_GROUP)
        self.downloaders_group = Group.objects.get(name=DOWNLOADERS_GROUP)
        self.uploaders_group = Group.objects.get(name=UPLOADERS_GROUP)

        # Add users to the appropriate groups.
        self.readonly_user.groups.add(self.readers_group)
        self.writeonly_user.groups.add(self.writers_group)
        self.read_and_write_user.groups.add(self.readers_group)
        self.read_and_write_user.groups.add(self.writers_group)
        self.everything_but_admin_user.groups.add(self.readers_group)
        self.everything_but_admin_user.groups.add(self.writers_group)
        self.everything_but_admin_user.groups.add(self.downloaders_group)
        self.everything_but_admin_user.groups.add(self.uploaders_group)

        # Assign write bucket permissions for the groups.
        assign_perm('filemaster.write_bucket', self.readers_group, self.allowed_bucket)
        assign_perm('filemaster.write_bucket', self.writers_group, self.allowed_bucket)
        assign_perm('filemaster.write_bucket', self.downloaders_group, self.allowed_bucket)
        assign_perm('filemaster.write_bucket', self.uploaders_group, self.allowed_bucket)

        # Have the superuser create two files.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_INSIDE_GROUP_INFO), content_type='application/json')
        self.accessible_file_uuid = json.loads(response.content)['uuid']

        response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_OUTSIDE_GROUP_INFO), content_type='application/json')
        self.inaccessible_file_uuid = json.loads(response.content)['uuid']

        # Create the buckets in our "virtual AWS/boto" here for our moto mock S3 calls.
        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=ALLOWED_BUCKET_NAME)
        conn.create_bucket(Bucket=BLOCKED_BUCKET_NAME)

        # Prepare faked STS credentials for mocking later.
        fake_sts_credentials = FakeStsCredentials(access_key=FAKE_AWS_KEY_ID, secret_key=FAKE_AWS_SECRET, session_token='abcdefghikjlmnop')
        self.fake_federation_token = FakeStsFederationToken(credentials=fake_sts_credentials)

    @override_settings(BUCKETS=BUCKETS_SETTING)
    def superuser_uploads_and_downloads_file(self, get_federation_token):
        """
        A helper method to quickly have a superuser upload and download a file.
        """

        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')

    def test_groups_have_valid_bucket_permissions(self):

        # Confirm that the permissions added during test setUp applied.
        self.assertTrue('write_bucket' in get_perms(self.readers_group, self.allowed_bucket))
        self.assertTrue('write_bucket' in get_perms(self.writers_group, self.allowed_bucket))
        self.assertTrue('write_bucket' in get_perms(self.downloaders_group, self.allowed_bucket))
        self.assertTrue('write_bucket' in get_perms(self.uploaders_group, self.allowed_bucket))

        # Permissions were never given to the blocked bucket.
        self.assertFalse('write_bucket' in get_perms(self.readers_group, self.blocked_bucket))
        self.assertFalse('write_bucket' in get_perms(self.writers_group, self.blocked_bucket))
        self.assertFalse('write_bucket' in get_perms(self.downloaders_group, self.blocked_bucket))
        self.assertFalse('write_bucket' in get_perms(self.uploaders_group, self.blocked_bucket))


    def test_superuser_can_add_user(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        data = {"users": ["random_person@example.com"]}

        response = client.post('/filemaster/user/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)


    def test_miscellaneous_user_cannot_add_user(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        data = {"users": ["random_person@example.com"]}

        response = client.post('/filemaster/user/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 403)


    def test_superuser_can_add_user_to_group(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        user_email = "random_person@example.com"

        # First create the user.
        data = {"users": [user_email]}
        response = client.post('/filemaster/user/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 201)

        # Then add it to the group.
        data = {
            "users": [{"email": user_email}],
            "buckets": [{"name": ALLOWED_BUCKET_NAME}]
        }

        response = client.put(f'/filemaster/groups/{READERS_GROUP}/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(user_email in str(response.content))


    def test_superuser_can_remove_user_from_group(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        data = {"users": [{"email": READONLY_USER_EMAIL}]}

        response = client.delete(f'/filemaster/groups/{READERS_GROUP}/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(READONLY_USER_EMAIL in str(response.content))


    def test_miscellaneous_user_cannot_add_user_to_group(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        data = {
            "users": [{"email": READ_AND_WRITE_USER_EMAIL}],
            "buckets": [{"name": ALLOWED_BUCKET_NAME}]
        }

        response = client.put(f'/filemaster/groups/{UPLOADERS_GROUP}/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 403)


    def test_superuser_can_post_and_get_file_info(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Test that the superuser can POST a new file.
        response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_INSIDE_GROUP_INFO), content_type='application/json')
        self.assertEqual(response.status_code, 201)

        file_uuid = json.loads(response.content)['uuid']

        # Test that the superuser can GET information about that file.
        response = client.get(f'/filemaster/api/file/{file_uuid}/')
        self.assertEqual(response.status_code, 200)

        # Test that the superuser can POST a new file without permissions specified.
        response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_OUTSIDE_GROUP_INFO), content_type='application/json')
        self.assertEqual(response.status_code, 201)

        file_uuid = json.loads(response.content)['uuid']

        # Test that the superuser can GET information about that file even though there were no permissions with it.
        response = client.get(f'/filemaster/api/file/{file_uuid}/')
        self.assertEqual(response.status_code, 200)


    # TODO FS-72: users without write permissions to a group should not be able to post files to it
    # def test_noperms_user_cannot_post_file_to_group(self):
    #     client = Client()
    #     client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

    #     response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_INSIDE_GROUP_INFO), content_type='application/json')
    #     self.assertEqual(response.status_code, 403)


    def test_noperms_user_can_post_file_if_no_group_specified(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.post(f'/filemaster/api/file/', data=json.dumps(FILE_OUTSIDE_GROUP_INFO), content_type='application/json')
        self.assertEqual(response.status_code, 201)


    def test_noread_user_cannot_get_file(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.writeonly_user_token}'

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/')
        self.assertEqual(response.status_code, 403)


    def test_readonly_user_cannot_get_file_outside_group(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/file/{self.inaccessible_file_uuid}/')
        self.assertEqual(response.status_code, 403)


    def test_readonly_user_can_get_someone_elses_file(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/')
        self.assertEqual(response.status_code, 200)


    def test_user_cannot_access_file_after_being_removed_from_group(self):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        # First confirm the user can access the file.
        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/')
        self.assertEqual(response.status_code, 200)

        # Have the superuser remove the user from the group.
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'
        data = {
            "users": [{"email": READONLY_USER_EMAIL}],
        }
        response = client.delete(f'/filemaster/groups/{READERS_GROUP}/', data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(READONLY_USER_EMAIL in str(response.content))

        # Now confirm the user cannot access the file.
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'
        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/')
        self.assertEqual(response.status_code, 403)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_superuser_can_get_upload_url(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue("url" in json.loads(response.content))


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_upload_user_can_get_upload_url(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue("url" in json.loads(response.content))


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_upload_user_cannot_get_upload_url_for_file_outside_group(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.inaccessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 403)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_upload_user_cannot_get_upload_url_for_file_for_blocked_bucket(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={BLOCKED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 403)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_notupload_user_cannot_get_upload_url(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 403)


    # # TODO FS-59: 500 error if the file was not uploaded. Cannot run test in this case because of uncaught exception.
    # @patch('boto.sts.connection.STSConnection.get_federation_token')
    # @override_settings(BUCKETS=BUCKETS_SETTING)
    # def test_superuser_can_check_uploadcomplete_on_file_never_uploaded(self, get_federation_token):
    #     client = Client()
    #     client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

    #     # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
    #     get_federation_token.return_value = self.fake_federation_token

    #     response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
    #     self.assertEqual(response.status_code, 200)

    #     file_location_id = json.loads(response.content)["locationid"]

    #     response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/uploadcomplete/?location={file_location_id}')
    #     self.assertEqual(response.status_code, 500)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_superuser_can_check_uploadcomplete_on_file_actually_uploaded(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        file_location_id = json.loads(response.content)["locationid"]
        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/uploadcomplete/?location={file_location_id}')
        self.assertEqual(response.status_code, 200)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_upload_user_can_check_uploadcomplete(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        file_location_id = json.loads(response.content)["locationid"]
        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/uploadcomplete/?location={file_location_id}')
        self.assertEqual(response.status_code, 200)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_notupload_user_cannot_check_uploadcomplete(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/uploadcomplete/')
        self.assertEqual(response.status_code, 403)


    # # TODO FS-75 This should return an error code but currently breaks because of FS-74
    # @override_settings(BUCKETS=BUCKETS_SETTING)
    # def test_superuser_cannot_get_download_url_for_file_never_uploaded(self):
    #     client = Client()
    #     client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

    #     response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')
    #     self.assertEqual(response.status_code, 404)


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_superuser_can_get_download_url_for_uploaded_file(self, get_federation_token):
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue("url" in json.loads(response.content))


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_downloader_user_can_get_download_url_for_uploaded_file(self, get_federation_token):

        # First have a superuser upload the file
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        # Then have a downloader user try to download it.
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'
        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue("url" in json.loads(response.content))


    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_notdownloader_user_cannot_get_download_url_for_uploaded_file(self, get_federation_token):
        # First have a superuser upload the file
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")

        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        # Then have a readonly user try to download it.
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'
        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')
        self.assertEqual(response.status_code, 403)

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    @override_settings(BUCKETS=BUCKETS_SETTING)
    def test_download_request_creates_download_log(self, get_federation_token):

        # First have a superuser upload the file
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.super_user_token}'

        # Patch what get_federation_token() would return since we will not be calling any real AWS STS service.
        get_federation_token.return_value = self.fake_federation_token

        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/upload/?bucket={ALLOWED_BUCKET_NAME}')
        self.assertEqual(response.status_code, 200)

        folder_name = json.loads(response.content)["foldername"]
        file_name = json.loads(response.content)["filename"]

        # Pretend to upload the file to S3.
        file_content = io.StringIO()
        file_content.write("abcdefghijklmnopqrst")
        s3 = boto3.client('s3')
        s3.upload_fileobj(file_content, ALLOWED_BUCKET_NAME, folder_name + '/' + file_name)

        # Then have a downloader user try to download it.
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.everything_but_admin_user_token}'
        response = client.get(f'/filemaster/api/file/{self.accessible_file_uuid}/download/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue("url" in json.loads(response.content))

        # Then check to see if a download log was created.
        archivefile = ArchiveFile.objects.get(uuid=self.accessible_file_uuid)
        download_log = DownloadLog.objects.filter(archivefile=archivefile, requesting_user=self.everything_but_admin_user)
        self.assertTrue(download_log.exists())

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_without_permissions_cannot_access_download_log(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user without any permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.noperms_user_token}'

        response = client.get(f'/filemaster/api/logs/')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there were no results returned.
        self.assertTrue(response_json['count'] == 0)
        self.assertTrue(response_json['results'] == [])

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_with_permissions_can_access_download_log(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/logs/')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_gets_download_logs_with_user_email_param(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/logs/?user_email={SUPERUSER_EMAIL}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_gets_download_logs_with_uuid_param(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/logs/?uuid={self.accessible_file_uuid}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_gets_download_logs_with_filename_param(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        response = client.get(f'/filemaster/api/logs/?filename={ACCESSIBLE_FILE_NAME}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_gets_download_logs_with_download_date_gte_param(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        # Search for files uploaded after yesterday. Should return one.
        yesterdays_date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
        response = client.get(f'/filemaster/api/logs/?download_date_gte={yesterdays_date}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

        # Search for files uploaded after today. Should return none.
        tomorrows_date = datetime.strftime(datetime.now() - timedelta(-1), '%Y-%m-%d')
        response = client.get(f'/filemaster/api/logs/?download_date_gte={tomorrows_date}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 0)

    @patch('boto.sts.connection.STSConnection.get_federation_token')
    def test_user_gets_download_logs_with_download_date_lte_param(self, get_federation_token):

        # Have a superuser upload and download the file.
        self.superuser_uploads_and_downloads_file(get_federation_token)

        # Now have a user with permissions to that file try to get the download logs.
        client = Client()
        client.defaults['HTTP_AUTHORIZATION'] = f'Token {self.readonly_user_token}'

        # Search for files uploaded after yesterday. Should return one.
        tomorrows_date = datetime.strftime(datetime.now() - timedelta(-1), '%Y-%m-%d')
        response = client.get(f'/filemaster/api/logs/?download_date_lte={tomorrows_date}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 1)

        # Ensure that the download log contained some expected values.
        self.assertTrue(response_json['results'][0]['archivefile']['uuid'] == self.accessible_file_uuid)
        self.assertTrue(response_json['results'][0]['requesting_user']['email'] == SUPERUSER_EMAIL)
        self.assertTrue("download_requested_on" in response_json['results'][0])

        # Search for files uploaded before yesterday. Should return none.
        yesterdays_date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
        response = client.get(f'/filemaster/api/logs/?download_date_lte={yesterdays_date}')
        response_json = json.loads(response.content)

        # Ensure that the json response is paginated.
        self.assertTrue("count" in response_json)

        # Ensure that there one result was returned.
        self.assertTrue(response_json['count'] == 0)
