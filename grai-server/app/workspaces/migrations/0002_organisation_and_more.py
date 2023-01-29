# Generated by Django 4.1.5 on 2023-01-15 14:21

import uuid

import django.db.models.deletion
from django.db import migrations, models


def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Organisation = apps.get_model("workspaces", "Organisation")
    db_alias = schema_editor.connection.alias
    Organisation.objects.using(db_alias).create(id="c8dba28b-6991-4c1d-98d5-f9b58ccada90", name="default")


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organisation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveIndex(
            model_name="workspace",
            name="workspaces__name_5adeb1_idx",
        ),
        migrations.AddField(
            model_name="workspace",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workspaces",
                to="workspaces.organisation",
                blank=True,
                null=True,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_func),
        migrations.AlterField(
            model_name="workspace",
            name="organisation",
            field=models.ForeignKey(
                default="c8dba28b-6991-4c1d-98d5-f9b58ccada90",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="workspaces",
                to="workspaces.organisation",
            ),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(fields=["organisation", "name"], name="workspaces__organis_007202_idx"),
        ),
        migrations.AddConstraint(
            model_name="workspace",
            constraint=models.UniqueConstraint(
                fields=("organisation", "name"),
                name="Organisation workspace name uniqueness",
            ),
        ),
        migrations.AddIndex(
            model_name="organisation",
            index=models.Index(fields=["name"], name="workspaces__name_fedc67_idx"),
        ),
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.UniqueConstraint(fields=("name",), name="Organisation name uniqueness"),
        ),
    ]
