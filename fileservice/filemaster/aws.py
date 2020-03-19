import os
import boto3
from botocore.client import Config

from .models import FileLocation

import logging
log = logging.getLogger(__name__)


def awsClient(service):
    """
    Returns a boto3 client for the passed resource. Will use local testing URLs if
    running in such an environment.
    :param service: The AWS service
    :return: boto3.client
    """
    # Build kwargs
    kwargs = {'config': Config(signature_version='s3v4')}

    # Check for local URL
    if os.environ.get(f'DBMI_AWS_{service.upper()}_URL'):
        kwargs['endpoint_url'] = os.environ.get(f'LOCAL_AWS_{service.upper()}_URL')

    # Check for local URL
    if os.environ.get(f'DBMI_AWS_{service.upper()}_REGION'):
        kwargs['region_name'] = os.environ.get(f'LOCAL_AWS_{service.upper()}_REGION')

    return boto3.client(service, **kwargs)


def awsResource(service):
    """
    Returns a boto3 resource for the passed resource. Will use local testing URLs if
    running in such an environment.
    :param service: The AWS service
    :return: boto3.resource
    """
    # Build kwargs
    kwargs = {'config': Config(signature_version='s3v4')}

    # Check for local URL
    if os.environ.get(f'DBMI_AWS_{service.upper()}_URL'):
        kwargs['endpoint_url'] = os.environ.get(f'LOCAL_AWS_{service.upper()}_URL')

    # Check for local URL
    if os.environ.get(f'DBMI_AWS_{service.upper()}_REGION'):
        kwargs['region_name'] = os.environ.get(f'LOCAL_AWS_{service.upper()}_REGION')

    return boto3.resource(service, **kwargs)


def awsSignedURLUpload(archiveFile=None, bucket=None, foldername=None):

    # Determine URL of upload
    url = "S3://%s/%s" % (bucket, foldername + "/" + archiveFile.filename)

    # register file
    fl = FileLocation(url=url, storagetype='s3')
    fl.save()
    archiveFile.locations.add(fl)

    # Get the service client with sigv4 configured
    s3 = awsClient(service='s3')

    # Generate the URL to get 'key-name' from 'bucket-name'
    # URL expires in 604800 seconds (seven days)
    pre_signed_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': bucket,
            'Key': foldername + "/" + archiveFile.filename
        },
        ExpiresIn=604800
    )
    log.error(f'Pre-signed upload: {pre_signed_url}')
    return pre_signed_url, fl


def signedUrlDownload(archiveFile=None, hours=24):

    # Find a location where upload has been completed
    for loc in archiveFile.locations.filter(uploadComplete__isnull=False):

        # Get bucket and key
        bucket, path = loc.get_bucket()
        if not bucket or not path:
            return False

        # Generate the URL to get 'key-name' from 'bucket-name'
        s3_client = awsClient(service='s3')
        pre_signed_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': path
            },
            ExpiresIn=3600 * hours
        )

        return pre_signed_url

    log.error(f'Could not find Location with "uploadComplete" for "{archiveFile.uuid}"')
    return False


def awsCopyFile(archive_file, destination, origin):

    # Get the location
    location = archive_file.get_location(origin)
    if not location:
        log.error(f'No location found for file: {archive_file.uuid}')
        return None

    # Get the file key
    bucket, key = location.get_bucket()

    # Trim the protocol from the S3 URL
    log.debug(f'Copying file: s3://{origin.lower()}/{key} -> s3://{destination.lower()}/{key}')

    # Do the move
    s3 = awsClient(service='s3')
    s3.copy_object(Bucket=destination, CopySource=f'{origin}/{key}', Key=f'{key}')

    # Create the new location
    new_location = FileLocation(url=f'S3://{destination.lower()}/{key}',
                                storagetype='s3',
                                uploadComplete=location.uploadComplete,
                                filesize=location.filesize)
    new_location.save()

    # Add it
    archive_file.locations.add(new_location)

    return new_location


def awsRemoveFile(location):

    # Get the file bucket and key
    bucket, key = location.get_bucket()

    # Trim the protocol from the S3 URL
    log.debug(f'Removing file: {bucket}/{key}')

    # Do the move
    s3 = awsClient(service='s3')
    s3.delete_object(Bucket=bucket, Key=f'{key}')

    return True


def awsMoveFile(archive_file, destination, origin):

    # Get the current location
    location = archive_file.get_location(origin)
    if not location:
        log.error(f'No location found for file: {archive_file.uuid}')
        return False

    # Call other methods
    new_location = awsCopyFile(archive_file, destination, origin)
    if new_location:

        # File was copied, remove from origin
        if awsRemoveFile(location):

            # Delete the location
            archive_file.locations.remove(location)
            location.delete()

        else:
            log.error(f'Could not delete original file after move: {archive_file.uuid}')

        return new_location

    return False
