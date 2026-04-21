from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0006_remove_quizattempt_failed_topics_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentanswer',
            name='topic',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='subtopic',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='difficulty',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        migrations.AddField(
            model_name='studentanswer',
            name='question_type',
            field=models.CharField(blank=True, default='MCQ', max_length=50),
        ),
    ]
