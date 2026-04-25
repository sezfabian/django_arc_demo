from django.urls import path
from .views import free_view, cheap_view, expensive_view

urlpatterns = [
    path('free/', free_view, name='free'),
    path('cheap/', cheap_view, name='cheap'),
    path('expensive/', expensive_view, name='expensive'),
]