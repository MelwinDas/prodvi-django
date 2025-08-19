from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('evaluate/', views.evaluate_response, name='evaluate'),
    path('reports/<int:employee_id>/', views.generate_report, name='generate_report'),
]
