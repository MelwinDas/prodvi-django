from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from .models import CustomUser, EvaluationForm, EvaluationResponse, PeerReview, EmployeeSummary 
import json
import traceback
import os
from django.conf import settings
from django.utils import timezone 
from .models import *
from dotenv import load_dotenv
load_dotenv()


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
        
        check_and_generate_summary(colleague, form)
        
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

def generate_summary_file(employee, form):
    """Generate summary file for employee based on all peer reviews"""
    
    # Get all reviews for this employee on this form
    reviews = PeerReview.objects.filter(reviewee=employee, form=form)
    
    if not reviews.exists():
        return None
    
    # Create summary data in format like your examples
    summary_data = {
        "name": employee.username,
        "questions": []
    }
    
    # Organize answers by question
    for question in form.questions:
        question_data = {
            "question": question['text'],
            "answers": []
        }
        
        # Collect all answers for this question from different reviewers
        for review in reviews:
            if question['text'] in review.responses:
                answer = review.responses[question['text']]
                reviewer_name = review.reviewer.username
                question_data['answers'].append(f"{answer} (by {reviewer_name})")
        
        summary_data['questions'].append(question_data)
    
    # Create summaries directory if it doesn't exist
    summaries_dir = os.path.join(settings.BASE_DIR, 'evaluation', 'summaries')
    os.makedirs(summaries_dir, exist_ok=True)
    
    # Save to JSON file
    filename = f"{employee.username}_{form.id}_summary.json"
    file_path = os.path.join(summaries_dir, filename)
    
    with open(file_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    return file_path

def process_with_gemini_api(file_path):
    """Process summary file with Gemini API"""
    try:
        from .ml_models.api import FileProcessor
        processor = FileProcessor()
        analysis = processor.process_new_file(file_path)
        return analysis
    except Exception as e:
        return f"Error processing with Gemini API: {str(e)}"

def check_and_generate_summary(employee, form):
    """Check if all reviews are complete and generate summary"""
    
    # Check if all expected reviews are completed
    assigned_employees = form.assigned_employees.all()
    expected_reviewers = assigned_employees.exclude(id=employee.id)
    
    completed_reviews = PeerReview.objects.filter(
        form=form, 
        reviewee=employee,
        reviewer__in=expected_reviewers
    ).count()
    
    if completed_reviews == expected_reviewers.count() and completed_reviews > 0:
        # All reviews completed, generate summary
        summary, created = EmployeeSummary.objects.get_or_create(
            employee=employee,
            form=form
        )
        
        if created or not summary.gemini_analysis:
            # Generate new summary file
            file_path = generate_summary_file(employee, form)
            if file_path:
                # Process with Gemini API
                analysis = process_with_gemini_api(file_path)
                
                # Save results
                summary.summary_file_path = file_path
                summary.gemini_analysis = analysis
                summary.save()
        
        return summary
    
    return None

@user_passes_test(is_employee)
def my_summary(request, form_id):
    """Employee view to see their own performance summary"""
    form = get_object_or_404(EvaluationForm, id=form_id)
    
    # Check if user was assigned to this form
    if request.user not in form.assigned_employees.all():
        messages.error(request, 'You were not assigned to this form')
        return redirect('employee_dashboard')
    
    # Check and generate summary if ready
    summary = check_and_generate_summary(request.user, form)
    
    if not summary:
        messages.info(request, 'Your performance summary is not ready yet. Please wait for all colleagues to complete their reviews.')
        return redirect('employee_dashboard')
    
    return render(request, 'evaluation/my_summary.html', {
        'summary': summary,
        'form': form,
        'employee': request.user
    })

@user_passes_test(is_admin)
def admin_employee_summary(request, form_id, employee_id):
    print(f"Admin accessing summary: form_id={form_id}, employee_id={employee_id}")
    print(f"User: {request.user}, Role: {request.user.role}")
    
    try:
        form = get_object_or_404(EvaluationForm, id=form_id, created_by=request.user)
        print(f"Form found: {form}")
        
        employee = get_object_or_404(CustomUser, id=employee_id, role='employee')
        print(f"Employee found: {employee}")
        
        summary = check_and_generate_summary(employee, form)
        print(f"Summary: {summary}")
        
        if not summary:
            messages.info(request, f'Summary for {employee.username} is not ready yet.')
            return redirect('admin_summaries_list', form_id=form.id)
        
        return render(request, 'evaluation/employee_summary.html', {
            'summary': summary,
            'form': form,
            'employee': employee
        })
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'Error loading summary')
        return redirect('admin_dashboard')

@user_passes_test(is_admin)
def admin_summaries_list(request, form_id):
    """Admin view to see list of all employee summaries for a form"""
    form = get_object_or_404(EvaluationForm, id=form_id, created_by=request.user)
    
    # Get all assigned employees and their summary status
    employees_data = []
    for employee in form.assigned_employees.all():
        summary = EmployeeSummary.objects.filter(employee=employee, form=form).first()
        
        # Check if summary can be generated
        if not summary:
            summary = check_and_generate_summary(employee, form)
        
        employees_data.append({
            'employee': employee,
            'summary': summary,
            'has_summary': bool(summary and summary.gemini_analysis)
        })
    
    return render(request, 'evaluation/admin_summaries_list.html', {
        'form': form,
        'employees_data': employees_data
    })

@user_passes_test(is_admin)
def refresh_employee_summary(request, form_id, employee_id):
    """Admin can refresh/regenerate employee summary"""
    form = get_object_or_404(EvaluationForm, id=form_id, created_by=request.user)
    employee = get_object_or_404(CustomUser, id=employee_id, role='employee')
    
    try:
        # Get existing summary or create new one
        summary, created = EmployeeSummary.objects.get_or_create(
            employee=employee,
            form=form
        )
        
        # Force regeneration
        file_path = generate_summary_file(employee, form)
        if file_path:
            # Process with Gemini API
            analysis = process_with_gemini_api(file_path)
            
            # Save results
            summary.summary_file_path = file_path
            summary.gemini_analysis = analysis
            summary.generated_at = timezone.now()  # Update timestamp
            summary.save()
            
            if "Error processing with Gemini API" in analysis:
                messages.warning(request, f'Summary refreshed but API error occurred. Please try again.')
            else:
                messages.success(request, f'Summary for {employee.username} has been refreshed successfully!')
        else:
            messages.error(request, 'Could not generate summary file. Please ensure all reviews are completed.')
    
    except Exception as e:
        messages.error(request, f'Error refreshing summary: {str(e)}')
    
    return redirect('admin_employee_summary', form_id=form.id, employee_id=employee.id)

@user_passes_test(is_employee)
def refresh_my_summary(request, form_id):
    """Employee can refresh their own summary"""
    form = get_object_or_404(EvaluationForm, id=form_id)
    
    if request.user not in form.assigned_employees.all():
        messages.error(request, 'You are not assigned to this form')
        return redirect('employee_dashboard')
    
    # Same logic as admin refresh but for current user
    try:
        summary, created = EmployeeSummary.objects.get_or_create(
            employee=request.user,
            form=form
        )
        
        file_path = generate_summary_file(request.user, form)
        if file_path:
            analysis = process_with_gemini_api(file_path)
            summary.summary_file_path = file_path
            summary.gemini_analysis = analysis
            summary.generated_at = timezone.now()
            summary.save()
            
            if "Error processing with Gemini API" in analysis:
                messages.warning(request, 'Summary refreshed but API error occurred. Please try again.')
            else:
                messages.success(request, 'Your performance summary has been refreshed successfully!')
        else:
            messages.error(request, 'Could not generate summary file.')
    
    except Exception as e:
        messages.error(request, f'Error refreshing summary: {str(e)}')
    
    return redirect('my_summary', form_id=form.id)

@login_required
def performance_output(request, form_id, employee_id):
    """Shared performance output page for both admins and employees"""
    form = get_object_or_404(EvaluationForm, id=form_id)
    employee = get_object_or_404(CustomUser, id=employee_id, role='employee')
    
    # Check permissions
    if request.user.role == 'admin':
        if form.created_by != request.user:
            messages.error(request, 'You can only view outputs for your own forms.')
            return redirect('admin_dashboard')
    else:
        if request.user != employee:
            messages.error(request, 'You can only view your own performance output.')
            return redirect('employee_dashboard')
        
        if request.user not in form.assigned_employees.all():
            messages.error(request, 'You are not assigned to this form.')
            return redirect('employee_dashboard')
    
    # Get all reviews for this employee and form
    reviews = PeerReview.objects.filter(reviewee=employee, form=form)
    
    # Calculate ML rating distribution
    rating_counts = {'Excellent': 0, 'Good': 0, 'Average': 0, 'Needs Improvement': 0}
    total_answers = 0
    total_score = 0
    
    for review in reviews:
        try:
            # FIXED: Use correct field name
            answers = json.loads(review.review_data)
            for answer_data in answers:
                if 'ml_rating' in answer_data:
                    rating = answer_data['ml_rating']
                    if rating in rating_counts:
                        rating_counts[rating] += 1
                    total_answers += 1
                    
                    # Calculate score (Excellent=5, Good=4, Average=3, Needs Improvement=2)
                    score_map = {'Excellent': 5, 'Good': 4, 'Average': 3, 'Needs Improvement': 2}
                    total_score += score_map.get(rating, 0)
        except Exception as e:
            print(f"Error processing review: {e}")
            continue
    
    # Calculate overall score
    overall_score = (total_score / total_answers) if total_answers > 0 else 0
    
    # Get or create summary for Gemini conclusion
    try:
        summary = EmployeeSummary.objects.get(employee=employee, form=form)
        gemini_conclusion = summary.gemini_analysis
    except EmployeeSummary.DoesNotExist:
        gemini_conclusion = None
    
    # Prepare chart data
    labels_pie = list(rating_counts.keys())
    data_pie = list(rating_counts.values())
    
    # Mock growth data (replace with actual historical data)
    labels_line = ['Review 1', 'Review 2', 'Review 3', 'Review 4', 'Current']
    data_line = [3.0, 3.2, 3.5, 3.8, max(overall_score, 1.0)]
    
    context = {
        'employee': employee,
        'form': form,
        'total_reviews': reviews.count(),
        'overall_score': overall_score,
        'total_answers': total_answers,
        'excellent_count': rating_counts['Excellent'],
        'improvement_areas': rating_counts['Needs Improvement'],
        'labels_pie': json.dumps(labels_pie),
        'data_pie': json.dumps(data_pie),
        'labels_line': json.dumps(labels_line),
        'data_line': json.dumps(data_line),
        'gemini_conclusion': gemini_conclusion,
    }
    
    return render(request, 'evaluation/output.html', context)


# Employee view (their own output)
@user_passes_test(is_employee)
def my_output(request, form_id):
    """Employee viewing their own performance output"""
    return performance_output(request, form_id, request.user.id)
