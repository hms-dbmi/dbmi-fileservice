# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-03-26 17:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0019_auto_20190325_1529'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='downloadlog',
            name='requesting_email',
        ),
    ]