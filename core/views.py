import contextlib
from datetime import datetime
from functools import cached_property
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    PasswordChangeView as DjangoPasswordChangeView,
    PasswordResetConfirmView as DjangoPasswordResetConfirmView,
)
from django.db.models import Count
from django.forms import TextInput
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView, ListView
from django.views.generic.edit import DeleteView, CreateView, UpdateView
from mptt.utils import get_cached_trees

from .forms import (
    CategoryCreateForm,
    CategoryEditForm,
    CategoryReorderForm,
    QuantityInProjectForm,
    QuantityInCategoryForm,
    CategoryDeleteForm,
    ProjectDeleteForm,
    ProjectCreateForm,
    ProjectEditForm,
    ProjectReorderForm,
    QuantityEditForm,
    QuantityDeleteForm,
)
from .models import Project, Category, Quantity, Intervals, get_dates_interval, get_prev_and_next_dates_interval
from . import signals


class PasswordChangeView(DjangoPasswordChangeView):
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        messages.info(self.request, _("Your new password was just saved!"))
        return super().form_valid(form)


class PasswordResetConfirmView(DjangoPasswordResetConfirmView):
    success_url = reverse_lazy("index")
    post_reset_login = True

    def form_valid(self, form):
        messages.info(self.request, _("Your new password was just saved!"))
        return super().form_valid(form)


class DateAndIntervalMixin:
    def dispatch(self, request, *args, **kwargs):
        self.date = None
        self.interval = None
        self.date, self.interval, error_date = get_date_and_interval_from_querystring(
            self.request, getattr(self, "project", None)
        )
        if error_date:
            return HttpResponseRedirect(
                f"{request.path}?date={self.date}" + (f"&interval={self.interval}" if self.interval else "")
            )
        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def start_and_end_dates(self):
        return get_dates_interval(self.date, self.interval or Intervals.daily)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs,
            date=self.date,
            date_str=self.date.strftime("%Y-%m-%d"),
        )
        if self.interval:
            context.update(
                dict(
                    interval=self.interval.value,
                    interval_name=self.interval.unit_name,
                )
            )

        context["prev_date"], context["next_date"] = get_prev_and_next_dates_interval(
            self.date, self.interval or Intervals.daily
        )
        return context


def get_date_from_querystring(request) -> tuple[datetime.date, Optional[str]]:
    date_error = None
    if date_str := (request.GET.get("date") or "").strip():
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date(), None
        except (ValueError, TypeError):
            date_error = date_str

    return datetime.now().date(), date_error


def get_interval_from_querystring(request) -> Optional[Intervals]:
    if interval_str := request.GET.get("interval") or None:
        with contextlib.suppress(ValueError):
            return Intervals(interval_str)
    return None


def get_date_and_interval_from_querystring(
    request, project: Optional[Project] = None
) -> tuple[datetime.date, Optional[Intervals], Optional[str]]:
    date, error_date = get_date_from_querystring(request)
    interval = get_interval_from_querystring(request) or (Intervals(project.interval) if project else None)
    return date, interval, error_date


class HomeView(DateAndIntervalMixin, TemplateView):
    template_name = "index.html"


class ProjectsView(DateAndIntervalMixin, LoginRequiredMixin, TemplateView):
    template_name = "projects.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for project in self.request.user.cached_projects:
            if project.nb_categories > 1:
                if project.has_interval or self.interval not in (None, Intervals.none):
                    project.summed_quantities = project.get_summed_quantities(self.date, self.interval)
                else:
                    project.summed_quantities = project.get_summed_quantities()
        return context


class OwnedProjectMixin(DateAndIntervalMixin, LoginRequiredMixin, UserPassesTestMixin):
    @cached_property
    def project(self):
        if (project := self.request.user.get_project(self.kwargs.get("project_pk"))) is None:
            raise Http404()
        return project

    def get_context_data(self, **kwargs):
        context = kwargs | {
            "project": self.project,
            "current_project": self.project,
            "main_object": self.project,
            "main_category": self.project.root_category,
            "current_category": None,
            "categories": self.project.main_categories,
        }
        return super().get_context_data(**context)

    def test_func(self):
        return self.request.user == self.project.owner


class OwnedCategoryMixin(OwnedProjectMixin):
    @cached_property
    def category(self):
        if (category := self.project.get_category(self.kwargs.get("category_pk"))) is None:
            raise Http404()
        return category

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs) | {
            "category": self.category,
            "main_object": self.category,
            "main_category": self.category,
            "current_category": self.category,
            "categories": self.category.get_children(),
        }


class ProjectOrCategoryDetailsMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.project.has_interval or self.interval not in (None, Intervals.none):
            self.project.summed_quantities = self.project.get_summed_quantities(self.date, self.interval)
        else:
            self.project.summed_quantities = self.project.get_summed_quantities()

        return context


class ProjectOrCategoryDetailsBaseView(ProjectOrCategoryDetailsMixin, DetailView):
    template_name = "project_or_category_details.html"


class ProjectDetailsView(OwnedProjectMixin, ProjectOrCategoryDetailsBaseView):
    model = Project
    pk_url_kwarg = "project_pk"

    def get_object(self):
        return self.project


class CategoryDetailsView(OwnedCategoryMixin, ProjectOrCategoryDetailsBaseView):
    model = Category
    pk_url_kwarg = "category_pk"

    def get_object(self):
        return self.category


class ProjectFormViewMixin:
    model = Project

    @cached_property
    def next_category(self):
        if (
            (next := self.request.GET.get("next", "")).startswith("category:")
            and (category_id := next.split(":")[1])
            and category_id.isdigit()
        ):
            return Category.objects.filter(project__owner=self.request.user, pk=category_id).first()
        return None

    def get_success_url(self):
        with_interval = bool(self.interval)
        if self.next_category:
            url = self.next_category.get_absolute_url()
        elif isinstance(self, ProjectDeleteView):
            with_interval = False
            url = settings.USER_HOME_URL
        else:
            url = self.object.get_absolute_url()

        url += f"?date={self.date}" + (f"&interval={self.interval}" if with_interval else "")

        return url


class ProjectCreateView(LoginRequiredMixin, DateAndIntervalMixin, ProjectFormViewMixin, CreateView):
    template_name = "project_form.html"
    form_class = ProjectCreateForm

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ProjectEditView(OwnedProjectMixin, ProjectFormViewMixin, UpdateView):
    template_name = "project_form.html"
    form_class = ProjectEditForm
    pk_url_kwarg = "project_pk"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, delete_form=ProjectDeleteForm(instance=self.project))


class ProjectDeleteView(OwnedProjectMixin, ProjectFormViewMixin, DeleteView):
    template_name = "project_delete.html"
    form_class = ProjectDeleteForm
    model = Project
    pk_url_kwarg = "project_pk"

    def get_success_url(self):
        return settings.USER_HOME_URL

    def get_form_kwargs(self):
        # not done by the default delete view because it uses a simple form, but here we use a model form
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs


class ProjectReorderView(OwnedProjectMixin, ProjectFormViewMixin, UpdateView):
    pk_url_kwarg = "project_pk"
    form_class = ProjectReorderForm
    template_name = "project_reorder_form.html"

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {"user": self.request.user}


class CategoryFormViewMixin:
    model = Category

    def get_queryset(self):
        return self.project.categories.all()

    def get_context_data(self, **kwargs):
        next = f"category:{self.next_category.pk}" if self.next_category else None
        return super().get_context_data(**kwargs, next=next)

    @cached_property
    def next_category(self):
        if (
            (next := self.request.GET.get("next", "")).startswith("category:")
            and (category_id := next.split(":")[1])
            and category_id.isdigit()
        ):
            return Category.objects.filter(project__owner=self.request.user, pk=category_id).first()
        return None

    def get_success_url(self):
        if self.next_category:
            url = self.next_category.get_absolute_url()
        else:
            url = self.project.get_absolute_url()

        url += f"?date={self.date}" + (f"&interval={self.interval}" if self.interval else "")

        return url


class CategoryCreateView(OwnedProjectMixin, CategoryFormViewMixin, CreateView):
    form_class = CategoryCreateForm
    template_name = "category_form.html"

    @cached_property
    def parent_category(self):
        if parent_category_pk := self.kwargs.get("category_pk"):
            return get_object_or_404(self.project.categories.all(), pk=parent_category_pk)
        return None

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {
            "project": self.project,
            "parent_category": self.parent_category,
        }


class CategoryEditView(OwnedCategoryMixin, CategoryFormViewMixin, UpdateView):
    pk_url_kwarg = "category_pk"
    form_class = CategoryEditForm
    template_name = "category_form.html"


class CategoryReorderView(OwnedCategoryMixin, CategoryFormViewMixin, UpdateView):
    pk_url_kwarg = "category_pk"
    form_class = CategoryReorderForm
    template_name = "category_reorder_form.html"


class CategoryDeleteView(OwnedCategoryMixin, CategoryFormViewMixin, DeleteView):
    form_class = CategoryDeleteForm
    pk_url_kwarg = "category_pk"
    template_name = "category_delete_form.html"

    def get_queryset(self):
        return self.project.categories.all()

    def get_form_kwargs(self):
        # not done by the default delete view because it uses a simple form, but here we use a model form
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs


class QuantityCreateBaseView(CreateView):
    template_name = "quantity_form.html"
    model = Quantity

    def get_form_kwargs(self):
        min_date, max_date, initial_date = QuantityInProjectForm.get_date_args(self.project, self.date, self.interval)
        result = super().get_form_kwargs() | {"min_date": min_date, "max_date": max_date}
        result["initial"]["date"] = initial_date
        return result

    def get_context_data(self, **kwargs):
        if self.next_category:
            next = f"category:{self.next_category.pk}"
        elif self.next_project:
            next = f"project:{self.next_project.pk}"
        else:
            next = settings.USER_HOME_URL
        return super().get_context_data(**kwargs, next=next)

    @cached_property
    def next_project(self):
        if (
            (next := self.request.GET.get("next", "")).startswith("project:")
            and (project_id := next.split(":")[1])
            and project_id.isdigit()
        ):
            return self.request.user.get_project(project_id)
        return None

    @cached_property
    def next_category(self):
        if (
            (next := self.request.GET.get("next", "")).startswith("category:")
            and (category_id := next.split(":")[1])
            and category_id.isdigit()
        ):
            return Category.objects.filter(project__owner=self.request.user, pk=category_id).first()
        return None

    def get_success_url(self):
        with_interval = bool(self.interval)
        if self.request.GET.get("next") == "projects":
            url = settings.USER_HOME_URL
            with_interval = False
        elif self.next_category:
            url = self.next_category.get_absolute_url()
        elif self.next_project:
            url = self.next_project.get_absolute_url()
        else:
            url = self.project.get_absolute_url()

        url += f"?date={self.date}" + (f"&interval={self.interval}" if with_interval else "")

        return url


class QuantityInProjectCreateView(OwnedProjectMixin, QuantityCreateBaseView):
    form_class = QuantityInProjectForm

    def get_form_kwargs(self):
        self.project.summed_quantities = self.project.get_summed_quantities(
            date=self.date if self.project.has_interval else None
        )
        return super().get_form_kwargs() | {"project": self.project}


class QuantityInCategoryCreateView(OwnedCategoryMixin, QuantityCreateBaseView):
    form_class = QuantityInCategoryForm

    @cached_property
    def next_project(self):
        return super().next_project or self.project

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {"category": self.category}


class QuantitiesBaseView(ProjectOrCategoryDetailsMixin, ListView):
    template_name = "quantities.html"
    context_object_name = "quantities"
    paginate_by = 25

    @cached_property
    def categories(self):
        if self.request.GET.get("with-children", "1") == "0":
            return [self.category]
        return self.category.get_descendants(include_self=True)

    @cached_property
    def prepared_categories(self):
        categories = {category.id: category for category in self.project.cached_categories}
        for category in categories.values():
            category.in_between_ancestors = tuple(category.get_ancestors(include_self=False))[
                self.category.level + 1 :
            ]
        return categories

    @property
    def queryset(self):
        queryset = Quantity.objects.filter(category__in=self.categories)
        start_date, end_date = self.start_and_end_dates
        queryset = queryset.filter(date__gte=start_date, date__lte=end_date)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs, with_children=self.request.GET.get("with-children", "1") != "0")
        if paginator := context.get("paginator"):
            context["elided_pages"] = paginator.get_elided_page_range(
                number=context["page_obj"].number,
                on_each_side=2,
                on_ends=1,
            )
        for quantity in context["quantities"]:
            quantity.category = self.prepared_categories[quantity.category_id]
        return context


class ProjectQuantitiesView(OwnedProjectMixin, QuantitiesBaseView):
    @cached_property
    def category(self):
        return self.project.root_category


class CategoryQuantitiesView(OwnedCategoryMixin, QuantitiesBaseView):
    pass


class QuantityFormViewMixin(OwnedCategoryMixin):
    model = Quantity
    pk_url_kwarg = "quantity_pk"

    def get_queryset(self):
        return self.category.quantities.all()

    def get_context_data(self, **kwargs):
        next = f"category:{self.next_category.pk}" if self.next_category else None
        return super().get_context_data(**kwargs, next=next)

    @cached_property
    def next_category(self):
        if (
            (next := self.request.GET.get("next", "")).startswith("category:")
            and (category_id := next.split(":")[1])
            and category_id.isdigit()
        ):
            return Category.objects.filter(project__owner=self.request.user, pk=category_id).first()
        return None

    def get_success_url(self):
        with_interval = bool(self.interval)
        if self.next_category:
            url = self.next_category.get_quantities_url()
        else:
            url = self.category.project.get_quantities_url()

        url += f"?date={self.date}" + (f"&interval={self.interval}" if with_interval else "")

        if self.request.GET.get("with-children") == "0":
            url += "&with-children=0"

        return url


class QuantityEditView(QuantityFormViewMixin, UpdateView):
    form_class = QuantityEditForm
    template_name = "quantity_form.html"


class QuantityDeleteView(QuantityFormViewMixin, DeleteView):
    form_class = QuantityDeleteForm
    template_name = "quantity_delete_form.html"

    def get_form_kwargs(self):
        # not done by the default delete view because it uses a simple form, but here we use a model form
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs
