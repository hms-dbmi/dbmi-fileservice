# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0005_auto_20141013_2018'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivefile',
            name='creationdate',
            field=models.DateTimeField(default=datetime.date(2014, 10, 13), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='archivefile',
            name='modifydate',
            field=models.DateTimeField(default=datetime.date(2014, 10, 13), auto_now=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='filelocation',
            name='modifydate',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
