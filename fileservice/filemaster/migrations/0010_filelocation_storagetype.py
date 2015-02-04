# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0009_archivefile_expirationdate'),
    ]

    operations = [
        migrations.AddField(
            model_name='filelocation',
            name='storagetype',
            field=models.CharField(max_length=255, null=True, blank=True),
            preserve_default=True,
        ),
    ]
