# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0004_auto_20141013_1947'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='archivefile',
            options={'permissions': (('download_archivefile', 'Download File'), ('upload_archivefile', 'Upload File'))},
        ),
        migrations.AddField(
            model_name='archivefile',
            name='filename',
            field=models.TextField(default='test.txt'),
            preserve_default=False,
        ),
    ]
