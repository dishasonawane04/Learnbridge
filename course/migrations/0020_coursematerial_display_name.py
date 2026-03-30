from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course', '0019_course_flashcard_chunk_index_flashcardchunk'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursematerial',
            name='display_name',
            field=models.CharField(blank=True, help_text='Custom name for the document', max_length=255),
        ),
    ]
