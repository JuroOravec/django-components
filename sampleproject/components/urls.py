from django.urls import path

from components.calendar.calendar import Calendar, CalendarRelative
from components.greeting import Greeting
from components.alpinui import AlpinuiDemo
from vue.with_python import WithPython
from components.nested.calendar.calendar import CalendarNested

urlpatterns = [
    path("greeting/", Greeting.as_view(), name="greeting"),
    path("alpinui/", AlpinuiDemo.as_view(), name="alpinui"),
    path("vue/python/", WithPython.as_view(), name="vue-python"),
    path("calendar/", Calendar.as_view(), name="calendar"),
    path("calendar-relative/", CalendarRelative.as_view(), name="calendar-relative"),
    path("calendar-nested/", CalendarNested.as_view(), name="calendar-nested"),
]
