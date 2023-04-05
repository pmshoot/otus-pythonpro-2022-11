from django import template

from hasker.models.hasker import Question

register = template.Library()


@register.simple_tag
def get_trends():
    """Queryset для отображения 'топовых' вопросов на правом блоке сайта в шаблоне"""
    return Question.objects.trend_queryset()
