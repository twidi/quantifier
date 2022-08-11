from __future__ import annotations

import calendar
import enum
import re
from datetime import datetime, timedelta
from functools import cached_property
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q, Sum, Deferrable, Count
from django.urls import reverse
from django.utils import timezone
from mptt.managers import TreeManager

from mptt.models import MPTTModel
from mptt.querysets import TreeQuerySet
from mptt.utils import get_cached_trees
from orderable.managers import OrderableManager
from orderable.models import Orderable
from orderable.querysets import OrderableQueryset

from .fields import TreeForeignKeyNoRoot


class User(AbstractUser):
    """We use a custom user model to be able to add fields later"""

    @cached_property
    def cached_projects(self):
        queryset = self.projects.all().annotate(nb_categories=Count("categories")).order_by("sort_order")
        queryset._fetch_all()
        return queryset

    def get_project(self, project_pk):
        if not project_pk:
            return None
        try:
            return [project for project in self.cached_projects if project.pk == project_pk][0]
        except IndexError:
            return None


class Intervals(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"
    none = "none"

    def __str__(self):
        return self.value

    @classmethod
    def as_choices(cls):
        return tuple((interval.value, interval.value) for interval in cls)

    @property
    def unit_name(self):
        if self == Intervals.daily:
            return "day"
        if self == Intervals.weekly:
            return "week"
        if self == Intervals.monthly:
            return "month"
        if self == Intervals.yearly:
            return "year"
        if self == Intervals.none:
            return "all time"
        return "none"

    def count_in(self, interval: Intervals, date: datetime.date) -> float:
        if self == Intervals.none or interval == Intervals.none:
            return 0
        if self == interval:
            return 1
        if self > interval:
            return 1 / interval.count_in(self, date)
        if self == Intervals.daily:
            if interval == Intervals.weekly:
                return 7
            if interval == Intervals.monthly:
                return calendar.monthrange(date.year, date.month)[1]
            # if interval == Intervals.yearly:
            return 365 + calendar.isleap(date.year)
        if self == Intervals.weekly:
            return Intervals.daily.count_in(interval, date) / 7
        if self == Intervals.monthly:
            if interval == Intervals.yearly:
                return 12
            return Intervals.daily.count_in(interval, date) / calendar.monthrange(date.year, date.month)[1]
        # if self == Intervals.yearly:
        return Intervals.daily.count_in(interval, date) / (365 + calendar.isleap(date.year))

    def __lt__(self, other):
        return OrderedIntervals[self] < OrderedIntervals[other]

    def __le__(self, other):
        return OrderedIntervals[self] <= OrderedIntervals[other]


OrderedIntervals = {interval.value: index for index, interval in enumerate(Intervals)}


def get_dates_interval(date: datetime.date, interval: Intervals) -> tuple[datetime.date, datetime.date]:
    if interval == Intervals.daily:
        start_date = end_date = date
    elif interval == Intervals.weekly:
        start_date = date - timedelta(days=date.weekday())
        end_date = start_date + timedelta(days=6)
    elif interval == Intervals.monthly:
        start_date = date.replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    elif interval == Intervals.yearly:
        start_date, end_date = date.replace(month=1, day=1), date.replace(month=12, day=31)
    else:
        return datetime.min, datetime.max
    return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())


def get_prev_and_next_dates_interval(date: datetime.time, interval: Intervals) -> tuple[datetime.date, datetime.date]:
    if not interval or interval == Intervals.daily:
        return date - relativedelta(days=1), date + relativedelta(days=1)
    if interval == Intervals.weekly:
        return date - relativedelta(weeks=1), date + relativedelta(weeks=1)
    if interval == Intervals.monthly:
        return date - relativedelta(months=1), date + relativedelta(months=1)
    # if interval == Intervals.yearly:
    return date - relativedelta(years=1), date + relativedelta(years=1)


def get_interval_str(date: datetime.date, interval: Intervals):
    start_date, end_date = get_dates_interval(date, interval)

    if interval == Intervals.daily:
        return date.strftime("%d %B %Y")

    if interval == Intervals.weekly:
        result = f'Week {date.strftime("%W")} of {date.strftime("%Y")}'
        if start_date.month == end_date.month:
            result += f' ({start_date.day} to {end_date.day} {end_date.strftime("%B")})'
        elif start_date.year == end_date.year:
            result += f' ({start_date.strftime("%-d %B")} to {end_date.strftime("%-d %B")})'
        else:
            result += f' ({start_date.strftime("%-d %B")} to {end_date.strftime("%-d %B %Y")})'
        return result

    if interval == Intervals.monthly:
        return date.strftime("%B %Y")

    if interval == Intervals.yearly:
        return f'Year {date.strftime("%Y")}'

    return "All time"


class Project(Orderable, models.Model):
    """A project is where some quantities are saved in categories."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    interval = models.CharField(
        max_length=10,
        choices=Intervals.as_choices(),
        default=Intervals.none.value,
    )
    interval_quantity = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Limit quantity",
        help_text="The quantity that will be reset at the beginning of each day, week, month or year (or never if no interval)",
    )
    quantity_name = models.CharField(
        max_length=100,
        help_text="The name of the thing to count: euros, minutes, kilometers, etc.",
    )
    quick_add_quantities = models.TextField(
        blank=True,
        help_text="A list of quantities available as quick add buttons. Each quantity is separated by a comma. Example: 1,2,5,10,20,50,100",
        validators=[
            RegexValidator(
                re.compile(r"^(\s*\d+\s*,)*\s*\d+\s*$"),
                message="Enter only digits separated by commas.",
                code="invalid",
            )
        ],
    )

    class Meta(Orderable.Meta):
        constraints = [
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_order_owner_uniq",
                fields=("owner", "sort_order"),
                deferrable=Deferrable.DEFERRED,
                violation_error_message="A project with this order already exists.",
            ),
        ]

    @property
    def has_interval_quantity(self):
        return self.interval_quantity is not None

    def get_unique_fields(self):
        """List field names that are unique_together with `sort_order`."""
        return ["owner"]

    def __str__(self):
        return self.name

    @property
    def short_description(self):
        if not self.has_interval_quantity:
            if not self.has_interval:
                return f"Cumulative amount, in {self.quantity_name}"
            return f"{self.get_interval_display().capitalize()} {self.quantity_name}"
        if not self.has_interval:
            return f"Total amount of {self.interval_quantity} {self.quantity_name}"
        return f"{self.get_interval_display().capitalize()} amount of {self.interval_quantity} {self.quantity_name}"

    def save(self, *args, **kwargs):
        # create a root category
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            self.categories.create(name="")

    @cached_property
    def visible_categories(self):
        queryset = self.cached_categories.filter(parent__isnull=False)
        queryset._result_cache = [category for category in self.cached_categories if category.parent_id]
        return queryset

    @cached_property
    def main_categories(self):
        queryset = self.cached_categories.filter(level=1)
        queryset._result_cache = [category for category in self.cached_categories if category.level == 1]
        return queryset

    @cached_property
    def quick_add_quantities_as_list(self) -> list[int]:
        try:
            return [int(q) for q in (self.quick_add_quantities or "").replace(" ", "").split(",")]
        except ValueError:
            return []

    def get_absolute_url(self):
        return reverse("project_details", kwargs={"project_pk": self.pk})

    def get_edit_url(self):
        return reverse("project_edit", kwargs={"project_pk": self.pk})

    def get_delete_url(self):
        return reverse("project_delete", kwargs={"project_pk": self.pk})

    def get_reorder_url(self):
        return reverse("project_reorder", kwargs={"project_pk": self.pk})

    def get_add_category_url(self):
        return reverse("category_create", kwargs={"project_pk": self.pk})

    def get_add_quantity_url(self):
        return reverse("quantity_create", kwargs={"project_pk": self.pk})

    def get_quantities_url(self):
        return reverse("quantities_list", kwargs={"project_pk": self.pk})

    @cached_property
    def has_interval(self):
        return self.interval != "none"

    @cached_property
    def interval_name(self):
        return Intervals(self.interval).unit_name

    @cached_property
    def root_category(self):
        self.cached_categories
        return self.__dict__["root_category"]

    @cached_property
    def cached_categories(self):
        categories = self.categories.all()
        categories._fetch_all()
        self.__dict__["root_category"] = get_cached_trees(categories)[0]
        return categories

    def get_category(self, category_pk):
        if not category_pk:
            return None
        try:
            return [category for category in self.cached_categories if category.pk == category_pk][0]
        except IndexError:
            return None

    def get_ancestors_categories(self, category, ascending=False, include_it=False):
        result = [category] if include_it else []
        while category.parent_id:
            result.append(category.parent)
            category = category.parent

        return result if ascending else result[::-1]

    def get_descendant_categtories(self, category, include_it=False):
        found = False
        result = []
        for cat in self.cached_categories:
            if not found:
                if cat.pk == category.pk:
                    found = True
                    if include_it:
                        result.append(category)
                continue
            if cat.level <= category.level:
                break
            result.append(cat)
        return result

    def get_siblings_categories(self, category, include_it=False):
        result = category.parent.get_children()
        if not include_it:
            result = [cat for cat in result if cat.pk != category.pk]
        return result

    def get_summed_quantities(
        self, date: Optional[datetime.date] = None, interval: Optional[Intervals] = None
    ) -> dict[Category, dict[str, int]]:
        """Return a dict with as key the category id, and as value, the sum of all quantities in the category."""
        sum_kwargs = {}
        if not self.has_interval and not interval:
            interval = Intervals.none
        elif interval is None:
            interval = self.interval

        alltime = self.has_interval and interval == Intervals.none
        no_details = alltime or self.has_interval and Intervals(interval) < Intervals(self.interval)

        if date:
            if not alltime:
                start_date, end_date = get_dates_interval(date, interval)
                sum_kwargs["filter"] = Q(quantities__datetime__gte=start_date) & Q(quantities__datetime__lte=end_date)

        summed_values = dict(
            self.categories.annotate(summed_values=Sum("quantities__value", default=0, **sum_kwargs)).values_list(
                "id", "summed_values"
            )
        )
        result = {category: {"self_used": summed_values[category.id]} for category in self.cached_categories}

        def update_count(category, is_root=False):
            for sub_category in (children := category.get_children()):
                update_count(sub_category)

            res_cat = result[category]
            res_cat["has_children"] = bool(children)

            interval_quantity = self.interval_quantity
            expected_quantity = category.expected_quantity
            if self.has_interval:
                factor = Intervals(self.interval).count_in(interval, date)
                if interval_quantity:
                    interval_quantity = round(interval_quantity * factor)
                if expected_quantity:
                    expected_quantity = round(expected_quantity * factor)

            if expected_quantity:
                res_cat["self_used_not_expected"] = 0
                res_cat["self_expected"] = expected_quantity
                res_cat["self_unexpected"] = max(0, res_cat["self_used"] - res_cat["self_expected"])
                res_cat["self_expected_not_used"] = (
                    res_cat["self_expected"] - res_cat["self_used"] + res_cat["self_unexpected"]
                )
            else:
                res_cat["self_used_not_expected"] = res_cat["self_used"]
                res_cat["self_expected"] = res_cat["self_unexpected"] = res_cat["self_expected_not_used"] = 0

            keys = ["used"]
            if not alltime and not no_details:
                keys.extend(["used_not_expected", "expected", "unexpected", "expected_not_used"])

                if expected_quantity:
                    for key in ["used_not_expected", "expected"]:
                        res_cat[key] = res_cat[f"self_{key}"]

                    res_cat["used"] = res_cat["self_used"] + sum(
                        result[sub_category]["used"] for sub_category in category.get_children()
                    )
                    res_cat["unexpected"] = max(0, res_cat["used"] - res_cat["self_expected"])
                    res_cat["expected_not_used"] = res_cat["expected"] - res_cat["used"] + res_cat["unexpected"]

                    keys = ["used"]

            for key in keys:
                res_cat[key] = res_cat[f"self_{key}"] + sum(
                    result[sub_category][key] for sub_category in category.get_children()
                )

            if is_root and not alltime and not no_details and self.has_interval_quantity:
                res_cat |= {
                    "available": interval_quantity - res_cat["used"],
                    "really_available": (
                        really_available := interval_quantity
                        - (res_cat["used_not_expected"] + res_cat["unexpected"] + res_cat["expected"])
                    ),
                    "total_unexpected": really_available + res_cat["used_not_expected"] + res_cat["unexpected"],
                }

        update_count(self.root_category, is_root=True)

        return result


class CategoryQuerySet(OrderableQueryset, TreeQuerySet):
    def all(self):
        queryset = super().all()
        if self._result_cache is not None:
            queryset._result_cache = self._result_cache
        return queryset

    def _iterator(self, use_chunked_fetch, chunk_size):
        if self._result_cache is not None:
            yield from self._result_cache
        return super()._iterator(use_chunked_fetch, chunk_size)


class CategoryManager(OrderableManager.from_queryset(CategoryQuerySet), TreeManager):
    pass


class Category(Orderable, MPTTModel):
    """A category belongs to a project and contains some quantities and some sub-categories"""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = TreeForeignKeyNoRoot("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    expected_quantity = models.PositiveIntegerField(null=True, blank=True)

    objects = CategoryManager()

    class MPTTMeta:
        order_insertion_by = ["sort_order"]

    class Meta(Orderable.Meta):
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_name_no_parent_uniq",
                fields=("project", "name"),
                condition=Q(parent__isnull=True),
                violation_error_message="A category with this name already exists in this project.",
            ),
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_name_parent_uniq",
                fields=("parent", "name"),
                condition=Q(parent__isnull=False),
                violation_error_message="A sub-category with this name already exists in this category.",
            ),
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_order_parent_uniq",
                fields=("parent", "sort_order"),
                deferrable=Deferrable.DEFERRED,
                violation_error_message="A category with this order already exists in this category.",
            ),
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_no_parent_uniq",
                fields=("project",),
                condition=Q(parent__isnull=True),
                violation_error_message="A project can only have one root category",
            ),
        ]

    def get_unique_fields(self):
        """List field names that are unique_together with `sort_order`."""
        return ["project", "parent"]

    def __str__(self):
        return self.name

    def validate_constraints(self, exclude=None):
        if exclude and self.project_id:
            # to allow checking the constraints related to the project
            exclude.discard("project")
        return super().validate_constraints(exclude)

    def validate_unique(self, exclude=None):
        # fix a bug in Orderable where `exclude` is seen as a list, not as a set as exepected by django
        if self._is_sort_order_unique_together_with_something():
            if exclude is None:
                exclude = set()
            if "sort_order" not in exclude:
                exclude.add("sort_order")
        # we force `super(Orderable, self) `to avoid calling the `Orderable.validate_unique` method that we just rewrote
        return super(Orderable, self).validate_unique(exclude=exclude)

    def get_ancestors(self, ascending=False, include_self=False):
        queryset = super().get_ancestors(ascending, include_self)
        queryset._result_cache = self.project.get_ancestors_categories(self, ascending, include_it=include_self)
        return queryset

    def get_descendants(self, include_self=False):
        queryset = super().get_descendants(include_self)
        queryset._result_cache = self.project.get_descendant_categtories(self, include_it=include_self)
        return queryset

    def get_siblings(self, include_self=False):
        queryset = super().get_siblings(include_self)
        queryset._result_cache = self.project.get_siblings_categories(self, include_it=include_self)
        return queryset

    @cached_property
    def has_children(self):
        return bool(self.get_children())

    def get_absolute_url(self):
        return reverse(
            "category_details",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_edit_url(self):
        return reverse(
            "category_edit",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_delete_url(self):
        return reverse(
            "category_delete",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_reorder_url(self):
        return reverse(
            "category_reorder",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_add_quantity_url(self):
        return reverse(
            "quantity_in_category_create",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_add_category_url(self):
        return reverse(
            "category_create",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )

    def get_quantities_url(self):
        return reverse(
            "quantities_list",
            kwargs={"project_pk": self.project_id, "category_pk": self.pk},
        )


class Quantity(models.Model):
    """A quantity belongs to a category"""

    category = TreeForeignKeyNoRoot(Category, on_delete=models.CASCADE, related_name="quantities")
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    value = models.PositiveIntegerField()

    datetime = models.DateTimeField(null=False, blank=False, default=timezone.now)

    class Meta:
        verbose_name_plural = "quantities"
        ordering = ["-datetime"]
        indexes = [
            models.Index(fields=["category", "datetime"]),
        ]

    def get_edit_url(self):
        return reverse(
            "quantity_edit",
            kwargs={"project_pk": self.category.project_id, "category_pk": self.category_id, "quantity_pk": self.pk},
        )

    def get_delete_url(self):
        return reverse(
            "quantity_delete",
            kwargs={"project_pk": self.category.project_id, "category_pk": self.category_id, "quantity_pk": self.pk},
        )
