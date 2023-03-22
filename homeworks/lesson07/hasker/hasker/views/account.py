from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from hasker.forms import RegisterUserForm, UpdateUserForm, UserProfileForm

AUTH_USER = get_user_model()


def register(request, *args, **kwargs):
    if request.method == 'POST':
        """save new user"""
        form = RegisterUserForm(request.POST)
        # p_form = UserProfileForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('login'))
    else:
        form = RegisterUserForm()
        # p_form = UserProfileForm()
    return render(request, 'registration/register.html', context={'form': form})


@login_required
def profile(request, *args, **kwargs):
    if request.method == 'POST':
        """save changed user profile"""
        u_form = UpdateUserForm(request.POST, instance=request.user)
        p_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            if u_form.has_changed():
                user = u_form.save()
            if p_form.has_changed():
                profile = p_form.save(commit=False)
                profile.save()
            return render(request, 'registration/profile.html', context={'u_form': u_form, 'p_form': p_form})
    else:
        u_form = UpdateUserForm(instance=request.user)
        p_form = UserProfileForm(instance=request.user.profile)
    return render(request, 'registration/profile.html', context={'u_form': u_form, 'p_form': p_form})
