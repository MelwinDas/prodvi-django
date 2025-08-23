from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EvaluationForm, PeerReview, EmployeeSummary, EvaluationResponse


class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin user list page
    list_display = ('username', 'email', 'role', 'employee_id')
    list_filter = ('role',)
    search_fields = ('username', 'email', 'employee_id')

    # Fields shown on the user detail page (when editing a user)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email',)}),
        ('Work Info', {'fields': ('role', 'employee_id', 'department')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields shown when adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'employee_id', 'department'),
        }),
    )


# Register all models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EvaluationForm)
admin.site.register(PeerReview)
admin.site.register(EmployeeSummary)
admin.site.register(EvaluationResponse)
