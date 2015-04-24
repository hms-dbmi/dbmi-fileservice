# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0010_filelocation_storagetype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivefile',
            name='description',
            field=models.CharField(default='', max_length=255, null=True, blank=True),
        ),
    ]
