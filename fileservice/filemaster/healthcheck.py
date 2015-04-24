from health_check.backends.base import BaseHealthCheckBackend, ServiceUnavailable, ServiceReturnedUnexpectedResult
from health_check_db.models import TestModel
from django.db import DatabaseError, IntegrityError
from health_check.plugins import plugin_dir
from .models import id_generator

class DjangoDatabaseBackend(BaseHealthCheckBackend):

    def check_status(self):
        try:
            obj = TestModel.objects.create(title="newtest_"+id_generator())
            obj.title = "newtest_"+id_generator()
            obj.save()
            obj.delete()
            return True
        except IntegrityError:
            raise ServiceReturnedUnexpectedResult("Integrity Error")
        except DatabaseError:
            raise ServiceUnavailable("Database error")

plugin_dir.register(DjangoDatabaseBackend)