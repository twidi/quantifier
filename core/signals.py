from datetime import datetime, timedelta, timezone

from django.contrib import messages
from django.contrib.auth import user_logged_in, user_logged_out
from django.utils.translation import gettext_lazy as _


def on_user_logged_in(sender, request, user, **kwargs):
    if user.is_authenticated:
        if user.date_joined is not None and user.date_joined < datetime.now(timezone.utc) - timedelta(minutes=2):
            messages.success(request, _("Welcome back, %(user)s!") % {"user": user.username})
        else:
            messages.success(request, _("Welcome, %(user)s!") % {"user": user.username})
    return None


def on_user_logged_out(sender, request, user, **kwargs):
    messages.info(request, _("You are now logged out!"))
    return None


user_logged_in.connect(on_user_logged_in)
user_logged_out.connect(on_user_logged_out)
