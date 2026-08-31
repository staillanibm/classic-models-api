from django.db import migrations

ROLE_GROUPS = ["restocker"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLE_GROUPS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0003_externalidentity"),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
