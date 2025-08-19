from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=20, blank=True, null=True)

class EvaluationForm(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    questions = models.JSONField()
    created_by = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE, related_name='created_forms')
    target_employees = models.ManyToManyField('evaluation.CustomUser', related_name='assigned_forms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class EvaluationResponse(models.Model):
    form = models.ForeignKey(EvaluationForm, on_delete=models.CASCADE)
    employee = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE)
    responses = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['form', 'employee']
