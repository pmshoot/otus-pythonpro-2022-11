from django import template

from hasker.models.hasker import Question

register = template.Library()


@register.simple_tag
def get_trends():
    return Question.objects.trend_queryset()
