# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0003_archivefile_owner'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileLocation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creationdate', models.DateTimeField(auto_now_add=True)),
                ('modifydate', models.DateTimeField(auto_now=True, auto_now_add=True)),
                ('url', models.TextField()),
            ],
            options={
                'ordering': ('-creationdate',),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='archivefile',
            name='locations',
            field=models.ManyToManyField(to='filemaster.FileLocation'),
            preserve_default=True,
        ),
    ]
