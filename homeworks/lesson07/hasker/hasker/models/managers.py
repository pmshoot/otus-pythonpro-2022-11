from django.conf import settings
from django.db import models

TREND_QUERYSET_COUNT = getattr(settings, 'HASKER_TREND_QUERYSET_COUNT', 20)


class QuestionManager(models.Manager):
    def trend_queryset(self):
        return self.get_queryset().filter(rating__gt=0).order_by('-rating', '-created_at')[:TREND_QUERYSET_COUNT]

    def new_questions(self):
        return self.get_queryset().order_by('-created_at', '-rating')

    def hot_questions(self):
        return self.get_queryset().order_by('-rating', '-created_at')
