from django.db import models

from django.contrib.auth.models import User

class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Evaluation(models.Model):
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Response(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=100)  # Leadership, Communication, etc.
    ml_prediction = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
