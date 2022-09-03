from datetime import datetime
from typing import Optional, NamedTuple, Literal, Union

from django.template.defaulttags import register
from django.utils.safestring import mark_safe
from mptt.utils import get_cached_trees

from core.forms import (
    QuantityInCategoryForm,
    CategoryCreateForm,
    CategoryEditForm,
    CategoryReorderForm,
    CategoryDeleteForm,
    ProjectCreateForm,
    ProjectEditForm,
    ProjectDeleteForm,
    ProjectReorderForm,
    QuantityEditForm,
    QuantityDeleteForm, QuantityInProjectForm,
)
from core.models import Intervals, get_interval_str, Project


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
        "form": ProjectCreateForm() if project is None else ProjectEditForm(instance=project),
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
def quantity_in_category_form(context, category, next_category=None, initial_value=None):
    min_date, max_date, initial_date = QuantityInCategoryForm.get_date_args(
        category.project, context.get("date"), context.get("interval") or category.project.interval
    )
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "project": category.project,
        "category": category,
        "next": f"category:{next_category.id}" if next_category else None,
        "form": QuantityInCategoryForm(
            category=category,
            min_date=min_date,
            max_date=max_date,
            initial={
                "value": initial_value if initial_value and initial_value > 0 else None,
                "datetime": initial_date,
            },
        ),
    }


@register.inclusion_tag("quantity_form_include.html", takes_context=True)
def quantity_in_project_form(context, project, initial_value=None):
    min_date, max_date, initial_date = QuantityInProjectForm.get_date_args(
        project, context.get("date"), context.get("interval") or project.interval
    )
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "project": project,
        "next": "projects",
        "form": QuantityInProjectForm(
            project=project,
            min_date=min_date,
            max_date=max_date,
            initial={
                "value": initial_value if initial_value and initial_value > 0 else None,
                "datetime": initial_date,
            },
        ),
    }


@register.inclusion_tag("quantity_form_include.html", takes_context=True)
def quantity_edit_form(context, quantity, next_category=None, next_with_children=True):
    category = quantity.category
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "category": category,
        "next": f"category:{next_category.id}" if next_category else None,
        "next_with_children": next_with_children,
        "form": QuantityEditForm(instance=quantity),
    }


@register.inclusion_tag("quantity_delete_form_include.html", takes_context=True)
def quantity_delete_form(context, quantity, next_category=None, next_with_children=True):
    return {
        "date": context.get("date"),
        "date_str": context.get("date_str"),
        "interval": context.get("interval"),
        "next": f"category:{next_category.id}" if next_category else None,
        "next_with_children": next_with_children,
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


@register.filter
def mul(value, arg):
    return value * arg


class TextPart(NamedTuple):
    text: str
    kind: Optional[Literal["used", "overflow", "left", "side-name"]] = None

    @classmethod
    def new(cls, value: Union[float, str], kind: Optional[Literal["used", "overflow", "left"]] = None):
        return cls(f"{value}", kind)


class BarPart(NamedTuple):
    percent: float
    kind: Optional[Literal["used", "overflow", "left"]] = None

    @classmethod
    def new(cls, ratio: float, kind: Optional[Literal["used", "overflow", "left"]] = None):
        return cls(ratio * 100, kind)


def extend_texts_or_bars(list_, func, args):
    list_.extend(
        func(*((subargs,) if isinstance(subargs, (str, float, int)) else subargs))
        for subargs in args
        if subargs not in (None, "")
    )


@register.inclusion_tag("gauge.html", takes_context=True)
def gauge(context, obj, summed_quantities):
    project = context["project"]
    if project.goal_mode and not summed_quantities.get("goal_planned"):
        return {}
    if not project.goal_mode and not summed_quantities.get("expected"):
        return {}

    is_for_project = isinstance(obj, Project)
    interval_quantity = summed_quantities.get("interval_quantity") or project.interval_quantity
    used_total = summed_quantities.get("used")
    planned = summed_quantities.get("expected", 0)
    used_planned_overflow = summed_quantities.get("unexpected", 0)
    left_in_planned = summed_quantities.get("expected_not_used", 0)
    used_in_planned = planned - left_in_planned
    used_in_unplanned = summed_quantities.get("used_not_expected", 0)
    used_unplanned = used_in_unplanned + used_planned_overflow

    if is_for_project and (max_unplanned := summed_quantities.get("total_unexpected")):
        left_in_unplanned = max_unplanned - used_unplanned
    else:
        max_unplanned = left_in_unplanned = None
        # if _used_in_planned < planned:
        #     used_unplanned = _used_in_unplanned
        #
    raw_data = {
        "used_total": used_total,
        "planned": planned,
        "used_planned_overflow": used_planned_overflow,
        "left_in_planned": left_in_planned,
        "used_in_planned": used_in_planned,
        "used_in_unplanned": used_in_unplanned,
        "used_unplanned": used_unplanned,
        "max_unplanned": max_unplanned,
        "left_in_unplanned": left_in_unplanned,
    }
    left_top_texts = []
    left_bottom_texts = []
    left_bars = []
    right_top_texts = []
    right_bottom_texts = []
    right_bars = []

    RTtexts = lambda *args: extend_texts_or_bars(right_top_texts, TextPart.new, args)
    RBtexts = lambda *args: extend_texts_or_bars(right_bottom_texts, TextPart.new, args)
    Rbars = lambda *args: extend_texts_or_bars(right_bars, BarPart.new, args)
    LTtexts = lambda *args: extend_texts_or_bars(left_top_texts, TextPart.new, args)
    LBtexts = lambda *args: extend_texts_or_bars(left_bottom_texts, TextPart.new, args)
    Lbars = lambda *args: extend_texts_or_bars(left_bars, BarPart.new, args)

    left_percent = 0

    # fmt: off
    if interval_quantity and planned and (planned_over_limit := max(0, planned - interval_quantity)):

        if project.goal_mode:
            LBtexts(
                ("Planned goal exceeds the", "warning"),
                (interval_quantity, "used"),
                ("total one by", "warning"),
                (planned_over_limit, "overflow"),
            )
        else:
            LBtexts(
                ("Planned exceeds the", "warning"),
                (interval_quantity, "used"),
                 ("limit by", "warning"),
                (planned_over_limit, "overflow"),
            )
        Lbars(
            (interval_quantity / planned, "used"),
            (planned_over_limit / planned, "overflow"),
        )
        LTtexts(
            ("Gauge cannot be displayed", "warning"),
        )

    elif project.goal_mode:
        final_planned = summed_quantities['goal_planned']
        max_value = summed_quantities['goal_max_value']
        diff = summed_quantities['gaol_diff']
        goal_reached = summed_quantities['goal_reached']

        LTtexts(
            (used_total, None if goal_reached or not used_total else "used"),
            f"/",
            (final_planned, "used" if goal_reached else None),
            "expected",
        )

        Lbars(
            (min(used_total, final_planned) / max_value, "used"),
            (diff / max_value, "overflow" if goal_reached else "warning"),
        )

        if diff:
            RBtexts(
                "Excess:" if goal_reached else "Left:",
                (diff, "overflow" if goal_reached else "warning"),
            )

    else:

        LTtexts(
            (used_in_planned, "used" if used_in_planned > 0 else None),
            f"/ {planned}",
            ("Planned", "side-name")
        )
        LBtexts(
            f"Left: {left_in_planned}"
        )
        Lbars(
            (used_in_planned / planned, "used"),
        )

        min_size = 10
        size_reference = used_total
        if is_for_project and max_unplanned:
            size_reference = max(used_total, interval_quantity)
        if size_reference == 0:
            size_reference = 100
        left_percent = min(100-min_size, max(min_size, planned / size_reference * 100))

        right_max_value = max(max_unplanned, used_unplanned) if max_unplanned and used_in_unplanned else (max_unplanned or used_unplanned or 0)

        if is_for_project and max_unplanned:
            is_excess = used_unplanned > max_unplanned
            if used_in_unplanned and used_planned_overflow:
                RTtexts(
                    used_unplanned,
                    f"/ {max_unplanned}" if max_unplanned else None,
                    ("Unplanned", "side-name"),
                )
                RBtexts(
                    (used_planned_overflow, "overflow"),
                    "+",
                )
                if is_excess:
                    if used_in_unplanned > max_unplanned:
                        if max_unplanned:
                            RBtexts(
                                (max_unplanned, "used"),
                                "+",
                            )
                        RBtexts(
                            (used_in_unplanned - max_unplanned, "overflow"),
                        )
                    else:
                        RBtexts(
                            (used_in_unplanned, "used"),
                        )
                    RBtexts(
                        "| Excess:",
                        (-left_in_unplanned, "overflow"),
                    )
                else:
                    RBtexts(
                        (used_in_unplanned, "used"),
                        "| Left:",
                        (left_in_unplanned, "left"),
                    )
                if is_excess and right_max_value:
                    Rbars(
                        (used_planned_overflow / right_max_value, "overflow"),
                        (max_unplanned / right_max_value, "used"),
                        ((used_in_unplanned - max_unplanned) / right_max_value, "overflow") if used_in_unplanned > max_unplanned else None,
                    )
                elif right_max_value:
                    Rbars(
                        (used_planned_overflow / right_max_value, "overflow"),
                        (used_in_unplanned / right_max_value, "used"),
                        (left_in_unplanned / right_max_value, "left"),
                    )

            elif used_planned_overflow:
                RTtexts(
                    (used_planned_overflow, "overflow"),
                    ("Unplanned", "side-name"),
                )
                if is_excess:
                    RBtexts(
                        "Excess:",
                        (-left_in_unplanned, "overflow"),
                    )
                else:
                    RBtexts(
                        "Left:",
                        (left_in_unplanned, "left"),
                    )
                if right_max_value:
                    Rbars(
                        (used_planned_overflow / right_max_value, "overflow"),
                        (left_in_unplanned / right_max_value, "left"),
                    )
            else:
                RTtexts(
                    (used_unplanned, None if used_unplanned > max_unplanned or used_unplanned <= 0 else "used"),
                    f"/ {max_unplanned}" if max_unplanned else None,
                    ("Unplanned", "side-name"),
                )
                if is_excess:
                    RBtexts(
                        "Excess:",
                        (-left_in_unplanned, "overflow"),
                    )
                else:
                    RBtexts(
                        "Left:",
                        (left_in_unplanned, "left"),
                    )
                if right_max_value:
                    Rbars(
                        (used_unplanned / right_max_value, "used"),
                        (left_in_unplanned / right_max_value, "left"),
                    )
        else:
            if used_in_unplanned and used_planned_overflow:
                RTtexts(
                    used_unplanned,
                    ("Unplanned", "side-name"),
                )
                RBtexts(
                    (used_planned_overflow, "overflow"),
                    "+",
                    (used_in_unplanned, "used"),
                )
                if right_max_value:
                    Rbars(
                        (used_planned_overflow / right_max_value, "overflow"),
                        (used_in_unplanned / right_max_value, "used"),
                    )
            elif used_planned_overflow:
                RTtexts(
                    (used_planned_overflow, "overflow"),
                    ("Unplanned", "side-name"),
                )
                Rbars(
                    (1, "overflow"),
                )
            else:
                RTtexts(
                    used_unplanned,
                )
                RTtexts(
                    ("Unplanned", "side-name"),
                )
                if used_in_unplanned:
                    Rbars(
                        (1, "used"),
                    )

    # fmt: on

    bars_sides = []
    if left_bars:
        bars_sides.append({"placement": "left", "parts": left_bars, "percent": left_percent if right_bars else 100})
    if right_bars:
        bars_sides.append(
            {"placement": "right", "parts": right_bars, "percent": (100 - left_percent) if left_bars else 100}
        )

    return {
        "gauge": {
            # 'raw_data': raw_data,
            "goal_mode": project.goal_mode,
            "text_lines": [
                {"placement": "top", "sides": [left_top_texts, right_top_texts]},
                {"placement": "bottom", "sides": [left_bottom_texts, right_bottom_texts]},
            ],
            "bars_sides": bars_sides,
        }
    }
