# Generated by Django 4.1.7 on 2023-03-07 09:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('rating', models.PositiveIntegerField(editable=False, null=True, verbose_name='Рейтинг')),
                ('title', models.CharField(max_length=254, verbose_name='Заголовок')),
                ('text', models.TextField(verbose_name='Содержание')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='questions', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=48, unique=True, verbose_name='Тэг')),
            ],
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answer_votes', to='hasker.question')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_votes', to='hasker.question')),
            ],
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('rating', models.PositiveIntegerField(editable=False, null=True, verbose_name='Рейтинг')),
                ('text', models.TextField(verbose_name='Содержание ответа')),
                ('is_right', models.BooleanField(default=False, verbose_name='Правильный ответ')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='answers', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='hasker.question', verbose_name='Вопрос')),
            ],
        ),
        migrations.AddConstraint(
            model_name='vote',
            constraint=models.UniqueConstraint(fields=('author', 'question'), name='unique_vote_user_question'),
        ),
        migrations.AddConstraint(
            model_name='vote',
            constraint=models.UniqueConstraint(fields=('author', 'answer'), name='unique_vote_user_answer'),
        ),
    ]
