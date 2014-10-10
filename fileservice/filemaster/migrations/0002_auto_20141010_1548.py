# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivefile',
            name='uuid',
            field=django_extensions.db.fields.UUIDField(editable=False, name=b'uuid', blank=True),
        ),
    ]
