from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('course', '0015_course_is_deleted'),
    ]
    operations = [
        migrations.AddField(
            model_name='course',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
