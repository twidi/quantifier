from datetime import datetime
from typing import Tuple

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django.core.exceptions import ValidationError
from django.forms import ModelForm, Select, BooleanField, TextInput
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
            "quantity_name",
            "interval",
            "interval_quantity",
            "goal_mode",
            "name",
            "quick_add_quantities",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quick_add_quantities"].widget = TextInput()

        self.with_helper = True
        self.helper = FormHelper()
        self.helper.form_tag = False

        layout_fields = []
        for field in self.fields:
            if field == "goal_mode":
                field = Field(field, wrapper_class="form-switch")
            layout_fields.append(field)
        self.helper.layout = Layout(*layout_fields)


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
        fields = ["name", "expected_quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.with_helper = True
        self.helper = FormHelper()
        self.helper.form_tag = False


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


class CategoryEditForm(CategoryBaseForm):
    class Meta(CategoryBaseForm.Meta):
        fields = CategoryBaseForm.Meta.fields.copy()
        name_position = fields.index("name")
        fields.insert(name_position + 1, "parent")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"category-edit-{self.instance.pk}"

        self.fields["parent"].queryset = self.instance.project.visible_categories
        self.fields["parent"].widget.attrs.update({"class": "autocomplete"})
        self.fields["parent"].empty_label = mark_safe("&nbsp;")

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
        fields = ["value", "date", "time", "category", "notes"]

    @staticmethod
    def get_initial_date(date, interval) -> datetime.date:
        initial_date = datetime.now().date()
        if initial_date != date and interval in (None, Intervals.none):
            initial_date = date
        min_date, max_date = get_dates_interval(date, interval)
        if not (min_date <= initial_date <= max_date):
            initial_date = min_date
        return initial_date

    def get_categories(self):
        return self.project.visible_categories

    def __init__(self, project, *args, **kwargs):
        self.project = project

        if project.unique_quick_add_quantity and (initial := (kwargs.get("initial") or {})).get("value") is None:
            kwargs["initial"] = initial | {"value": project.unique_quick_add_quantity}

        super().__init__(*args, **kwargs)

        self.with_helper = True
        self.helper = FormHelper()
        self.helper.form_tag = False

        value_widget_attrs = {}
        if self.project.quick_add_quantities:
            value_widget_attrs["list"] = f"project-{self.project.pk}-quick_add_quantities"

        self.fields["value"].widget.attrs.update(value_widget_attrs)
        self.fields["value"].help_text %= {"quantity_name": self.project.quantity_name}

        self.fields["notes"].widget.attrs.update({"rows": 3})

        self.fields["date"].widget.input_type = "date"
        self.fields["time"].widget.input_type = "time"

        self.fields["category"].queryset = self.get_categories()
        self.fields["category"].empty_label = None
        self.fields["category"].widget.attrs.update({"class": "autocomplete"})


class QuantityInProjectForm(QuantityBaseForm):
    def __init__(self, project, *args, **kwargs):
        super().__init__(project, *args, **kwargs)
        self.prefix = f"project-{project.pk}-qtt-" + (f"{self.instance.pk}" if self.instance.pk else "new")


class QuantityInCategoryForm(QuantityBaseForm):
    def get_categories(self):
        return self.category.get_descendants(include_self=True)

    def __init__(self, category, *args, **kwargs):
        self.category = category
        super().__init__(category.project, *args, **kwargs)
        self.prefix = f"category-{category.pk}-qtt-" + (f"{self.instance.pk}" if self.instance.pk else "new")
        self.instance.category = category


class QuantityEditForm(QuantityInCategoryForm):
    def get_categories(self):
        return self.project.visible_categories

    def __init__(self, *args, **kwargs):
        super().__init__(category=kwargs["instance"].category, *args, **kwargs)


class QuantityDeleteForm(ModelForm):
    confirm = BooleanField(required=True, label="Check this to confirm deletion")

    class Meta:
        model = Quantity
        fields = ["confirm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = f"quantity-delete-{self.instance.pk}"
        self.fields["confirm"].widget.attrs.update({"class": "form-check-input mt-0"})
