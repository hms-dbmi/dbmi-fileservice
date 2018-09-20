# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archivefile',
            name='uuid',
            field=models.UUIDField(editable=False, name=b'uuid', blank=True),
        ),
    ]
