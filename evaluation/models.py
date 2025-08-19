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
    questions = models.JSONField()  # List of questions
    created_by = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE, related_name='created_forms')
    assigned_employees = models.ManyToManyField('evaluation.CustomUser', related_name='assigned_forms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class PeerReview(models.Model):
    form = models.ForeignKey(EvaluationForm, on_delete=models.CASCADE)
    reviewer = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE, related_name='reviews_received')
    responses = models.JSONField()  # Question -> Answer mapping
    ml_analysis = models.JSONField(blank=True, null=True)  # Store ML results
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['form', 'reviewer', 'reviewee']

    def __str__(self):
        return f"{self.reviewer.username} reviews {self.reviewee.username} - {self.form.title}"

# Keep for backward compatibility if needed
class EvaluationResponse(models.Model):
    form = models.ForeignKey(EvaluationForm, on_delete=models.CASCADE)
    employee = models.ForeignKey('evaluation.CustomUser', on_delete=models.CASCADE)
    responses = models.JSONField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['form', 'employee']
