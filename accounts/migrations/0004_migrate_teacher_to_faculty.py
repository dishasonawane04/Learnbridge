from django.db import migrations

def migrate_teacher_to_faculty(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    # Use exact case matching as per old choices
    UserProfile.objects.filter(role='Teacher').update(role='Faculty')
    # Also handle lowercase just in case
    UserProfile.objects.filter(role='teacher').update(role='Faculty')

def reverse_faculty_to_teacher(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    UserProfile.objects.filter(role='Faculty').update(role='Teacher')

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_userprofile_role'),
    ]

    operations = [
        migrations.RunPython(migrate_teacher_to_faculty, reverse_faculty_to_teacher),
    ]
