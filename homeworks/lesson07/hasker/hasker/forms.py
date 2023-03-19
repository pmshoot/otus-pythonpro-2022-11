from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from hasker.models import Question

AUTH_USER = get_user_model()


class QuestionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    class Meta:
        model = Question
        fields = ('title', 'text', 'tag')
        widgets = {
            # 'text': forms.Textarea(attrs={'rows': 10}),
            # 'title': forms.TextInput(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'rows': 5}),
            # 'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'tag': forms.TextInput,
        }


class RegisterUser(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    class Meta(UserCreationForm.Meta):
        model = AUTH_USER
        fields = ('username', 'email', 'avatar')
        # widgets = {
        #     'password': forms.PasswordInput,
        # }

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']
        return avatar


class ProfileUser(forms.ModelForm):
    class Meta:
        model = AUTH_USER
        fields = ('email', 'avatar')


class QuestionNewAnswerForm(forms.Form):
    answer = forms.CharField(label='Ответ', widget=(forms.Textarea(attrs={'required': True, 'rows': 5})))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
