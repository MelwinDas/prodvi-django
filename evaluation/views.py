from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from .models import CustomUser, EvaluationForm, EvaluationResponse, PeerReview
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
    
    # Calculate statistics
    total_reviews = PeerReview.objects.filter(form__created_by=request.user).count()
    pending_reviews = 0
    
    # Calculate expected vs completed reviews for each form
    forms_with_stats = []
    for form in forms:
        assigned_count = form.assigned_employees.count()
        expected_reviews_count = assigned_count * (assigned_count - 1) if assigned_count > 1 else 0
        completed_reviews = PeerReview.objects.filter(form=form).count()
        
        forms_with_stats.append({
            'form': form,
            'expected_reviews': expected_reviews_count,
            'completed_reviews': completed_reviews
        })
        
        pending_reviews += expected_reviews_count - completed_reviews
    
    return render(request, 'evaluation/admin_dashboard.html', {
        'forms_with_stats': forms_with_stats,
        'employees': employees,
        'total_reviews': total_reviews,
        'pending_reviews': pending_reviews
    })

@user_passes_test(is_admin)
def create_form(request):
    employees = CustomUser.objects.filter(role='employee')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        questions_raw = request.POST.get('questions')
        assigned_employee_ids = request.POST.getlist('assigned_employees')
        
        questions = [{'text': q.strip()} for q in questions_raw.strip().split('\n') if q.strip()]
        form = EvaluationForm.objects.create(
            title=title,
            description=description,
            questions=questions,
            created_by=request.user
        )
        
        if assigned_employee_ids:
            form.assigned_employees.set(employees.filter(id__in=assigned_employee_ids))
        
        messages.success(request, 'Peer Review Form created successfully!')
        return redirect('admin_dashboard')
    
    return render(request, 'evaluation/create_form.html', {'employees': employees})

@user_passes_test(is_admin)
def view_reviews(request, form_id):
    form = get_object_or_404(EvaluationForm, id=form_id, created_by=request.user)
    reviews = PeerReview.objects.filter(form=form).select_related('reviewer', 'reviewee')
    
    # Organize reviews by reviewee
    reviews_by_reviewee = {}
    for review in reviews:
        if review.reviewee.id not in reviews_by_reviewee:
            reviews_by_reviewee[review.reviewee.id] = {
                'reviewee': review.reviewee,
                'reviews': []
            }
        reviews_by_reviewee[review.reviewee.id]['reviews'].append(review)
    
    return render(request, 'evaluation/view_reviews.html', {
        'form': form,
        'reviews_by_reviewee': reviews_by_reviewee
    })

# Employee views
def is_employee(user):
    return user.is_authenticated and user.role == 'employee'

@user_passes_test(is_employee)
def employee_dashboard(request):
    # Get forms where user is assigned
    assigned_forms = EvaluationForm.objects.filter(
        assigned_employees=request.user,
        is_active=True
    )
    
    # For each form, get colleagues to review
    forms_with_colleagues = []
    for form in assigned_forms:
        colleagues = form.assigned_employees.exclude(id=request.user.id)
        reviewed_colleagues = PeerReview.objects.filter(
            form=form,
            reviewer=request.user
        ).values_list('reviewee_id', flat=True)
        
        pending_colleagues = colleagues.exclude(id__in=reviewed_colleagues)
        
        forms_with_colleagues.append({
            'form': form,
            'total_colleagues': colleagues.count(),
            'reviewed_count': len(reviewed_colleagues),
            'pending_colleagues': pending_colleagues
        })
    
    completed_reviews = PeerReview.objects.filter(reviewer=request.user)
    
    return render(request, 'evaluation/employee_dashboard.html', {
        'forms_with_colleagues': forms_with_colleagues,
        'completed_reviews': completed_reviews
    })

@user_passes_test(is_employee)
def review_colleague(request, form_id, colleague_id):
    form = get_object_or_404(EvaluationForm, id=form_id, is_active=True)
    colleague = get_object_or_404(CustomUser, id=colleague_id, role='employee')
    
    # Check if user is assigned to this form
    if request.user not in form.assigned_employees.all():
        messages.error(request, 'You are not assigned to this form')
        return redirect('employee_dashboard')
    
    # Check if colleague is also assigned to this form
    if colleague not in form.assigned_employees.all():
        messages.error(request, 'This colleague is not assigned to this form')
        return redirect('employee_dashboard')
    
    # Check if already reviewed
    if PeerReview.objects.filter(form=form, reviewer=request.user, reviewee=colleague).exists():
        messages.info(request, 'You have already reviewed this colleague')
        return redirect('employee_dashboard')
    
    if request.method == 'POST':
        responses = {}
        ml_analysis = {}
        
        # Process each question and run ML analysis
        for i, question in enumerate(form.questions):
            answer = request.POST.get(f"question_{i}", '')
            responses[question['text']] = answer
            
            # Run ML analysis
            try:
                from .ml_models.qpsvc import QuestionClassifier
                from .ml_models.genprocess import Brain
                
                classifier = QuestionClassifier()
                brain = Brain()
                
                category, confidence = classifier.classify(question['text'])
                
                if category != "Out of Scope":
                    prediction = brain.brain(category, answer)
                else:
                    prediction = brain.brain("Out of Scope", answer)
                
                ml_analysis[question['text']] = {
                    'category': category,
                    'confidence': float(confidence),
                    'prediction': str(prediction)
                }
            except Exception as e:
                ml_analysis[question['text']] = {
                    'error': str(e)
                }
        
        # Create peer review
        PeerReview.objects.create(
            form=form,
            reviewer=request.user,
            reviewee=colleague,
            responses=responses,
            ml_analysis=ml_analysis
        )
        
        messages.success(request, f'Review for {colleague.username} submitted successfully!')
        return redirect('employee_dashboard')
    
    return render(request, 'evaluation/review_colleague.html', {
        'form': form,
        'colleague': colleague
    })

@login_required
@csrf_exempt
def evaluate_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            answer = data.get('answer', '')

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
