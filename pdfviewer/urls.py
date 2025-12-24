from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='pdf_index'),
]
