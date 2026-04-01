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
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        role = request.POST.get('role', 'employee')
        department = request.POST.get('department', '')
        employee_id = request.POST.get('employee_id', '')
        terms = request.POST.get('terms')

        # Preserve form values for re-render
        form_data = {
            'username': username, 'email': email, 'role': role,
            'department': department, 'employee_id': employee_id,
        }

        if not terms:
            messages.error(request, 'You must agree to the Terms of Service and Privacy Policy.')
            return render(request, 'evaluation/signup.html', {'form_data': form_data})
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'evaluation/signup.html', {'form_data': form_data})
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'evaluation/signup.html', {'form_data': form_data})
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'evaluation/signup.html', {'form_data': form_data})

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
            return render(request, 'evaluation/signup.html', {'form_data': form_data})
    return render(request, 'evaluation/signup.html')

def login_view(request):
    submitted_username = ''
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        submitted_username = username
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('employee_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'evaluation/login.html', {'submitted_username': submitted_username})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('landing_page')

# Admin views
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin view to see all evaluation forms"""
    forms = EvaluationForm.objects.all().order_by('-created_at')
    employees = CustomUser.objects.filter(role='employee')
    
    # Calculate statistics
    total_reviews = PeerReview.objects.all().count()
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
    form = get_object_or_404(EvaluationForm, id=form_id)
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
    ).prefetch_related('assigned_employees')
    
    # For each form, get colleagues to review
    forms_with_colleagues = []
    for form in assigned_forms:
        # Generalized fix: only review other employees, exclude self and admins
        colleagues = form.assigned_employees.filter(role='employee').exclude(id=request.user.id)
        
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
        # Using enumerate to match typical indexed questions if IDs are missing
        for i, question in enumerate(form.questions):
            # Match field names from template (answers_N and ratings_N)
            # Use index 'i' as the primary lookup to match forloop.counter0 in template
            answer = request.POST.get(f"answers_{i}", request.POST.get(f"answers_{question.get('id','')}", ''))
            rating = request.POST.get(f"ratings_{i}", request.POST.get(f"ratings_{question.get('id','')}", ''))
            
            responses[question['text']] = {
                'answer': answer,
                'rating': rating
            }

            # Run ML analysis
            try:
                from .api_views import get_question_bundle, get_answer_bundle
                
                q_bundle = get_question_bundle()
                a_bundle = get_answer_bundle()

                if not q_bundle or not a_bundle:
                    raise Exception("ML models are not loaded in WSGI memory")

                category, conf_q = q_bundle.predict(question['text'])

                if category.lower() != "out of scope":
                    prediction, conf_a = a_bundle.predict(answer)
                    confidence = float(conf_a)
                else:
                    prediction, conf_a = a_bundle.predict(answer)
                    confidence = float(conf_q)

                ml_analysis[question['text']] = {
                    'category': category,
                    'confidence': confidence,
                    'prediction': str(prediction),
                    'rating': rating
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
        'colleague': colleague,
        'questions': form.questions
    })

def generate_summary_file(employee, form):
    """Generate summary txt file for employee based on all peer reviews"""
    
    # Get all reviews for this employee on this form
    reviews = PeerReview.objects.filter(reviewee=employee, form=form)
    
    if not reviews.exists():
        return None
    
    # Build the custom txt payload
    lines = []
    lines.append("{")
    lines.append(f'name="{employee.username}",')
    lines.append("questions=[")
    
    for i, question in enumerate(form.questions):
        lines.append("    {")
        lines.append(f'        question="{question["text"]}",')
        lines.append("        answers=[")
        
        # Collect all answers for this question from different reviewers
        answers_for_q = []
        for review in reviews:
            if question['text'] in review.responses:
                ans_data = review.responses[question['text']]
                # Sometimes it's a dict depending on schema changes, extract just string
                ans_text = ans_data.get('answer', str(ans_data)) if isinstance(ans_data, dict) else str(ans_data)
                
                # Optionally append the classifier prediction if available
                if review.ml_analysis and question['text'] in review.ml_analysis:
                    pred = review.ml_analysis[question['text']].get('prediction', '')
                    if pred:
                        ans_text = f"{ans_text} ({pred})"
                
                answers_for_q.append(f'                "{ans_text}"')
        
        # Join all answers separating by comma
        if answers_for_q:
            lines.append(",\n".join(answers_for_q))
        
        lines.append("                ]")
        # Append closing brace; if it's the last question, omit trailing comma? (larson.txt doesn't have commas between objects but let's emulate closely)
        lines.append("    }")
    
    lines.append("          ]")
    lines.append("}")
    
    content = "\n".join(lines)
    
    # Create summaries directory if it doesn't exist
    summaries_dir = os.path.join(settings.BASE_DIR, 'evaluation', 'summaries')
    os.makedirs(summaries_dir, exist_ok=True)
    
    # Save to TXT file
    filename = f"{employee.username}_{form.id}_summary.txt"
    file_path = os.path.join(summaries_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

def process_with_gemini_api(file_path):
    """Process summary file with Gemini API"""
    try:
        from .ml_models.api import FileProcessor
        processor = FileProcessor()
        analysis = processor.process_new_file(file_path)
        return analysis
    except Exception as e:
        print(f"Error in evaluate_with_gemini: {e}")
        return f"Error processing with Groq API: {str(e)}"

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
        
        if created or not summary.gemini_analysis or "Error processing with Groq API" in summary.gemini_analysis:
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

def generate_team_summary_file(form):
    """Generate summary txt file for the whole team based on all peer reviews"""
    reviews = PeerReview.objects.filter(form=form)
    if not reviews.exists():
        return None
    
    lines = []
    lines.append("{")
    lines.append(f'form="{form.title}",')
    lines.append("team_members=[")
    
    employees = set(r.reviewee for r in reviews)
    for emp in employees:
        emp_reviews = reviews.filter(reviewee=emp)
        lines.append("    {")
        lines.append(f'        name="{emp.username}",')
        lines.append("        questions=[")
        
        for question in form.questions:
            lines.append("            {")
            lines.append(f'                question="{question["text"]}",')
            lines.append("                answers=[")
            
            answers_for_q = []
            for review in emp_reviews:
                if question['text'] in review.responses:
                    ans_data = review.responses[question['text']]
                    ans_text = ans_data.get('answer', str(ans_data)) if isinstance(ans_data, dict) else str(ans_data)
                    
                    if review.ml_analysis and question['text'] in review.ml_analysis:
                        pred = review.ml_analysis[question['text']].get('prediction', '')
                        if pred:
                            ans_text = f"{ans_text} ({pred})"
                    
                    answers_for_q.append(f'                    "{ans_text}"')
            
            if answers_for_q:
                lines.append(",\n".join(answers_for_q))
                
            lines.append("                ]")
            lines.append("            }")
            
        lines.append("        ]")
        lines.append("    }")
        
    lines.append("]")
    lines.append("}")
    
    content = "\n".join(lines)
    
    summaries_dir = os.path.join(settings.BASE_DIR, 'evaluation', 'summaries')
    os.makedirs(summaries_dir, exist_ok=True)
    
    filename = f"Team_{form.id}_summary.txt"
    file_path = os.path.join(summaries_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return file_path

def process_team_with_gemini_api(file_path):
    """Process team summary file with Gemini API"""
    try:
        from .ml_models.api import FileProcessor
        processor = FileProcessor()
        analysis = processor.process_team_file(file_path)
        return analysis
    except Exception as e:
        print(f"Error in evaluate_with_gemini: {e}")
        return f"Error processing with Groq API: {str(e)}"

def check_and_generate_team_summary(form):
    """Generate team summary using all available reviews (no strict completion check)"""
    reviews = PeerReview.objects.filter(form=form)
    if not reviews.exists():
        return None
        
    summary, created = TeamSummary.objects.get_or_create(form=form)
    
    if created or not summary.ai_analysis or "Error processing with Groq API" in summary.ai_analysis:
        file_path = generate_team_summary_file(form)
        if file_path:
            analysis = process_team_with_gemini_api(file_path)
            summary.ai_analysis = analysis
            summary.save()
            
    return summary

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
        form = get_object_or_404(EvaluationForm, id=form_id)
        print(f"Form found: {form}")
        
        employee = get_object_or_404(CustomUser, id=employee_id)
        print(f"User found: {employee}")
        
        # Self-healing: Check for and fix any reviews with AI errors
        detailed_reviews = PeerReview.objects.filter(reviewee=employee, form=form)
        for review in detailed_reviews:
            if any('error' in str(v) for v in review.ml_analysis.values()) or not review.ml_analysis:
                re_evaluate_review(review)
        
        # Refresh summary if needed
        summary = EmployeeSummary.objects.filter(employee=employee, form=form).first()

        return render(request, 'evaluation/employee_summary.html', {
            'summary': summary,
            'form': form,
            'employee': employee,
            'detailed_reviews': detailed_reviews
        })
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'Error loading summary')
        return redirect('login')

def re_evaluate_review(review):
    """Re-run ML analysis for a single review to fix errors or update data"""
    try:
        from .api_views import get_question_bundle, get_answer_bundle
        q_bundle = get_question_bundle()
        a_bundle = get_answer_bundle()
        
        if not q_bundle or not a_bundle:
            return False
            
        new_ml_analysis = {}
        for q_text, resp in review.responses.items():
            category, conf_q = q_bundle.predict(q_text)
            if category.lower() != "out of scope":
                prediction, conf_a = a_bundle.predict(resp['answer'])
                confidence = float(conf_a)
            else:
                prediction, conf_a = a_bundle.predict(resp['answer'])
                confidence = float(conf_q)
                
            new_ml_analysis[q_text] = {
                'category': category,
                'confidence': confidence,
                'prediction': str(prediction),
                'rating': resp.get('rating', '')
            }
        
        review.ml_analysis = new_ml_analysis
        review.save()
        return True
    except Exception as e:
        print(f"Re-evaluation failed: {e}")
        return False

@user_passes_test(is_admin)
def admin_summaries_list(request, form_id):
    """Admin view to see list of all employee summaries for a form"""
    form = get_object_or_404(EvaluationForm, id=form_id)
    
    # Get all assigned employees and their summary status
    employees_data = []
    for employee in form.assigned_employees.all():
        summary = EmployeeSummary.objects.filter(employee=employee, form=form).first()
        
        # Check if summary can be generated
        if not summary:
            # First, heal any reviews for this employee before generating summary
            for review in PeerReview.objects.filter(reviewee=employee, form=form):
                if any('error' in str(v) for v in review.ml_analysis.values()) or not review.ml_analysis:
                    re_evaluate_review(review)
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
    form = get_object_or_404(EvaluationForm, id=form_id)
    employee = get_object_or_404(CustomUser, id=employee_id)
    
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
            
            if "Error processing with Groq API" in analysis:
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
            
            if "Error processing with Groq API" in analysis:
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
    employee = get_object_or_404(CustomUser, id=employee_id)
    
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
    rating_counts = {'Excellent': 0, 'Good': 0, 'Satisfactory': 0, 'Needs Improvement': 0}
    total_answers = 0
    total_score = 0
    
    score_map = {'Excellent': 5, 'Good': 4, 'Satisfactory': 3, 'Needs Improvement': 2}

    for review in reviews:
        try:
            # Process ML analysis and ratings
            # The structure of ml_analysis is {question_text: {category: X, prediction: Y}}
            if review.ml_analysis:
                for q_text, analysis in review.ml_analysis.items():
                    # Both prediction and rating can be used
                    rating = analysis.get('prediction') or analysis.get('rating')
                    if rating in rating_counts:
                        rating_counts[rating] += 1
                        total_answers += 1
                        total_score += score_map.get(rating, 0)
            
            # If ML analysis is missing or not containing ratings, check responses for manual ratings
            elif isinstance(review.responses, dict):
                for q_text, resp in review.responses.items():
                    if isinstance(resp, dict) and 'rating' in resp:
                        # Convert numeric rating to label if needed
                        val = str(resp['rating'])
                        num_map = {'5': 'Excellent', '4': 'Good', '3': 'Satisfactory', '2': 'Needs Improvement', '1': 'Needs Improvement'}
                        label = num_map.get(val, 'Satisfactory')
                        rating_counts[label] += 1
                        total_answers += 1
                        total_score += score_map.get(label, 0)
        except Exception as e:
            print(f"Error processing review {review.id}: {e}")
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
@user_passes_test(is_employee)
def fill_evaluation(request, form_id):
    form = get_object_or_404(EvaluationForm, id=form_id, is_active=True)
    
    if request.user not in form.assigned_employees.all():
        messages.error(request, 'You are not assigned to this form')
        return redirect('employee_dashboard')

    # Check if already submitted
    if EvaluationResponse.objects.filter(form=form, employee=request.user).exists():
        messages.info(request, 'You have already submitted your self-evaluation for this form')
        return redirect('employee_dashboard')

    if request.method == 'POST':
        responses = {}
        for i, question in enumerate(form.questions):
            answer = request.POST.get(f"answers_{question.get('id', i)}", '')
            rating = request.POST.get(f"ratings_{question.get('id', i)}", '')
            responses[question['text']] = {
                'answer': answer,
                'rating': rating
            }

        EvaluationResponse.objects.create(
            form=form,
            employee=request.user,
            responses=responses
        )

        messages.success(request, 'Your self-evaluation has been submitted successfully!')
        return render(request, 'evaluation/submission_result.html')

    return render(request, 'evaluation/fill_evaluation_form.html', {
        'form': form,
        'questions': form.questions
    })

@user_passes_test(is_admin)
def re_evaluate_employee_reviews(request, form_id, employee_id):
    """Force re-run ML classification for an employee's reviews"""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    
    form = get_object_or_404(EvaluationForm, id=form_id)
    employee = get_object_or_404(CustomUser, id=employee_id)
    reviews = PeerReview.objects.filter(form=form, reviewee=employee)
    
    success_count = 0
    for review in reviews:
        if re_evaluate_review(review):
            success_count += 1
            
    if success_count:
        messages.success(request, f"Successfully fixed and re-labeled {success_count} reviews!")
    else:
        messages.error(request, "Found no reviews to fix or AI service is unavailable.")
        
    return redirect('view_reviews', form_id=form_id)


# ---------------------------------------------------------------------------
# Analytics Views
# ---------------------------------------------------------------------------

# Label → numeric score mapping.
# Scores range: -1.0 (very negative) → 1.0 (very positive)
# Neutral/baseline labels score around 0.0
_LABEL_SCORES = {
    # Ease of Working Together
    'Very Easy': 1.0,
    'Easy': 0.6,
    'Neutral': 0.0,
    'Difficult': -0.6,
    'Very Difficult': -1.0,

    # Cooperation / Helps Others
    'Highly Cooperative': 1.0,
    'Always': 1.0,
    'Often': 0.7,
    'Cooperative': 0.6,
    'Sometimes': 0.0,
    'Rarely': -0.5,
    'Not Cooperative': -0.7,
    'Very Uncooperative': -1.0,
    'Never': -1.0,

    # Work Ethics
    'Excellent': 1.0,
    'Good': 0.6,
    'Average': 0.0,
    'Poor': -0.7,
    'Very Poor': -1.0,

    # Punctuality
    'Always on time': 1.0,
    'Usually on time': 0.6,
    'Sometimes Late': -0.2,
    'Frequently Late': -0.8,

    # Work Efficiency
    'Highly Efficient': 1.0,
    'Moderately Efficient': 0.5,
    'Average Efficiency': 0.0,
    'Needs Improvement': -0.6,

    # Problem Solving
    'Exceptional Problem Solver': 1.0,
    'Good Problem Solver': 0.6,
    'Average Problem Solver': 0.0,
    'Struggles with Problem Solving': -0.7,

    # Adaptability
    'Highly Adaptable': 1.0,
    'Moderately Adaptable': 0.5,
    'Somewhat Adaptable': 0.1,
    'Resistant to Change': -0.8,

    # Communication
    'Excellent Communicator': 1.0,
    'Good Communicator': 0.6,
    'Average Communicator': 0.0,
    'Needs Improvement in Communication': -0.7,

    # Innovation
    'Highly Innovative': 1.0,
    'Moderately Innovative': 0.5,
    'Average Innovator': 0.0,
    'Limited Innovation': -0.7,

    # Leadership
    'Strong Leader': 1.0,
    'Good Leader': 0.6,
    'Moderate Leadership Skills': 0.1,
    'Struggles with Leadership': -0.8,

    # Self Motivation
    'Highly Self-Motivated': 1.0,
    'Moderately Self-Motivated': 0.5,
    'Somewhat Self-Motivated': 0.1,
    'Low Self-Motivation': -0.8,

    # Emotional Intelligence
    'Highly Emotionally Intelligent': 1.0,
    'Moderate Emotional Intelligence': 0.3,
    'Somewhat Emotionally Intelligent': 0.0,
    'Low Emotional Intelligence': -0.8,
}


def _label_to_score(prediction):
    """Return a numeric score for a prediction label. Falls back to 0 if unknown."""
    if not prediction:
        return 0.0
    # Direct lookup
    if prediction in _LABEL_SCORES:
        return _LABEL_SCORES[prediction]
    # Substring fuzzy match — covers labels with minor wording
    pred_lower = prediction.lower()
    for label, score in _LABEL_SCORES.items():
        if label.lower() in pred_lower or pred_lower in label.lower():
            return score
    return 0.0


def _build_analytics_data(reviews):
    """
    Aggregate PeerReview ML analysis into chart-ready structures.
    Returns a dict with keys:
      - category_counts:   {category: count}
      - prediction_counts: {prediction: count}
      - category_scores:   {category: avg_numeric_score}  ← used for all charts
      - category_confidence: {category: avg_confidence}   ← kept for heatmap only
      - drill_down:        {category: [{question, answer, prediction, confidence, score, reviewer}]}
    """
    category_counts = {}
    prediction_counts = {}
    category_score_sum = {}
    category_confidence_sum = {}
    category_n = {}
    drill_down = {}

    for review in reviews:
        if not review.ml_analysis:
            continue
        for q_text, ml_data in review.ml_analysis.items():
            if 'error' in ml_data:
                continue
            cat = ml_data.get('category', 'General').replace('_', ' ').title()
            pred = ml_data.get('prediction', 'Unknown')
            conf = float(ml_data.get('confidence', 0))
            score = _label_to_score(pred)

            # Get the actual answer text
            answer_data = review.responses.get(q_text, {})
            if isinstance(answer_data, dict):
                answer_text = answer_data.get('answer', '')
            else:
                answer_text = str(answer_data)

            # Skip empty answers for drill-down display
            if not answer_text.strip():
                continue

            category_counts[cat] = category_counts.get(cat, 0) + 1
            prediction_counts[pred] = prediction_counts.get(pred, 0) + 1
            category_score_sum[cat] = category_score_sum.get(cat, 0) + score
            category_confidence_sum[cat] = category_confidence_sum.get(cat, 0) + conf
            category_n[cat] = category_n.get(cat, 0) + 1

            if cat not in drill_down:
                drill_down[cat] = []
            drill_down[cat].append({
                'question': q_text,
                'answer': answer_text,
                'prediction': pred,
                'score': round(score, 2),
                'confidence': round(conf, 2),
                'reviewer': review.reviewer.username,
            })

    # Average score per category (used for all chart plotting)
    category_scores = {
        cat: round(category_score_sum[cat] / category_n[cat], 2)
        for cat in category_n
    }
    # Average confidence per category (shown only in heatmap row)
    category_confidence = {
        cat: round(category_confidence_sum[cat] / category_n[cat], 2)
        for cat in category_n
    }

    return {
        'category_counts': category_counts,
        'prediction_counts': prediction_counts,
        'category_scores': category_scores,
        'category_confidence': category_confidence,
        'drill_down': drill_down,
        'total_reviews': len(reviews),
    }


@login_required
def personal_analytics(request, form_id, employee_id=None):
    """
    Personal analytics dashboard.
    - Employee: can only view their own (employee_id ignored / redirected).
    - Admin: can view anyone via employee_id parameter.
    """
    form = get_object_or_404(EvaluationForm, id=form_id)

    if request.user.role == 'admin':
        if employee_id:
            employee = get_object_or_404(CustomUser, id=employee_id)
        else:
            # Admin viewing without choosing — show first employee
            employee = form.assigned_employees.filter(role='employee').first()
            if not employee:
                messages.error(request, "No employees assigned to this form.")
                return redirect('admin_dashboard')
    else:
        # Employees can only see their own data
        employee = request.user
        if employee not in form.assigned_employees.all():
            messages.error(request, "You are not assigned to this form.")
            return redirect('employee_dashboard')

    reviews = PeerReview.objects.filter(form=form, reviewee=employee).select_related('reviewer')
    analytics = _build_analytics_data(list(reviews))

    # All employees in the form for the admin switcher
    all_employees = form.assigned_employees.filter(role='employee') if request.user.role == 'admin' else []

    return render(request, 'evaluation/personal_analytics.html', {
        'form': form,
        'employee': employee,
        'analytics': analytics,
        'analytics_json': json.dumps(analytics),
        'all_employees': all_employees,
        'drill_down_json': json.dumps(analytics.get('drill_down', {})),
    })


@user_passes_test(is_admin)
@user_passes_test(is_admin)
def refresh_team_summary(request, form_id):
    """Regenerate the team-level AI summary for a form"""
    form = get_object_or_404(EvaluationForm, id=form_id)
    
    try:
        # Force a regeneration by deleting existing
        TeamSummary.objects.filter(form=form).delete()
        file_path = generate_team_summary_file(form)
        if file_path:
            analysis = process_team_with_gemini_api(file_path)
            TeamSummary.objects.create(form=form, ai_analysis=analysis, summary_file_path=file_path if hasattr(TeamSummary, 'summary_file_path') else '')
        messages.success(request, 'Team summary regenerated successfully')
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'Failed to regenerate team summary: {e}')
        
    return redirect('admin_team_analytics', form_id=form.id)


def admin_team_analytics(request, form_id):
    """
    Admin-only team comparison dashboard.
    Builds per-employee analytics and cross-employee comparison datasets.
    """
    form = get_object_or_404(EvaluationForm, id=form_id)
    employees = form.assigned_employees.filter(role='employee')

    # Automatically generate team summary if it doesn't exist
    team_summary = check_and_generate_team_summary(form)

    team_data = []
    all_categories = set()

    for emp in employees:
        reviews = PeerReview.objects.filter(form=form, reviewee=emp).select_related('reviewer')
        analytics = _build_analytics_data(list(reviews))
        all_categories.update(analytics['category_counts'].keys())
        team_data.append({
            'employee': emp,
            'analytics': analytics,
        })

    # Build comparison chart datasets
    all_categories = sorted(all_categories)

    colors = ['#3952bc', '#72479e', '#0058ba', '#059669', '#dc2626', '#d97706', '#7c3aed']

    # Grouped bar: each employee's review COUNT per category (kept for heatmap table)
    comparison_datasets = []
    for i, td in enumerate(team_data):
        color = colors[i % len(colors)]
        comparison_datasets.append({
            'label': td['employee'].username,
            'data': [td['analytics']['category_counts'].get(cat, 0) for cat in all_categories],
            'backgroundColor': color + '99',
            'borderColor': color,
            'borderWidth': 2,
        })

    # Grouped bar: each employee's average label score per category
    comparison_score_datasets = []
    for i, td in enumerate(team_data):
        color = colors[i % len(colors)]
        comparison_score_datasets.append({
            'label': td['employee'].username,
            'data': [td['analytics']['category_scores'].get(cat, 0) for cat in all_categories],
            'backgroundColor': color + '99',
            'borderColor': color,
            'borderWidth': 2,
        })

    # Radar: average label SCORE per category per employee (not confidence)
    radar_datasets = []
    for i, td in enumerate(team_data):
        color = colors[i % len(colors)]
        radar_datasets.append({
            'label': td['employee'].username,
            'data': [td['analytics']['category_scores'].get(cat, 0) for cat in all_categories],
            'backgroundColor': color + '33',
            'borderColor': color,
            'borderWidth': 2,
            'pointBackgroundColor': color,
        })

    # Ranking: sort employees by total reviews received
    ranking = sorted(team_data, key=lambda x: x['analytics']['total_reviews'], reverse=True)

    return render(request, 'evaluation/admin_analytics.html', {
        'form': form,
        'team_data': team_data,
        'all_categories': all_categories,
        'comparison_datasets_json': json.dumps(comparison_datasets),
        'comparison_score_datasets_json': json.dumps(comparison_score_datasets),
        'radar_datasets_json': json.dumps(radar_datasets),
        'all_categories_json': json.dumps(all_categories),
        'ranking': ranking,
        'team_summary': team_summary,
    })
