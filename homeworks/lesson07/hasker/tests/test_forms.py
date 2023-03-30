import functools
from io import BytesIO

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from hasker.forms import AnswerForm, QuestionForm, RegisterUserForm, UpdateUserForm, UserProfileForm
from hasker.models.account import User


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)

        return wrapper

    return decorator


class HaskerQuestionFormTest(TestCase):
    """"""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
                'user', 'uaer@email.net'
        )

    def test_form_fields(self):
        form = QuestionForm()
        self.assertEqual(form.fields['tag'].label, 'Теги')
        self.assertEqual(form.fields['tag'].help_text, 'Не более 3-х тегов')
        self.assertIsInstance(form.fields['tag'].widget, forms.TextInput)
        self.assertIsInstance(form.fields['text'].widget, forms.Textarea)
        self.assertEqual(form.fields['text'].widget.attrs['rows'], 5)
        self.assertEqual(form.fields['title'].label, 'Заголовок')
        self.assertEqual(form.fields['title'].help_text, 'Краткое описание вопроса')
        self.assertEqual(form.fields['title'].max_length, 254)
        self.assertEqual(form.fields['text'].label, 'Содержание')
        self.assertEqual(form.fields['text'].help_text, 'Суть вопроса')

    @cases([
        {'title': '', 'text': '', 'author': '', 'tag': ''},
        {'title': 'Question', 'text': '', 'author': '', 'tag': ''},
        {'title': 'Question', 'text': "Question's text", 'author': True, 'tag': 'tag1,tag2,taf3,t'},
    ])
    def test_form_invalid(self, form_data):
        form_data['author'] = self.user
        form = QuestionForm(data=form_data)
        valid = form.is_valid()
        self.assertFalse(valid, form_data)

    @cases([
        {'title': 'Question', 'text': "Question's text", 'author': '', 'tag': ''},
        {'title': 'Question', 'text': "Question's text", 'author': '', 'tag': 'tag1'},
        {'title': 'Question', 'text': "Question's text", 'author': '', 'tag': 'tag1,tag2'},
        {'title': 'Question', 'text': "Question's text", 'author': '', 'tag': 'tag1,tag2,tag3'},
    ])
    def test_form_valid(self, form_data):
        form_data['author'] = self.user
        form = QuestionForm(data=form_data)
        self.assertTrue(form.is_valid())


class HaskerAnswerFormTest(TestCase):
    """"""

    def test_form_fields(self):
        form = AnswerForm()
        self.assertEqual(form.fields['answer'].label, 'Ответ')
        self.assertIsInstance(form.fields['answer'].widget, forms.Textarea)
        self.assertTrue(form.fields['answer'].widget.attrs['required'])
        self.assertEqual(form.fields['answer'].widget.attrs['rows'], 5)
        self.assertTrue(form.fields['answer'].required)


class HaskerRegisterUserFormTest(TestCase):
    """"""

    def test_form_fields(self):
        form = RegisterUserForm()
        self.assertListEqual(list(form.fields.keys()), ['username', 'email', 'password1', 'password2'])


class HaskerUpdateUserFormTest(TestCase):
    """"""

    def test_form_fields(self):
        form = UpdateUserForm()
        self.assertTrue(form.fields['username'].widget.attrs['readonly'])
        self.assertListEqual(list(form.fields.keys()), ['username', 'email'])


class HaskerUserProfileFormTest(TestCase):
    """"""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
                'user', 'uaer@email.net'
        )

    def test_form_fields(self):
        form = UserProfileForm()
        self.assertEqual(form.fields['avatar'].label, 'Аватар')
        self.assertEqual(form.fields['avatar'].max_length, 500)
        self.assertEqual(form.fields['avatar'].initial, 'images/profile/default.jpg')
        self.assertFalse(form.fields['avatar'].required)

    @cases([
        ((900, 900), ('image', 'jpeg'), 'jpeg'),
        ((1000, 1000), ('image', 'jpg'), 'jpeg'),
        ((600, 600), ('image', 'gif'), 'gif'),
        ((800, 800), ('image', 'png'), 'png'),
    ])
    def test_form_valid(self, size, ftype, format):
        blob = BytesIO()
        Image.new('RGB', size, 'white').save(blob, format)
        blob.seek(0)
        up_file = SimpleUploadedFile(
                name=f'test_image.{ftype[1]}',
                content=blob.read(),
                content_type='/'.join(ftype)
        )
        form = UserProfileForm(
                {'user': self.user},
                {'avatar': up_file}
        )
        valid = form.is_valid()
        self.assertTrue(valid, ftype)

    @cases([
        ((900, 500), ('image', 'tif')),
        ((900, 1001), ('image', 'jpeg')),
        ((900, 1000), ('image', 'bmp')),
        ((900, 500), ('image', 'tif')),
        ((900, 500), ('image', 'pic')),
        ((900, 500), ('image', 'tif')),
        ((700, 500), ('application', 'msword')),
        ((700, 500), ('application', 'x-msdownload')),
    ])
    def test_form_invalid(self, size, ftype):
        try:
            blob = BytesIO()
            Image.new('RGB', size, 'white').save(blob, ftype[1].upper())
            blob.seek(0)
        except KeyError:
            self.assertTrue(True)  # Image не принимает незнакомые (неграфические) форматы файлов
        else:
            up_file = SimpleUploadedFile(
                    name=f'test_image.{ftype[1]}',
                    content=blob.read(),
                    content_type='/'.join(ftype)
            )
            form = UserProfileForm(
                    {'user': self.user},
                    {'avatar': up_file}
            )
            valid = form.is_valid()
            self.assertFalse(valid, ftype)
