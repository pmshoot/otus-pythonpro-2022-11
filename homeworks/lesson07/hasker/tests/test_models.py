from django.db import IntegrityError
from django.test import TestCase

from hasker.models.account import User, UserProfile
from hasker.models.hasker import Answer, Question, Tag, Vote


class UserProfileModelTest(TestCase):
    """"""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user('user1', 'mail@mail.ltd', 'password')

    def test_user_profile_auto_create(self):
        user = User.objects.get(pk=1)
        self.assertTrue(hasattr(user, 'profile'), 'не создан профиль пользователя')
        profile = getattr(user, 'profile')
        self.assertIsInstance(profile, UserProfile)
        self.assertIsNotNone(profile.avatar)
        self.assertEqual(profile.avatar.url, r'/media/images/profile/default.jpg')

    def test_user_profile_fields_attrs(self):
        user = User.objects.get(pk=1)
        avatar_field_upload_to = user.profile._meta.get_field('avatar').upload_to
        avatar_field_label = user.profile._meta.get_field('avatar').verbose_name
        avatar_field_lenght = user.profile._meta.get_field('avatar').max_length
        avatar_field_blank = user.profile._meta.get_field('avatar').blank
        self.assertEqual(avatar_field_upload_to, 'images/profile')
        self.assertEqual(avatar_field_label, 'Аватар')
        self.assertEqual(avatar_field_lenght, 500)
        self.assertTrue(avatar_field_blank)


class TestQuestionModel(TestCase):
    """"""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user('user1', 'mail@mail.ltd', 'password')
        User.objects.create_user('user2', 'mail@mail.ltd', 'password')
        User.objects.create_user('user3', 'mail@mail.ltd', 'password')

    def test_question_create(self):
        user1 = User.objects.get(pk=1)
        q1, created = Question.objects.get_or_create(
                title='question1',
                text='lorem ipsum dolor',
                author=user1,
        )
        self.assertTrue(created)
        self.assertEqual(q1.title, 'question1')
        self.assertEqual(q1.text, 'lorem ipsum dolor')
        self.assertEqual(q1.author, user1)
        self.assertFalse(q1.tags.exists(), 'no tags!')


class TestAnswerModel(TestCase):
    """"""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user('user1', 'mail@mail.ltd', 'password')

    def test_question_create(self):
        user1 = User.objects.get(pk=1)
        q1, _ = Question.objects.get_or_create(
                title='question1',
                text='lorem ipsum dolores',
                author=user1,
        )
        a = Answer.objects.create(
                question=q1,
                author=user1,
                text='Lorem ipsum dolor sit amet, consectetur adipiscing elit'
        )

        self.assertEqual(a.question, q1)
        self.assertEqual(a.author, user1)
        self.assertEqual(a.text, 'Lorem ipsum dolor sit amet, consectetur adipiscing elit')


class TestTagModel(TestCase):
    """"""

    def test_tag_create(self):
        tag = Tag.objects.create(
                title='tag1'
        )
        self.assertEqual(tag.title, 'tag1')
        with self.assertRaises(IntegrityError):
            Tag.objects.create(title='tag1')


class TestVoteModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user('user1', 'mail@mail.ltd', 'password')
        cls.q1 = Question.objects.create(
                title='question1',
                text='lorem ipsum dolores',
                author=cls.user1
        )
        cls.a1 = Answer.objects.create(
                question=cls.q1,
                author=cls.user1,
                text='Lorem ipsum dolor sit amet, consectetur adipiscing elit'
        )

        cls.qv1 = Vote.objects.create(
                author=cls.user1,
                question=cls.q1
        )
        cls.av1 = Vote.objects.create(
                author=cls.user1,
                answer=cls.a1
        )

    def test_vote_create(self):
        self.assertEqual(self.qv1.author, self.user1)
        self.assertEqual(self.qv1.question, self.q1)
        self.assertIsNone(self.qv1.answer)
        self.assertEqual(self.av1.author, self.user1)
        self.assertEqual(self.av1.answer, self.a1)
        self.assertIsNone(self.av1.question)

    def test_unique_votes_question(self):
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                    author=self.user1,
                    question=self.q1
            )

    def test_unique_totes_qnswer(self):
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                    author=self.user1,
                    answer=self.a1
            )
