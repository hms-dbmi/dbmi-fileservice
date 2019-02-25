import json
import uuid

from boto.sts import STSConnection
from boto.s3.connection import S3Connection
from django.conf import settings

from .models import FileLocation

import logging
log = logging.getLogger(__name__)


def awsSignedURLUpload(archiveFile=None, bucket=None, aws_key=None, aws_secret=None, foldername=None):
    if not aws_key:
        aws_key = settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID")
    if not aws_secret:
        aws_secret = settings.BUCKETS.get(bucket, {}).get('AWS_SECRET')

    conn = S3Connection(aws_key, aws_secret, is_secure=True)

    url = "S3://%s/%s" % (bucket, foldername + "/" + archiveFile.filename)
    # register file
    fl = FileLocation(url=url, storagetype=settings.BUCKETS[bucket]['type'])
    fl.save()
    archiveFile.locations.add(fl)
    return conn.generate_url(3600 * 24 * 7, 'PUT', bucket=bucket, key=foldername + "/" + archiveFile.filename,
                             force_http=False), fl


def awsTVMUpload(archiveFile=None, bucket=None, aws_key=None, aws_secret=None, foldername=None):
    if not aws_key:
        aws_key = settings.BUCKETS[settings.S3_DEFAULT_BUCKET]['AWS_KEY_ID']
    if not aws_secret:
        aws_secret = settings.BUCKETS[settings.S3_DEFAULT_BUCKET]['AWS_SECRET']

    stsconn = STSConnection(aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)

    policydict = {
        "Statement": [
            {
                "Action": [
                    "s3:*"
                ],
                "Resource": [
                    "arn:aws:s3:::%s/%s/*" % (bucket, foldername)
                ],
                "Effect": "Allow"
            }, {
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": [
                    "arn:aws:s3:::%s*" % (bucket)
                ],
                "Effect": "Allow"
            }
        ]}

    policystring = json.dumps(policydict)
    ststoken = stsconn.get_federation_token("sys_upload", 24 * 3600, policystring)
    jsonoutput = {}
    jsonoutput["SecretAccessKey"] = ststoken.credentials.secret_key
    jsonoutput["AccessKeyId"] = ststoken.credentials.access_key
    jsonoutput["SessionToken"] = ststoken.credentials.session_token
    return jsonoutput


def signedUrlUpload(archiveFile=None, bucket=None, aws_key=None, aws_secret=None, cloud="aws"):
    if not bucket:
        bucket = settings.S3_DEFAULT_BUCKET

    url = None
    fl = None
    foldername = str(uuid.uuid4())

    try:
        if cloud == "aws":
            url, fl = awsSignedURLUpload(archiveFile=archiveFile, bucket=bucket, aws_key=aws_key, aws_secret=aws_secret,
                                         foldername=foldername)
            jsonoutput = awsTVMUpload(archiveFile=archiveFile, bucket=bucket, aws_key=aws_key, aws_secret=aws_secret,
                                      foldername=foldername)

        return {
            "url": url,
            "location": "s3://" + bucket + "/" + foldername + "/" + archiveFile.filename,
            "locationid": fl.id,
            "bucket": bucket,
            "foldername": foldername,
            "filename": archiveFile.filename,
            "secretkey": jsonoutput["SecretAccessKey"],
            "accesskey": jsonoutput["AccessKeyId"],
            "sessiontoken": jsonoutput["SessionToken"]
        }

    except Exception as exc:
        log.error("Error: %s" % exc)
        return {}


def signedUrlDownload(archiveFile=None, aws_key=None, aws_secret=None):

    # TODO: This chunk is looking particularly sketchy
    url = None
    for loc in archiveFile.locations.all():
        if not loc.storagetype:
            pass
        elif loc.storagetype == "glacier":
            return False

        if loc.uploadComplete:
            url = loc.url
            break

    bucket, path = loc.get_bucket()

    if not aws_key:
        aws_key = settings.BUCKETS.get(bucket, {}).get("AWS_KEY_ID")
    if not aws_secret:
        aws_secret = settings.BUCKETS.get(bucket, {}).get('AWS_SECRET')

    conn = S3Connection(aws_key, aws_secret, is_secure=True)

    # check for glacier move
    b = conn.get_bucket(bucket)
    k = b.get_key(path)
    try:
        # restoring
        if k.storage_class == "GLACIER":
            # still restoring
            if k.ongoing_restore and not k.expiry_date:
                return False
            # no restore tried... still in glacier
            if not k.ongoing_restore and not k.expiry_date:
                pass
            # idone restoring with expiration date -- done glacier restore
            if not k.ongoing_restore and k.expiry_date:
                pass
    except:
        pass

    return conn.generate_url(3600 * 24, 'GET', bucket, path)


def awsCopyFile(archive_file, destination, origin=None, aws_key=None, aws_secret=None):

    # If not origin, assume default
    if not origin:
        origin = settings.S3_DEFAULT_BUCKET

    # Get the location
    location = archive_file.get_location(origin)
    if not location:
        log.error(f'No location found for file: {archive_file.uuid}')
        return None

    # Get the file key
    key = location.get_bucket()[1]

    # Trim the protocol from the S3 URL
    log.debug(f'Copying file: s3://{origin.lower()}/{key} -> s3://{destination.lower()}/{key}')

    # Get credentials
    if not aws_key:
        aws_key = settings.BUCKETS.get(destination, {}).get("AWS_KEY_ID")
    if not aws_secret:
        aws_secret = settings.BUCKETS.get(destination, {}).get('AWS_SECRET')

    # Do the move
    s3 = boto3.client('s3',
                      aws_access_key_id=aws_key,
                      aws_secret_access_key=aws_secret)
    s3.copy_object(Bucket=destination, CopySource=f'{origin}/{key}', Key=f'{key}')

    # Create the new location
    new_location = FileLocation(url=f'S3://{destination.lower()}/{key}',
                                storagetype=settings.BUCKETS[destination]['type'],
                                uploadComplete=location.uploadComplete,
                                filesize=location.filesize)
    new_location.save()

    # Add it
    archive_file.locations.add(new_location)

    return new_location


def awsRemoveFile(archive_file, location, origin=None, aws_key=None, aws_secret=None):

    # If not origin, assume default
    if not origin:
        origin = settings.S3_DEFAULT_BUCKET

    # Ensure another location exists
    if not len(archive_file.locations.all()) > 1:
        log.error(f'Cannot delete location "{location}" for file "{archive_file.uuid}", no other locations')
        return False

    # Get the file key
    key = location.get_bucket()[1]

    # Trim the protocol from the S3 URL
    log.debug(f'Removing file from bucket: {origin}')

    # Get credentials
    if not aws_key:
        aws_key = settings.BUCKETS.get(origin, {}).get("AWS_KEY_ID")
    if not aws_secret:
        aws_secret = settings.BUCKETS.get(origin, {}).get('AWS_SECRET')

    # Do the move
    s3 = boto3.client('s3',
                      aws_access_key_id=aws_key,
                      aws_secret_access_key=aws_secret)
    s3.delete_object(Bucket=origin, Key=f'{key}')

    # Delete the location
    archive_file.locations.remove(location)
    location.delete()

    return True


def awsMoveFile(archive_file, destination, origin=None, aws_key=None, aws_secret=None):

    # If not origin, assume default
    if not origin:
        origin = settings.S3_DEFAULT_BUCKET

    # Get the current location
    location = archive_file.get_location(origin)
    if not location:
        log.error(f'No location found for file: {archive_file.uuid}')
        return False

    # Call other methods
    new_location = awsCopyFile(archive_file, destination, origin, aws_key, aws_secret)
    if new_location:

        # File was copied, remove from origin
        if awsRemoveFile(archive_file, location, origin, aws_key, aws_secret):
            return new_location

    return False
