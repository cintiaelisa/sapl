# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-02-13 14:37
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('materia', '0075_auto_20170203_1019'),
        ('parlamentares', '0039_remove_votante_ip'),
        ('sessao', '0033_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='VotoNominal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voto', models.CharField(max_length=10, verbose_name='Voto')),
                ('ip', models.CharField(max_length=30, verbose_name='IP')),
                ('data_hora', models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora')),
                ('expediente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='sessao.ExpedienteMateria')),
                ('materia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='materia.MateriaLegislativa')),
                ('ordem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='sessao.OrdemDia')),
                ('parlamentar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='parlamentares.Parlamentar')),
                ('sessao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sessao.SessaoPlenaria')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Registro do Voto do Parlamentar',
                'verbose_name_plural': 'Registros dos Votos dos Parlamentares',
            },
        ),
    ]