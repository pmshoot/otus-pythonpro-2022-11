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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from hasker.views import account, hasker

urlpatterns = [
    path('', hasker.index, name='index'),
    path('ask/', hasker.ask, name='ask'),
    path('question/<str:pk>/', hasker.question_detail, name='question_detail'),
    path('account/register/', account.register, name='register'),
    path('account/profile/', account.profile, name='profile'),
    path('accounts/', include('django.contrib.auth.urls')),
]

urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
