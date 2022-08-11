from datetime import datetime
from typing import Optional

from django.template.defaulttags import register
from django.utils.safestring import mark_safe
from mptt.utils import get_cached_trees

from core.forms import (
    QuantityInCategoryForm,
    CategoryCreateForm,
    CategoryEditForm,
    CategoryReorderForm,
    CategoryDeleteForm, ProjectCreateForm, ProjectEditForm, ProjectDeleteForm, ProjectReorderForm, QuantityEditForm,
    QuantityDeleteForm,
)
from core.models import Intervals, get_interval_str


@register.filter
def dict_value(dictionary, key):
    return dictionary.get(key)


@register.filter
def concat(value1, value2):
    return f"{value1}{value2}"


@register.simple_tag
def interval_str(date: Optional[datetime.date] = None, interval: Optional[str] = None) -> str:
    if date is None:
        date = datetime.now().date()
    try:
        interval = Intervals(interval) if interval else None
    except ValueError:
        interval = None
    return get_interval_str(date, interval or Intervals.daily)


@register.filter
def summed_quantities(project, date_str=None):
    if project.has_interval:
        date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
    else:
        date = None
    return project.get_summed_quantities(date)


@register.filter
def cache_tree(categories):
    return get_cached_trees(categories)


@register.inclusion_tag("project_form_include.html", takes_context=True)
def project_form(context, project=None, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": ProjectCreateForm()
        if project is None
        else ProjectEditForm(instance=project),
    }


@register.inclusion_tag("project_delete_form_include.html", takes_context=True)
def project_delete_form(context, project, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": ProjectDeleteForm(instance=project),
    }


@register.inclusion_tag("project_reorder_form_include.html", takes_context=True)
def project_reorder_form(context, user, project, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": ProjectReorderForm(user=user, instance=project),
    }


@register.inclusion_tag("category_form_include.html", takes_context=True)
def category_form(context, project, parent_category=None, category=None, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": CategoryCreateForm(project=project, parent_category=parent_category)
        if category is None
        else CategoryEditForm(instance=category),
    }


@register.inclusion_tag("category_reorder_form_include.html", takes_context=True)
def category_reorder_form(context, category, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": CategoryReorderForm(instance=category),
    }


@register.inclusion_tag("category_delete_form_include.html", takes_context=True)
def category_delete_form(context, category, next_category=None):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": CategoryDeleteForm(instance=category),
    }


@register.inclusion_tag("quantity_form_include.html", takes_context=True)
def quantity_in_category_form(context, category=None, next_category=None, initial_value=None):
    min_date, max_date, initial_date = QuantityInCategoryForm.get_date_args(category.project, context.get("date"), context.get("interval") or category.project.interval)
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "category": category,
        "next": f"category:{next_category.id}" if next_category else None,
        "form": QuantityInCategoryForm(
            category=category,
            min_date=min_date,
            max_date=max_date,
            initial={
                "value": initial_value if initial_value and initial_value > 0 else None,
                "datetime": initial_date
            },
        ),
    }


@register.inclusion_tag("quantity_form_include.html", takes_context=True)
def quantity_edit_form(context, quantity, next_category=None):
    category = quantity.category
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "category": category,
        "next": f"category:{next_category.id}" if next_category else None,
        "form": QuantityEditForm(instance=quantity),
    }


@register.inclusion_tag("quantity_delete_form_include.html", takes_context=True)
def quantity_delete_form(context, quantity, next_category=None):
    category = quantity.category
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "form": QuantityDeleteForm(instance=quantity),
    }


@register.filter(name="add_field_attr")
def add_field_attribute(field, css):
    # https://stackoverflow.com/questions/61822256/adding-a-class-is-invalid-to-input-form-in-djang
    attrs = field.subwidgets[0].data["attrs"]  # Accessing the already declared attributes
    definition = css.split(",")

    for d in definition:
        if ":" not in d:
            attrs["class"] += f" {d}"  # Extending the class string
        else:
            key, val = d.split(":")
            attrs[key] += f"{val}"  # Extending the `key` string

    return field.as_widget(attrs=attrs)


@register.filter
def interval(interval):
    try:
        return Intervals(interval)
    except ValueError:
        return None


@register.simple_tag
def icon(name, style="light", size=None, classes=None):
    if name.startswith("fa-"):
        name = name[3:]
    if style.startswith("fa-"):
        style = style[3:]
    if size and size.startswith("fa-"):
        size = size[3:]
    size_part = "" if size is None else f" fa-{size}"
    return mark_safe(f'<i class="fa-{style} fa-{name}{size_part} {classes or ""}"></i>')


@register.simple_tag
def icon_sm(name, style="light", classes=None):
    return icon(name, style, "sm", classes)


@register.simple_tag
def icon_xs(name, style="light", classes=None):
    return icon(name, style, "xs", classes)


@register.filter
def sub(value, arg):
    return value - arg
