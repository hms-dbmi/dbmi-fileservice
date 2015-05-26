# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.auth.models import User, Group, Permission

from django.db import models, migrations

def poweruser(apps, schema_editor):
    Group.objects.get_or_create(name="powerusers")

class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0012_filelocation_filesize'),
    ]
    
    operations = [
        migrations.RunPython(poweruser),
    ]