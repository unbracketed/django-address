# Generated by Django 2.0 on 2017-12-03 15:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0002_auto_20160213_1726'),
    ]

    operations = [
        migrations.CreateModel(
            name='Admin2',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='', max_length=165)),
            ],
            options={
                'ordering': ('state', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Admin3',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='address.Admin2')),
            ],
            options={
                'ordering': ('state', 'parent', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Admin4',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.Admin3')),
            ],
            options={
                'ordering': ('parent', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Admin5',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.Admin4')),
            ],
            options={
                'ordering': ('parent', 'name'),
            },
        ),
        migrations.CreateModel(
            name='SubLocality1',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
            ],
        ),
        migrations.CreateModel(
            name='SubLocality2',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.SubLocality1')),
            ],
        ),
        migrations.CreateModel(
            name='SubLocality3',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.SubLocality2')),
            ],
        ),
        migrations.CreateModel(
            name='SubLocality4',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.SubLocality3')),
            ],
        ),
        migrations.CreateModel(
            name='SubLocality5',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=165)),
                ('parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.SubLocality4')),
            ],
        ),
        migrations.AlterField(
            model_name='country',
            name='name',
            field=models.CharField(max_length=40, unique=True),
        ),
        migrations.AlterField(
            model_name='locality',
            name='name',
            field=models.CharField(max_length=165),
        ),
        migrations.AlterField(
            model_name='state',
            name='name',
            field=models.CharField(max_length=165),
        ),
        migrations.AddField(
            model_name='sublocality1',
            name='locality',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.Locality'),
        ),
        migrations.AddField(
            model_name='admin3',
            name='state',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='address.State'),
        ),
        migrations.AddField(
            model_name='admin2',
            name='state',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='counties', to='address.State'),
        ),
        migrations.AlterUniqueTogether(
            name='admin5',
            unique_together={('name', 'parent')},
        ),
        migrations.AlterUniqueTogether(
            name='admin4',
            unique_together={('name', 'parent')},
        ),
        migrations.AlterUniqueTogether(
            name='admin3',
            unique_together={('name', 'state')},
        ),
        migrations.AlterUniqueTogether(
            name='admin2',
            unique_together={('name', 'state')},
        ),
    ]
