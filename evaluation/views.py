from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
import os
from django.conf import settings

def landing_page(request):
    """Landing page view"""
    return render(request, 'evaluation/landing_page.html')

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basic validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'evaluation/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'evaluation/signup.html')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'evaluation/signup.html')
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'evaluation/signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'evaluation/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('landing_page')

@login_required
def dashboard(request):
    """Dashboard with the evaluation form"""
    return render(request, 'evaluation/dashboard.html')

@login_required
@csrf_exempt
def evaluate_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            answer = data.get('answer', '')
            
            print(f"Received question: {question}")
            print(f"Received answer: {answer}")
            
            # Check if data files exist
            data_path = os.path.join(settings.BASE_DIR, 'evaluation', 'data')
            csv_file = os.path.join(data_path, 'prodvi-dataset-new4.csv')
            question_csv = os.path.join(data_path, 'prodvi-random-questionset.csv')
            
            print(f"Looking for data files in: {data_path}")
            print(f"CSV file exists: {os.path.exists(csv_file)}")
            print(f"Question CSV exists: {os.path.exists(question_csv)}")
            
            # Import ML models
            from .ml_models.qpsvc import QuestionClassifier
            from .ml_models.genprocess import Brain
            
            print("ML models imported successfully")
            
            # Initialize models
            classifier = QuestionClassifier()
            brain = Brain()
            
            print("Models initialized successfully")
            
            # Classify the question
            category, confidence = classifier.classify(question)
            print(f"Classification result: {category}, confidence: {confidence}")
            
            # Get ML prediction for the answer
            if category != "Out of Scope":
                prediction = brain.brain(category, answer)
            else:
                prediction = brain.brain("Out of Scope", answer)
            
            print(f"Brain prediction: {prediction}")
            
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
            print("Error occurred:")
            print(error_details)
            return JsonResponse(error_details, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def generate_report(request, employee_id):
    return JsonResponse({'message': 'Report generation not implemented yet'})
