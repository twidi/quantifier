from datetime import datetime
from typing import NamedTuple

from crispy_forms.helper import FormHelper
from django.core.exceptions import ValidationError
from django.forms import ModelForm, ChoiceField, Select, BooleanField, TextInput
from django.utils.safestring import mark_safe
from django_registration.forms import RegistrationFormUniqueEmail
from mptt.forms import MPTTAdminForm

from .fields import TreeNodeChoiceFieldNoRoot
from .models import User, Quantity, Category, Project, get_dates_interval, Intervals


class CoreRegistrationForm(RegistrationFormUniqueEmail):
    class Meta(RegistrationFormUniqueEmail.Meta):
        model = User


class ProjectBaseForm(ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "interval",
            "interval_quantity",
            "quantity_name",
            "quick_add_quantities",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quick_add_quantities"].widget = TextInput()

        self.with_helper = True
        self.helper = FormHelper()
        self.helper.label_class = "small"
        self.helper.wrapper_class = "mb-0"
        self.helper.form_tag = False

        for field in self.Meta.fields:
            if field == "interval":
                self.fields[field].widget.attrs.update({"class": "form-select form-select-sm"})
            elif field == "description":
                self.fields["description"].widget.attrs.update(
                    {"class": "form-control form-control-sm auto-reduce", "rows": 5}
                )
            else:
                self.fields[field].widget.attrs.update({"class": "form-control form-control-sm"})


class ProjectCreateForm(ProjectBaseForm):
    prefix = "project-create"


class ProjectEditForm(ProjectBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"project-edit-{self.instance.pk}"


class ProjectDeleteForm(ModelForm):
    confirm = BooleanField(required=True, label="Check this to confirm deletion")

    class Meta:
        model = Project
        fields = ["confirm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"project-delete-{self.instance.pk}"
        self.fields["confirm"].widget.attrs.update({"class": "form-check-input mt-0"})


class ProjectReorderForm(ModelForm):
    class Meta:
        model = Project
        fields = ["sort_order"]

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.prefix = f"project-reorder-{self.instance.pk}"

        field = self.fields["sort_order"]

        projects = list(self.user.cached_projects)

        choices = []
        before = True
        self.allowed_sort_orders = set()
        for index, project in enumerate(projects):
            if not index:
                label = "first_position"
            elif before:
                label = f"after «{projects[index-1].name}»"
            else:
                label = f"after «{project.name}»"

            if project == self.instance:
                before = False
                label += " (current position)"

            choices.append((project.sort_order, label))
            self.allowed_sort_orders.add(project.sort_order)

        field.widget = Select(choices=choices)
        field.label = "Position"
        field.widget.attrs.update({"class": "form-select form-select-sm autocomplete"})

    def clean_sort_order(self):
        sort_order = self.cleaned_data["sort_order"]
        if sort_order not in self.allowed_sort_orders:
            raise ValidationError("Invalid sort order")
        return sort_order


class CategoryBaseForm(MPTTAdminForm):
    class Meta:
        model = Category
        fields = ["name", "description", "expected_quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].widget.attrs.update({"class": "form-control form-control-sm"})
        self.fields["description"].widget.attrs.update(
            {"class": "form-control form-control-sm auto-reduce", "rows": 5}
        )
        self.fields["expected_quantity"].widget.attrs.update({"class": "form-control form-control-sm"})

        self.fields["name"].widget.attrs["placeholder"] = "Name"
        self.fields["description"].widget.attrs["placeholder"] = "Description"
        self.fields["expected_quantity"].widget.attrs["placeholder"] = "Planned quantity"


class CategoryCreateForm(CategoryBaseForm):
    def __init__(self, project, parent_category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f'category-create-{project.pk}-{parent_category.pk if parent_category else "root"}'

        if parent_category and parent_category.project != project:
            parent_category = None
        if parent_category is None:
            parent_category = project.root_category

        self.instance.project_id = project.pk
        self.instance.parent = parent_category
        self.fields["expected_quantity"].widget.attrs[
            "placeholder"
        ] = f"Planned {parent_category.project.quantity_name}"
        self.fields["expected_quantity"].help_text = "If set, should include planned amounts of sub-categories."


class CategoryEditForm(CategoryBaseForm):
    class Meta(CategoryBaseForm.Meta):
        fields = CategoryBaseForm.Meta.fields.copy()
        description_position = fields.index("description")
        fields.insert(description_position + 1, "parent")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"category-edit-{self.instance.pk}"

        self.fields["parent"].queryset = self.instance.project.visible_categories
        self.fields["parent"].label = "Parent category:"
        self.fields["parent"].widget.attrs.update({"class": "form-select form-select-sm autocomplete"})
        self.fields["parent"].empty_label = mark_safe("&nbsp;")

        self.fields["expected_quantity"].widget.attrs[
            "placeholder"
        ] = f"Planned {self.instance.project.quantity_name}"
        self.fields["expected_quantity"].help_text = "If set, should include planned amounts of sub-categories."

    def clean_parent(self):
        return self.cleaned_data["parent"] or self.instance.project.root_category


class CategoryReorderForm(ModelForm):
    class Meta:
        model = Category
        fields = ["sort_order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"category-reorder-{self.instance.pk}"

        field = self.fields["sort_order"]

        categories = list(self.instance.get_siblings(include_self=True))

        choices = []
        before = True
        self.allowed_sort_orders = set()
        for index, category in enumerate(categories):
            if not index:
                label = "first_position"
            elif before:
                label = f"after «{categories[index-1].name}»"
            else:
                label = f"after «{category.name}»"

            if category == self.instance:
                before = False
                label += " (current position)"

            choices.append((category.sort_order, label))
            self.allowed_sort_orders.add(category.sort_order)

        field.widget = Select(choices=choices)
        field.label = "Position"
        field.widget.attrs.update({"class": "form-select form-select-sm autocomplete"})

    def clean_sort_order(self):
        sort_order = self.cleaned_data["sort_order"]
        if sort_order not in self.allowed_sort_orders:
            raise ValidationError("Invalid sort order")
        return sort_order


class CategoryDeleteForm(ModelForm):
    confirm = BooleanField(required=True, label="Check this to confirm deletion")

    class Meta:
        model = Category
        fields = ["confirm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"category-delete-{self.instance.pk}"
        self.fields["confirm"].widget.attrs.update({"class": "form-check-input mt-0"})


class QuantityBaseForm(ModelForm):
    error_css_class = "is-invalid"

    class Meta:
        model = Quantity
        fields = ["value", "datetime", "name", "description"]

    @classmethod
    def get_date_args(cls, project, date, interval):
        initial_datetime = datetime.now()
        min_date, max_date = get_dates_interval(date, interval)
        if initial_datetime.date() != date and interval in (None, Intervals.none):
            initial_datetime = datetime.combine(date, datetime.min.time())
        if not (min_date <= initial_datetime <= max_date):
            initial_datetime = min_date
        if not project.has_interval:
            min_date = max_date = None
        return min_date, max_date, initial_datetime

    def __init__(self, min_date, max_date, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_date, self.max_date = min_date, max_date

        value_widget_attrs = {
            "class": "form-control",
            "title": f"Enter a quantity in {self.project.quantity_name}",
            "placeholder": f"Quantity in {self.project.quantity_name}",
        }
        if self.project.quick_add_quantities:
            value_widget_attrs["list"] = f"project-{self.project.pk}-quick_add_quantities"
            if len(quick_add_quantities := self.project.quick_add_quantities_as_list) == 1:
                self.fields["value"].initial = quick_add_quantities[0]
                value_widget_attrs["title"] += " (or pick one from the list)"
        self.fields["value"].widget.attrs.update(value_widget_attrs)

        self.fields["name"].widget.attrs.update({"class": "form-control form-control-sm"})
        self.fields["description"].widget.attrs.update(
            {"class": "form-control form-control-sm auto-reduce", "rows": 5}
        )

        date_attrs = {
            "data-input": "true",
            "class": "form-control form-control-sm",
        }
        if self.project.has_interval and min_date and max_date:
            date_attrs |= {
                "data-min-date": min_date.strftime("%Y-%m-%d %H:%M"),
                "data-max-date": max_date.strftime("%Y-%m-%d %H:%M"),
            }
        self.fields["datetime"].widget.attrs.update(date_attrs)

        self.fields["name"].widget.attrs["placeholder"] = "Name"
        self.fields["description"].widget.attrs["placeholder"] = "Description"
        self.fields["datetime"].widget.attrs["placeholder"] = "Date & time"

    def clean_datetime(self):
        date = self.cleaned_data["datetime"]
        if (
            self.project.has_interval
            and date
            and self.min_date
            and self.max_date
            and not (self.min_date.replace(tzinfo=date.tzinfo) <= date <= self.max_date.replace(tzinfo=date.tzinfo))
        ):
            raise ValidationError(
                f"Date must be between {self.min_date.date()} and {self.max_date()} (both inclusive)"
            )
        return date


class QuantityInProjectForm(QuantityBaseForm):
    class Meta(QuantityBaseForm.Meta):
        fields = ["category"] + QuantityBaseForm.Meta.fields

    def __init__(self, project, min_date, max_date, *args, **kwargs):
        self.project = project
        super().__init__(min_date, max_date, *args, **kwargs)
        self.prefix = f"project-{project.pk}-qtt-" + (f"{self.instance.pk}" if self.instance.pk else "new")

        self.fields["value"].widget.attrs["placeholder"] = ""

        class CategoryChoiceField(TreeNodeChoiceFieldNoRoot):
            def label_from_instance(self, obj):
                # project.summed_quantities must be defined by the caller by calling get_summed_quantities()
                summed = project.summed_quantities[obj]
                result = super().label_from_instance(obj)
                result = f'{result} &nbsp;&nbsp;-&nbsp;&nbsp; {summed["used"]}'
                if summed.get("expected"):
                    result += f'/ {summed["expected"]}'
                    if summed["unexpected"]:
                        result += f' (+ {summed["unexpected"]})'
                    if summed["expected_not_used"]:
                        result += f' (- {summed["expected_not_used"]})'

                return mark_safe(result)

        self.fields["category"].queryset = project.visible_categories
        categories = list(project.visible_categories)
        if len(categories) > 1:
            self.fields["category"].__class__ = CategoryChoiceField
        else:
            self.fields["category"].initial = categories[0] if categories else None
        self.fields["category"].empty_label = mark_safe("&nbsp;")
        self.fields["category"].widget.attrs.update(
            {
                "class": "form-select form-select-sm autocomplete",
                "title": "Select a category",
            }
        )


class QuantityInCategoryForm(QuantityBaseForm):
    class Meta(QuantityBaseForm.Meta):
        fields = QuantityBaseForm.Meta.fields.copy()
        value_position = fields.index("datetime")
        fields.insert(value_position + 1, "category")

    def get_categories(self):
        return self.instance.category.get_descendants(include_self=True)

    def __init__(self, category, min_date, max_date, *args, **kwargs):
        self.project = category.project
        super().__init__(min_date, max_date, *args, **kwargs)
        self.prefix = f"category-{category.pk}-qtt-" + (f"{self.instance.pk}" if self.instance.pk else "new")
        self.instance.category = category

        self.fields["category"].queryset = self.get_categories()
        categories = list(self.fields["category"].queryset)
        if len(categories) > 1:
            self.fields["category"].initial = categories[0]
            self.fields["category"].empty_label = None
            self.fields["category"].label = "Category:"
            self.fields["category"].widget.attrs.update({"class": "form-select form-select-sm autocomplete"})
        else:
            del self.fields["category"]


class QuantityEditForm(QuantityInCategoryForm):
    def get_categories(self):
        return self.project.visible_categories

    def __init__(self, *args, **kwargs):
        super().__init__(category=kwargs["instance"].category, min_date=None, max_date=None, *args, **kwargs)


class QuantityDeleteForm(ModelForm):
    confirm = BooleanField(required=True, label="Check this to confirm deletion")

    class Meta:
        model = Quantity
        fields = ["confirm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"quantity-delete-{self.instance.pk}"
        self.fields["confirm"].widget.attrs.update({"class": "form-check-input mt-0"})
