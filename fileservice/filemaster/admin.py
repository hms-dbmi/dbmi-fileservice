from django.contrib import admin
from .models import HealthCheck,CustomUser,Bucket
from guardian.admin import GuardedModelAdmin

class HealthCheckAdmin(GuardedModelAdmin):
    pass

class CustomUserAdmin(GuardedModelAdmin):
    pass

class BucketAdmin(GuardedModelAdmin):
    pass


admin.site.register(HealthCheck,HealthCheckAdmin)
admin.site.register(CustomUser,CustomUserAdmin)
admin.site.register(Bucket,BucketAdmin)
