# Generated by Django 2.2.28 on 2022-08-18 21:47

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0022_auto_20210525_1039'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileOperation',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('operation', models.CharField(choices=[('copy', 'Copy'), ('move', 'Move')], max_length=200)),
                ('task_id', models.TextField()),
                ('creationdate', models.DateTimeField(auto_now_add=True)),
                ('modifydate', models.DateTimeField(auto_now=True)),
                ('origin', models.TextField()),
                ('destination', models.TextField()),
                ('archivefile', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='filemaster.ArchiveFile')),
                ('destination_location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='destination_location', to='filemaster.FileLocation')),
                ('origin_location', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='origin_location', to='filemaster.FileLocation')),
            ],
        ),
    ]
