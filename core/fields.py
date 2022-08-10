from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from mptt.fields import TreeForeignKey
from mptt.forms import TreeNodeChoiceField


class TreeNodeChoiceFieldNoRoot(TreeNodeChoiceField):
    def _get_relative_level(self, obj):
        return super()._get_relative_level(obj) - 1

    def _get_level_indicator(self, obj):
        level = self._get_relative_level(obj)
        return mark_safe(
            "&nbsp;&nbsp;&nbsp;&nbsp;" * level + conditional_escape(self.level_indicator) * (1 if level > 0 else 0)
        )


class TreeForeignKeyNoRoot(TreeForeignKey):
    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", TreeNodeChoiceFieldNoRoot)
        return super().formfield(**kwargs)
