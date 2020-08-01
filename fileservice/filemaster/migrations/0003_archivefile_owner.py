# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0002_auto_20141010_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivefile',
            name='owner',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.deletion.DO_NOTHING),
            preserve_default=True,
        ),
    ]
