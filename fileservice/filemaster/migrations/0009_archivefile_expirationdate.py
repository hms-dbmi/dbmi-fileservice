# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0008_auto_20150107_2157'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivefile',
            name='expirationdate',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
