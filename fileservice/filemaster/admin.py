from django.contrib import admin
from .models import HealthCheck,CustomUser
from guardian.admin import GuardedModelAdmin

class HealthCheckAdmin(GuardedModelAdmin):
    pass

class CustomUserAdmin(GuardedModelAdmin):
    pass


admin.site.register(HealthCheck,HealthCheckAdmin)
admin.site.register(CustomUser,CustomUserAdmin)
