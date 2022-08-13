import contextlib
from datetime import datetime

from django.conf import settings
from django.urls import reverse

from .models import Intervals


def default_context(request):
    today = date = datetime.now().date()
    if date_str := (request.GET.get("date") or "").strip():
        with contextlib.suppress(ValueError):
            date = datetime.strptime(date_str, "%Y-%m-%d").date()

    context = {
        "today": today,
        "current_date": date,
        "intervals": list(Intervals),
    }

    if request.user and request.user.is_authenticated:
        context["home_url"] = settings.USER_HOME_URL
        context["projects"] = request.user.cached_projects
        context["nb_projects"] = len(context["projects"])

    return context
