from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from .models import CustomUser, EvaluationForm, EvaluationResponse
import json
import traceback
import os
from django.conf import settings

def landing_page(request):
    return render(request, 'evaluation/landing_page.html')

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role', 'employee')
        department = request.POST.get('department', '')
        employee_id = request.POST.get('employee_id', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'evaluation/signup.html')
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'evaluation/signup.html')
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'evaluation/signup.html')

        try:
            CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                department=department,
                employee_id=employee_id
            )
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
        except IntegrityError:
            messages.error(request, 'Employee ID already exists. Please use a different one.')
            return render(request, 'evaluation/signup.html')
    return render(request, 'evaluation/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('employee_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'evaluation/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('landing_page')

# Admin views
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@user_passes_test(is_admin)
def admin_dashboard(request):
    forms = EvaluationForm.objects.filter(created_by=request.user).order_by('-created_at')
    employees = CustomUser.objects.filter(role='employee')
    return render(request, 'evaluation/admin_dashboard.html', {'forms': forms, 'employees': employees})

@user_passes_test(is_admin)
def create_form(request):
    employees = CustomUser.objects.filter(role='employee')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        questions_raw = request.POST.get('questions')
        target_employee_ids = request.POST.getlist('target_employees')
        
        questions = [{'text': q.strip()} for q in questions_raw.strip().split('\n') if q.strip()]
        form = EvaluationForm.objects.create(
            title=title, description=description, questions=questions, created_by=request.user
        )
        if target_employee_ids:
            form.target_employees.set(employees.filter(id__in=target_employee_ids))
        messages.success(request, 'Evaluation Form created!')
        return redirect('admin_dashboard')
    return render(request, 'evaluation/create_form.html', {'employees': employees})

# Employee views
def is_employee(user):
    return user.is_authenticated and user.role == 'employee'

@user_passes_test(is_employee)
def employee_dashboard(request):
    assigned_forms = EvaluationForm.objects.filter(
        target_employees=request.user, is_active=True
    ).exclude(
        evaluationresponse__employee=request.user
    )
    completed_forms = EvaluationResponse.objects.filter(employee=request.user)
    return render(request, 'evaluation/employee_dashboard.html', {
        'assigned_forms': assigned_forms,
        'completed_forms': completed_forms
    })

@user_passes_test(is_employee)
def fill_form(request, form_id):
    form = get_object_or_404(EvaluationForm, id=form_id, is_active=True)
    if request.user not in form.target_employees.all():
        messages.error(request, 'You are not assigned to this form')
        return redirect('employee_dashboard')
    if EvaluationResponse.objects.filter(form=form, employee=request.user).exists():
        messages.info(request, 'You have already submitted this form')
        return redirect('employee_dashboard')
    if request.method == 'POST':
        responses = {}
        for i, q in enumerate(form.questions):
            answer = request.POST.get(f"question_{i}", '')
            responses[q['text']] = answer
        EvaluationResponse.objects.create(form=form, employee=request.user, responses=responses)
        messages.success(request, 'Form submitted successfully!')
        return redirect('employee_dashboard')
    return render(request, 'evaluation/fill_form.html', {'form': form})

@login_required
@csrf_exempt
def evaluate_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            answer = data.get('answer', '')

            # Import ML models
            from .ml_models.qpsvc import QuestionClassifier
            from .ml_models.genprocess import Brain

            classifier = QuestionClassifier()
            brain = Brain()

            category, confidence = classifier.classify(question)

            if category != "Out of Scope":
                prediction = brain.brain(category, answer)
            else:
                prediction = brain.brain("Out of Scope", answer)

            return JsonResponse({
                'category': category,
                'confidence': float(confidence),
                'prediction': str(prediction),
                'status': 'success'
            })

        except Exception as e:
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'type': type(e).__name__
            }
            return JsonResponse(error_details, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
