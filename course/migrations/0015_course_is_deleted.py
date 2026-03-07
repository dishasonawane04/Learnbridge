from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('course', '0014_course_executive_summary_alter_coursematerial_file_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='course',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
