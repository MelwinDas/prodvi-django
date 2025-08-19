from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('evaluate/', views.evaluate_response, name='evaluate_response'),
    path('report/<int:employee_id>/', views.generate_report, name='generate_report'),
]
