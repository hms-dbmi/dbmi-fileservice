from boto.sts import STSConnection
from boto.s3.connection import S3Connection

from .models import FileLocation

from django.conf import settings

import json, uuid


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
        aws_key = settings.AWS_STS_ACCESS_KEY_ID
    if not aws_secret:
        aws_secret = settings.AWS_STS_SECRET_ACCESS_KEY

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
        bucket = settings.S3_UPLOAD_BUCKET

    url = None
    fl = None
    foldername = str(uuid.uuid4())

    try:
        if cloud == "aws":
            url, fl = awsSignedURLUpload(archiveFile=archiveFile, bucket=bucket, aws_key=aws_key, aws_secret=aws_secret,
                                         foldername=foldername)
            jsonoutput = awsTVMUpload(archiveFile=archiveFile, bucket=bucket, aws_key=aws_key, aws_secret=aws_secret,
                                      foldername=foldername)
    except Exception as exc:
        print("Error: %s" % exc)
        return {}

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


def signedUrlDownload(archiveFile=None, aws_key=None, aws_secret=None):
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