from django.urls import path

from components.greeting2.importer import import_components

CompCls = import_components()

urlpatterns = [
    path("predefined-url/", CompCls.as_view()),
]
