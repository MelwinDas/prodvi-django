from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json 
import traceback
from .ml_models.qpsvc import QuestionClassifier
from .ml_models.genprocess import Brain
from .ml_models.api import FileProcessor
from .models import Employee, Evaluation, Response

def index(request):
    return render(request, 'evaluation/index.html')

@csrf_exempt
def evaluate_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question')
            answer = data.get('answer')
            
            # Import here to avoid import-time errors
            from .ml_models.qpsvc import QuestionClassifier
            from .ml_models.genprocess import Brain
            
            # Use your ML models
            classifier = QuestionClassifier()
            brain = Brain()
            
            # Classify the question
            category, confidence = classifier.classify(question)
            
            # Get ML prediction for the answer
            if category != "Out of Scope":
                prediction = brain.brain(category, answer)
            else:
                prediction = brain.brain("Out of Scope", answer)
            
            return JsonResponse({
                'category': category,
                'confidence': float(confidence),
                'prediction': str(prediction)
            })
            
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def generate_report(request, employee_id):
    # Implementation for generating reports
    return JsonResponse({'message': 'Report generation not implemented yet'})
