from random import random

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from hasker.forms import AnswerForm, QuestionForm
from hasker.models import Answer, Question, Tag, Vote

# class TrendingMixing:  # todo заменить на middleware или templatetag
#     """"""
#     # def get_context_data(self, *, object_list=None, **kwargs):
#     #     trend_list = Question.objects.trend_queryset()
#     #     kwargs['trend_list'] = trend_list
#     #     return super().get_context_data(object_list=object_list, **kwargs)
QUESTIONS_ON_PAGE = 20
ANSWERS_ON_PAGE = 30
SEND_ANSWER_NOTIFY = getattr(settings, 'HASKER_SEND_ANSWER_NOTIFY', True)


def index(request):
    query = request.GET.get('q', '')
    if query:
        # split
        q = query.split(':')
        if len(q) > 1:
            attr, value = q
            if attr == 'tag':
                filter = Q(tags__title=value.lower())
            elif attr == 'author':
                filter = Q(author__username=value)
            # elif attr == '...':
            #     filter = Q(...)
            else:
                filter = Q()
        else:
            value = q[0]
            filter = Q(title__contains=value) | Q(text__contains=value)
        objects_list = Question.objects.filter(filter)
    else:
        objects_list = Question.objects.all()

    order = request.GET.get('o', 'new')
    if order == 'hot':
        objects_list = objects_list.order_by('-rating')
    else:
        objects_list = objects_list.order_by('-created_at')

    paginator = Paginator(objects_list, QUESTIONS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'object_list': page_obj, 'paginator': paginator, 'query': query,
               'order': order, 'is_paginated': True if page_obj.has_other_pages() else False}
    return render(request, 'index.html', context)


@login_required
def ask(request):
    # if not request.user.is_authenticated:
    #     url = reverse('login') + f"?next={reverse('ask')}"
    #     return HttpResponseRedirect(url)

    if request.method == 'GET':
        form = QuestionForm()
        return render(request, 'question_create.html', context={'form': form})
    elif request.method == 'POST':
        """"""
        with transaction.atomic():
            form = QuestionForm(request.POST)
            object: Question = form.save(commit=False)
            object.author = request.user
            object.save()
            tag_list = form.cleaned_data.get('tag', '').split(',')
            for tag_name in tag_list[:3]:
                tag, _ = Tag.objects.get_or_create(title=tag_name.strip().lower())
                object.tags.add(tag)
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
        form = AnswerForm(request.POST)
        if not form.is_valid():
            context.update({'form': form})
            return render(request, 'question_detail.html', context=context)
        answer = form.cleaned_data.get('answer')
        if answer:
            ###
            from django.utils.lorem_ipsum import words
            count = int(random() * 100)
            new_answer = Answer.objects.create(
                    question=object,
                    # text=answer,
                    text=words(count),
                    author=request.user,
            )
            if SEND_ANSWER_NOTIFY and object.author.email:
                message = f"""
                Новый ответ на вопрос "{object.title}":
                
                {new_answer.text}
                
                Перейти к ответу: {request.META['HTTP_ORIGIN']}{new_answer.get_absolute_url()}
                """

                send_mail(
                        'Новый ответ на Hasker',
                        message,
                        'hasker@mail.com',
                        [object.author.email],
                        fail_silently=True,
                )

            return HttpResponseRedirect(reverse('question_detail', args=(object.pk,)))
    form = AnswerForm()
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
    attr = 'question'
    object = question
    answer_pk = request.GET.get('answer')
    if answer_pk:
        try:
            answer = Answer.objects.get(pk=int(answer_pk))
        except Answer.DoesNotExist:
            return
        else:
            attr = 'answer'
            object = answer

    request_data = {'author': request.user,
                    attr: object}

    try:
        with transaction.atomic():
            if action == 'up':
                Vote.objects.create(**request_data)
                object.rating += 1
                object.save()
            else:
                Vote.objects.get(**request_data).delete()
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
