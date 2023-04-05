from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse

from hasker.models.managers import QuestionManager

AUTH_USER = get_user_model()


class BaseModel(models.Model):
    """Базовая модель для моделей Question, Answer

    - created_at: дата создания вопроса, ответа
    - rating    : голоса пользователей за вопросы и ответы
    """
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, editable=False)
    rating = models.PositiveIntegerField('Рейтинг', default=0, editable=False)

    class Meta:
        abstract = True


class Question(BaseModel):
    """Вопросы пользователей"""
    title = models.CharField('Заголовок', help_text='Краткое описание вопроса', max_length=254, db_index=True)
    text = models.TextField('Содержание', help_text='Суть вопроса')
    tags = models.ManyToManyField('Tag', related_name='questions', blank=True)
    author = models.ForeignKey(AUTH_USER, verbose_name='Автор', on_delete=models.PROTECT, related_name='questions')

    objects = QuestionManager()

    def get_answers(self):
        """Ответы, относящиеся к вопросу"""
        return self.answers.order_by('-is_right', '-rating', 'created_at')


class Answer(BaseModel):
    """Ответы на вопросы пользователей"""
    text = models.TextField('Содержание ответа')
    question = models.ForeignKey('Question', verbose_name='Вопрос', on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey(AUTH_USER, verbose_name='Автор', on_delete=models.PROTECT, related_name='answers')
    is_right = models.BooleanField('Правильный ответ', default=False)

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse('question_detail', args=(self.pk,))


class Tag(models.Model):
    """Теги вопросов"""
    title = models.CharField('Тэг', max_length=48, unique=True)

    def __str__(self):
        return self.title.lower()


class Vote(models.Model):
    """Журнал рейтинга вопросов/ответов по пользователям

    Ограничение выставления рейтинга на вопрос/ответ одним пользователем. Пользователь может только один раз
    проголосовать за конкретный вопрос или ответ. Ограничение на уровне БД
    """
    author = models.ForeignKey(AUTH_USER, on_delete=models.DO_NOTHING)
    question = models.ForeignKey('Question', on_delete=models.CASCADE, null=True, related_name='question_votes')
    answer = models.ForeignKey('Answer', on_delete=models.CASCADE, null=True, related_name='answer_votes')

    class Meta:
        constraints = (
            models.UniqueConstraint(name='unique_vote_user_question', fields=('author', 'question')),
            models.UniqueConstraint(name='unique_vote_user_answer', fields=('author', 'answer')),
        )
