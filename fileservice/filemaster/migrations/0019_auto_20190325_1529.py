# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-03-25 19:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0018_auto_20190325_1106'),
    ]

    operations = [
        migrations.RenameField(
            model_name='downloadlog',
            old_name='user',
            new_name='requesting_user',
        ),
        migrations.AddField(
            model_name='downloadlog',
            name='requesting_email',
            field=models.EmailField(blank=True, help_text='Since the user might be a service account, this field helps track where the original request came from.', max_length=254, null=True),
        ),
    ]
