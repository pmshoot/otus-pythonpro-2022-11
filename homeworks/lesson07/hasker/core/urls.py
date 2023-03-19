"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path

from hasker.views import account, hasker

urlpatterns = [
    path('', hasker.index, name='index'),
    path('ask/', hasker.ask, name='ask'),
    # path('search/', hasker.QuestionSearch.as_view()),
    # path('tag/<str: tag>/', hasker.QuestionSearch.as_view()),
    #
    path('question/<str:pk>/', hasker.question_detail, name='question_detail'),
    # path('answer/<str:pk>/', hasker.answer_detail, name='answer_detail'),
    # path('question/<str: pk>/right', hasker.QuestionRight.as_view()),
    # path('question/<str: pk>/rating', hasker.QuestionRating.as_view()),
    # path('answer/<str: pk>/rating', hasker.AnswerRating.as_view()),
    #
    path('account/register/', account.register, name='register'),
    path('account/profile/', account.profile, name='profile'),
    path('account/', include('django.contrib.auth.urls')),
    # path('logout/', account.UserProfile.as_view()),
    # path('signup/', account.UserProfile.as_view()),
    # path('settings/', account.UserProfile.as_view()),

    # path('admin/', admin.site.urls),
]
