from random import random

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from hasker.forms import QuestionForm, QuestionNewAnswerForm
from hasker.models import Answer, Question, Vote

# class TrendingMixing:  # todo заменить на middleware или templatetag
#     """"""
#     # def get_context_data(self, *, object_list=None, **kwargs):
#     #     trend_list = Question.objects.trend_queryset()
#     #     kwargs['trend_list'] = trend_list
#     #     return super().get_context_data(object_list=object_list, **kwargs)
OBJECTS_ON_PAGE = 2


def index(request):
    objects_list = Question.objects.order_by('-created_at')
    paginator = Paginator(objects_list, OBJECTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'object_list': page_obj,
        'paginator': paginator
    }
    context['is_paginated'] = True if page_obj.has_other_pages() else False
    return render(request, 'index.html', context)


def ask(request):
    if not request.user.is_authenticated:
        url = reverse('login') + f"?next={reverse('ask')}"
        return HttpResponseRedirect(url)

    if request.method == 'GET':
        form = QuestionForm()
        return render(request, 'question_create.html', context={'form': form})
    elif request.method == 'POST':
        """"""
        form = QuestionForm(request.POST)
        object = form.save(commit=False)
        object.author = request.user
        object.save()
        url = reverse('question_detail', kwargs={'pk': object.pk})
        return HttpResponseRedirect(url)

    return HttpResponseBadRequest


def question_detail(request, *args, **kwargs):
    context = {}
    pk = kwargs.get('pk')
    object = get_object_or_404(Question, pk=pk)
    _question_rating_handle(request, object)  # обработка установки рэйтинга
    answers = object.get_answers()
    paginator = Paginator(answers, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context.update({'object': object,
                    'answers': page_obj,
                    'page_obj': page_obj,
                    'paginator': paginator,
                    })
    if page_obj.has_other_pages():
        context['is_paginated'] = True
    else:
        context['is_paginated'] = False

    if request.method == 'POST' and request.user.is_authenticated:
        form = QuestionNewAnswerForm(request.POST)
        if not form.is_valid():
            context.update({'form': form})
            return render(request, 'question_detail.html', context=context)
        answer = form.cleaned_data.get('answer')
        if answer:
            ###
            from django.utils.lorem_ipsum import words
            count = int(random() * 100)
            Answer.objects.create(
                    question=object,
                    # text=answer,
                    text=words(count),
                    author=request.user,
            )
            return HttpResponseRedirect(reverse('question_detail', args=(object.pk,)))
    form = QuestionNewAnswerForm()
    context.update({'form': form})
    return render(request, 'question_detail.html', context=context)


def _question_rating_handle(request, question):
    """"""
    if not request.user.is_authenticated:
        return
    # Обработка установки правильного ответа инициатором вопроса
    answer_pk = request.GET.get('right_answer')
    if answer_pk and question.author == request.user:
        try:
            answer = Answer.objects.get(pk=int(answer_pk))
        except Answer.DoesNotExist:
            return
        else:
            with transaction.atomic():
                Answer.objects.filter(question=question, is_right=True).update(is_right=False)
                answer.is_right = True
                answer.save()
        return

    # Обработка установки рейтинга вопроса/ответа
    action = request.GET.get('rating')
    if action not in ('up', 'down'):
        return
    object = question
    attr = 'question'
    answer_pk = request.GET.get('answer')
    if answer_pk:
        try:
            answer = Answer.objects.get(pk=int(answer_pk))
        except Answer.DoesNotExist:
            return
        else:
            object = answer
            attr = 'answer'
    request_data = {'author': request.user,
                    attr: object}

    try:
        with transaction.atomic():
            if action == 'up':
                Vote.objects.create(**request_data)
                object.rating += 1
                object.save()
            else:
                Vote.objects.filter(**request_data).delete()
                object.rating -= 1
                if object.rating < 0:
                    object.rating = 0
                object.save()
    except (IntegrityError, Vote.DoesNotExist):
        pass

# class Index(TrendingMixing, ListView):
#     """"""
#     model = Question
#     paginate_by = 20
#     ordering = '-created_at', '-rating'
#     template_name = 'question_list.html'
#
#     def get_queryset(self):
#         # todo исходя из ссылки - new or hot
#         return super().get_queryset()
#
#
# class CreateQuestion(TrendingMixing, CreateView):
#     model = Question
#     template_name = 'question_create.html'
#
#
# class DetailQuestion(TrendingMixing, DetailView):
#     """"""
#     model = Question
#     template_name = 'question_detail.html'
#
#     # todo paginate
#     # todo add new answer form только для авторизованных пользователей
#
#     def get_context_data(self, *, object_list=None, **kwargs):
#         answers = self.object.answers()
#         kwargs['answers'] = answers  # todo сортировку
#         return super().get_context_data(object_list=object_list, **kwargs)
#
#     # todo add def form_valid() - создание нового вопроса
#     # todo add отправку email автору вопроса
#
#
# class QuestionRight(BaseDetailView):
#     model = Question
#
#     # todo установка флага правильного ответа автором
#
#
# class QuestionRating(BaseDetailView):
#     model = Question
#
#     # todo голосование пользователями за вопрос
#
#
# class AnswerRating(BaseDetailView):
#     model = Answer
#
#     # todo голосование пользователями за вопрос
#
#
# class QuestionSearch(TrendingMixing, ListView):
#     model = Question
#     template_name = 'question_list.html'
#     ordering = ('-rating', '-created_at')
#     paginate_by = 20
#
#     # todo поиск по заголовку и тексту вопроса по тэгу через tag:<tag_name>
