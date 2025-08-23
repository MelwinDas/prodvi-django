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
    
    path('view-reviews/<int:form_id>/', views.view_reviews, name='view_reviews'),
    path('admin-summaries/<int:form_id>/', views.admin_summaries_list, name='admin_summaries_list'),
    path('admin-summary/<int:form_id>/<int:employee_id>/', views.admin_employee_summary, name='admin_employee_summary'),
    path('refresh-summary/<int:form_id>/<int:employee_id>/', views.refresh_employee_summary, name='refresh_employee_summary'),
    path('evaluation/<int:form_id>/results/', views.evaluation_results, name="evaluation_results"),

    
    # Employee paths
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('review-colleague/<int:form_id>/<int:colleague_id>/', views.review_colleague, name='review_colleague'),
    path('my-summary/<int:form_id>/', views.my_summary, name='my_summary'),
    path('refresh-my-summary/<int:form_id>/', views.refresh_my_summary, name='refresh_my_summary'),  # Add this line
    
    path('output/<int:form_id>/<int:employee_id>/', views.performance_output, name='performance_output'),
    path('my-output/<int:form_id>/', views.my_output, name='my_output'),

    # API
    path('evaluate/', views.evaluate_response, name='evaluate'),
]
