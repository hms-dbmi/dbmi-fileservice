# Generated by Django 2.2.28 on 2022-08-19 19:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filemaster', '0023_fileoperation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileoperation',
            name='archivefile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='filemaster.ArchiveFile'),
        ),
        migrations.AlterField(
            model_name='fileoperation',
            name='destination_location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='destination_location', to='filemaster.FileLocation'),
        ),
        migrations.AlterField(
            model_name='fileoperation',
            name='origin_location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='origin_location', to='filemaster.FileLocation'),
        ),
    ]