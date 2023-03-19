from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from hasker.forms import ProfileUser, RegisterUser

AUTH_USER = get_user_model()


def register(request, *args, **kwargs):
    if request.method == 'POST':
        """save new user"""
        form = RegisterUser(request.POST)
        if form.is_valid():
            object = form.save(commit=False)
            object.save()
            return HttpResponseRedirect(reverse('login'))
        else:
            return render(request, 'registration/register.html', context={'form': form})
    form = RegisterUser()
    return render(request, 'registration/register.html', context={'form': form})


def profile(request, *args, **kwargs):
    if request.user.is_authenticated:
        if request.method == 'POST':
            """save changed user profile"""
            form = ProfileUser(request.POST)
            if form.is_valid():
                form.save()
                return render(request, 'registration/profile.html')
            else:
                return render(request, 'registration/profile.html', context={'form': form})
        form = ProfileUser()
        return render(request, 'registration/profile.html', context={'form': form})
    return HttpResponseRedirect(reverse('login'))

# class UserProfile(DetailView):
#     model = AUTH_USER
#
#
# class UserCreate(CreateView):
#     model = AUTH_USER
