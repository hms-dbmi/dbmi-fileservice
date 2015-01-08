# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0007_bucket'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bucket',
            options={'permissions': (('write_bucket', 'Write to bucket'),)},
        ),
        migrations.AddField(
            model_name='filelocation',
            name='uploadComplete',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
