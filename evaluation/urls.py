from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin paths
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('create-form/', views.create_form, name='create_form'),

    # Employee paths
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('fill-form/<int:form_id>/', views.fill_form, name='fill_form'),

    # API
    path('evaluate/', views.evaluate_response, name='evaluate'),
]
