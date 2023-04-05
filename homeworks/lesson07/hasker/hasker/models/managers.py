from django.conf import settings
from django.db import models

TREND_QUERYSET_COUNT = getattr(settings, 'HASKER_TREND_QUERYSET_COUNT', 20)


class QuestionManager(models.Manager):
    def trend_queryset(self):
        """Выборка вопросов с наибольшим рейтингом на сайте (правый блок)"""
        return self.get_queryset().filter(rating__gt=0).order_by('-rating', '-created_at')[:TREND_QUERYSET_COUNT]

    def new_questions(self):
        """Вопросы с сортировкой по дате создания"""
        return self.get_queryset().order_by('-created_at', '-rating')

    def hot_questions(self):
        """Вопросы с сортировкой по рейтингу"""
        return self.get_queryset().order_by('-rating', '-created_at')
