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
    
    # Employee paths
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('review-colleague/<int:form_id>/<int:colleague_id>/', views.review_colleague, name='review_colleague'),
    
    # API
    path('evaluate/', views.evaluate_response, name='evaluate'),
]
