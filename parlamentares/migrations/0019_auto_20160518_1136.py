# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-18 14:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parlamentares', '0018_auto_20160510_0943'),
    ]

    operations = [
        migrations.AlterField(
            model_name='composicaocoligacao',
            name='partido',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parlamentares.Partido', verbose_name='Partido'),
        ),
    ]