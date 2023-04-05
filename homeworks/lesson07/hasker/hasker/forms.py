from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

from hasker.models.account import UserProfile
from hasker.models.hasker import Question

AUTH_USER = get_user_model()


class BootstrapMixin:
    """Установка классов css для форм"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class QuestionForm(BootstrapMixin, forms.ModelForm):
    """Форма создания вопроса"""
    tag = forms.CharField(label='Теги', help_text='Не более 3-х тегов', required=False)

    class Meta:
        model = Question
        fields = ('title', 'text')
        widgets = {
            'text': forms.Textarea(attrs={'rows': 5}),
            'tag': forms.TextInput,
        }

    def clean_tag(self):
        text = self.cleaned_data['tag']
        if len(text.split(',')) > 3:
            raise ValidationError('Не более 3-х тегов на вопрос')
        return text


class AnswerForm(BootstrapMixin, forms.Form):
    """Форма создания ответа"""
    answer = forms.CharField(label='Ответ', widget=(forms.Textarea(attrs={'required': True, 'rows': 5})))


class RegisterUserForm(BootstrapMixin, UserCreationForm):
    """Форма регистрации нового пользователя"""
    class Meta(UserCreationForm.Meta):
        model = AUTH_USER
        fields = ('username', 'email')


class UpdateUserForm(BootstrapMixin, UserChangeForm):
    """Форма изменения данных пользователя"""
    password = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['readonly'] = True

    class Meta(UserChangeForm.Meta):
        fields = ('username', 'email',)


class UserProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('avatar',)

    def clean_avatar(self):
        """
        max size: 1000x1000px
        available ext: jpeg, png, gif
        """
        avatar = self.cleaned_data['avatar']
        if avatar:
            try:
                w, h = get_image_dimensions(avatar)
                # validate dimensions
                max_width = max_height = 1000
                if w > max_width or h > max_height:
                    raise forms.ValidationError(
                            u'Please use an image that is '
                            '%s x %s pixels or smaller.' % (max_width, max_height))
                # validate content type
                main, sub = avatar.content_type.split('/')
                if not (main == 'image' and sub in ['jpg', 'jpeg', 'gif', 'png']):
                    raise forms.ValidationError(u'Please use a JPEG, '
                                                'GIF or PNG image.')
                # validate file size
                if len(avatar) > (120 * 1024):
                    raise forms.ValidationError(
                            u'Avatar file size may not exceed 20k.')
            except AttributeError:
                """
                Handles case when we are updating the user profile
                and do not supply a new avatar
                """
                pass
        return avatar
