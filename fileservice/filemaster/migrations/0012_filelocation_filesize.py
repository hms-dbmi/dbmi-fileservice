# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0011_auto_20150423_2041'),
    ]

    operations = [
        migrations.AddField(
            model_name='filelocation',
            name='filesize',
            field=models.BigIntegerField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
