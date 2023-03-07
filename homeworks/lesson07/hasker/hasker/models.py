from django.contrib.auth import get_user, get_user_model
from django.db import models

AUTH_USER = get_user_model()


class BaseModel(models.Model):
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, editable=False)
    rating = models.PositiveIntegerField('Рейтинг', default=0, editable=False)

    class Meta:
        abstract = True


class Question(BaseModel):
    """Вопросы"""
    title = models.CharField('Заголовок', max_length=254, db_index=True)
    text = models.TextField('Содержание')
    tag = models.ManyToManyField('Tag', related_name='questions')
    author = models.ForeignKey(AUTH_USER, verbose_name='Автор', on_delete=models.PROTECT, related_name='questions')


class Answer(BaseModel):
    """Ответы"""
    text = models.TextField('Содержание ответа')
    question = models.ForeignKey('Question', verbose_name='Вопрос', on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(AUTH_USER, verbose_name='Автор', on_delete=models.PROTECT, related_name='answers')
    is_right = models.BooleanField('Правильный ответ', default=False)


class Tag(models.Model):
    """Теги вопросов"""
    title = models.CharField('Тэг', max_length=48, unique=True)


class Vote(models.Model):
    """Журнал рейтинга вопросов/ответов по пользователям"""
    author = models.ForeignKey(AUTH_USER, on_delete=models.DO_NOTHING)
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='question_votes')
    answer = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='answer_votes')

    class Meta:
        constraints = (
            models.UniqueConstraint(name='unique_vote_user_question', fields=('author', 'question')),
            models.UniqueConstraint(name='unique_vote_user_answer', fields=('author', 'answer')),
        )
