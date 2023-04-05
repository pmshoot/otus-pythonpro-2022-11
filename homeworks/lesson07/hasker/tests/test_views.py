from random import randint

from django.test import TestCase
from django.urls import reverse
from django.utils import lorem_ipsum

from hasker.models.account import User
from hasker.models.hasker import Question
from hasker.views.hasker import QUESTIONS_ON_PAGE


class IndexViewTest(TestCase):
    """"""

    @classmethod
    def setUpTestData(cls):
        cls.usr_numbers = 5
        cls.qst_numbers = 5
        for i in range(cls.usr_numbers):
            u = User.objects.create_user(f'user{i}', f'user{i}@mail.ltd', f'password{i}')
            for ii in range(cls.qst_numbers):
                Question.objects.create(title=lorem_ipsum.words(20),
                                        text=lorem_ipsum.paragraphs(1),
                                        author=u,
                                        )

    def test_view_index_url_exists(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'index.html')

    def test_view_index_reverse_url_exists(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)

    def test_view_index_order_is_new(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['order'] == 'new')

    def test_view_index_is_hots(self):
        resp = self.client.get(reverse('index') + '?o=hot')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['order'] == 'hot')

    def test_view_index_paginate_exists(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] is True)

    def test_view_index_page1(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.context['object_list']) == QUESTIONS_ON_PAGE)

    def test_view_index_page2(self):
        resp = self.client.get(reverse('index') + '?page=2')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] is True)
        self.assertTrue(len(resp.context['object_list']) == self.usr_numbers * self.qst_numbers - QUESTIONS_ON_PAGE)


class RegisteredUserViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user('user', 'user@mail.ltd', 'password')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('ask'))
        self.assertRedirects(resp, '/accounts/login/?next=/ask/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username='user', password='password')
        self.assertTrue(login)
        resp = self.client.get(reverse('ask'))

        # Проверка что пользователь залогинился
        self.assertEqual(str(resp.context['user']), 'user')
        # Проверка ответа на запрос
        self.assertEqual(resp.status_code, 200)

        # Проверка того, что мы используем правильный шаблон
        self.assertTemplateUsed(resp, 'question_create.html')


class SearchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.qst_numbers = 4
        cls.QTITLE = 'QUESTION_TITLE'
        cls.QTEXT = 'QUESTION_TEXT'
        u = User.objects.create_user('user', 'user@mail.ltd', 'password')
        for i in range(cls.qst_numbers):
            Question.objects.create(
                    title=f'{lorem_ipsum.words(randint(1, 20))}_{cls.QTITLE}_{i}',
                    text=f'{lorem_ipsum.words(randint(1, 30))}_{cls.QTEXT}_{i}',
                    author=u,
            )

    def test_search_question_title_like(self):
        resp = self.client.get(reverse('index') + f'?q={self.QTITLE}')
        self.assertTrue(len(resp.context['object_list']) == self.qst_numbers, 'test_search_question_title_like')

    def test_search_question_title(self):
        resp = self.client.get(reverse('index') + f'?q={self.QTITLE}_1')
        self.assertTrue(len(resp.context['object_list']) == 1, 'test_search_question_title')

    def test_search_question_text_like(self):
        resp = self.client.get(reverse('index') + f'?q={self.QTEXT}')
        self.assertTrue(len(resp.context['object_list']) == self.qst_numbers, 'test_search_question_text_like')

    def test_search_question_text(self):
        resp = self.client.get(reverse('index') + f'?q={self.QTEXT}_2')
        self.assertTrue(len(resp.context['object_list']) == 1, 'test_search_question_text')
