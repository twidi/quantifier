"""quantifier URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from django.contrib import admin
from django.contrib.staticfiles import views as static_views
from django.urls import path, include, reverse_lazy, re_path
from django_registration.backends.one_step.views import RegistrationView

from core import views
from core.forms import CoreRegistrationForm

urlpatterns = [
    path(
        "accounts/register/",
        RegistrationView.as_view(
            form_class=CoreRegistrationForm,
            success_url=reverse_lazy(settings.LOGIN_REDIRECT_URL),
        ),
        name="django_registration_register",
    ),
    path("accounts/", include("django_registration.backends.one_step.urls")),
    path(
        "accounts/password_change/",
        views.PasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),

    path("", views.HomeView.as_view(), name="index"),
    path("projects/", views.ProjectsView.as_view(), name="projects"),
    path("project/create/", views.ProjectCreateView.as_view(), name="project_create"),
    path(
        "project/<int:project_pk>/",
        views.ProjectDetailsView.as_view(),
        name="project_details",
    ),
    path(
        "project/<int:project_pk>/edit/",
        views.ProjectEditView.as_view(),
        name="project_edit",
    ),
    path(
        "project/<int:project_pk>/delete/",
        views.ProjectDeleteView.as_view(),
        name="project_delete",
    ),
    path(
        "project/<int:project_pk>/reorder/",
        views.ProjectReorderView.as_view(),
        name="project_reorder",
    ),
    path(
        "project/<int:project_pk>/quantities/",
        views.ProjectQuantitiesView.as_view(),
        name="quantities_list",
    ),
    path(
        "project/<int:project_pk>/quantity/create/",
        views.QuantityInProjectCreateView.as_view(),
        name="quantity_create",
    ),
    path(
        "project/<int:project_pk>/category/create/",
        views.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/",
        views.CategoryDetailsView.as_view(),
        name="category_details",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/edit/",
        views.CategoryEditView.as_view(),
        name="category_edit",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/delete/",
        views.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/reorder/",
        views.CategoryReorderView.as_view(),
        name="category_reorder",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/category/create/",
        views.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/quantity/create/",
        views.QuantityInCategoryCreateView.as_view(),
        name="quantity_in_category_create",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/quantities/",
        views.CategoryQuantitiesView.as_view(),
        name="quantities_list",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/quantity/<int:quantity_pk>/edit/",
        views.QuantityEditView.as_view(),
        name="quantity_edit",
    ),
    path(
        "project/<int:project_pk>/category/<int:category_pk>/quantity/<int:quantity_pk>/delete/",
        views.QuantityDeleteView.as_view(),
        name="quantity_delete",
    ),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", static_views.serve),
        path("__debug__/", include("debug_toolbar.urls")),
    ]
