from django.contrib import admin

from .models import Project, User, Quantity, Category

# register the project model in admin
admin.site.register(Project)
admin.site.register(User)
