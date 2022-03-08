import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from filemaster.models import ArchiveFile

log = logging.getLogger(__name__)


class Healthcheck(APIView):
    """
    API healthcheck endpoints
    """

    def get(self, _):
        """
        Respond 200 if all is good with FileService, else an error code
        """
        try:
            ArchiveFile.objects.first()

            return Response('FileService up and running', status=status.HTTP_200_OK)
        except Exception as exc:
            log.error('Healthcheck failed with error: %s' % exc)
            return Response(
                'FileService unable to respond correctly at this time', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
