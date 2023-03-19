from django import template

from hasker.models import Question

register = template.Library()


@register.simple_tag
def get_trends():
    return Question.objects.trend_queryset()
    c = qs.count()
    return {'trends': qs}
    # return Question.objects.trend_queryset()
