# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('filemaster', '0014_auto_20180920_1436'),
    ]

    operations = [
        migrations.RunSQL(
            "UPDATE `filemaster_archivefile` SET uuid = REPLACE(uuid,'-','');"
        )
    ]
