import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import traceback
import torch

# Import the inference wrapper
from .ml_models.train import ModelBundle

# ---------------------------------------------------------------------------
# Lazy Singleton Loading
# ---------------------------------------------------------------------------

# Restrict PyTorch to a single CPU thread to prevent massive memory spikes causing SIGKILL on Render
torch.set_num_threads(1)
# CRITICAL: Disable all gradient calculations to massively reduce memory overhead during prediction
torch.set_grad_enabled(False)

import gc

_question_bundle = None
_answer_bundle = None
_models_loaded = False

def get_question_bundle():
    global _question_bundle, _answer_bundle, _models_loaded
    if not _models_loaded:
        _load_models()
    return _question_bundle

def get_answer_bundle():
    global _question_bundle, _answer_bundle, _models_loaded
    if not _models_loaded:
        _load_models()
    return _answer_bundle

def _load_models():
    global _question_bundle, _answer_bundle, _models_loaded
    print("Lazily loading PyTorch Models into WSGI memory on first request...")

    Q_MODEL_PATH = os.path.join(settings.BASE_DIR, 'new_models', 'question_classifier.pt')
    A_MODEL_PATH = os.path.join(settings.BASE_DIR, 'new_models', 'answer_classifier.pt')

    try:
        if os.path.exists(Q_MODEL_PATH):
            _question_bundle = ModelBundle.load(Q_MODEL_PATH)
            # Evaluate mode to disable dropout etc
            if hasattr(_question_bundle, 'encoder'):
                _question_bundle.encoder.eval()
            print("✓ Question classifier loaded successfully.")
        else:
            print(f"Warning: {Q_MODEL_PATH} not found.")

        if os.path.exists(A_MODEL_PATH):
            _answer_bundle = ModelBundle.load(A_MODEL_PATH)
            if hasattr(_answer_bundle, 'encoder'):
                _answer_bundle.encoder.eval()
            print("✓ Answer classifier loaded successfully.")
        else:
            print(f"Warning: {A_MODEL_PATH} not found.")
    except Exception as e:
        print(f"Error loading models: {e}")
        traceback.print_exc()

    _models_loaded = True

def unload_models():
    """Aggressively clear PyTorch models from memory to prevent the website from crashing."""
    global _question_bundle, _answer_bundle, _models_loaded
    _question_bundle = None
    _answer_bundle = None
    _models_loaded = False
    # Force python garbage collector to free RAM immediately
    gc.collect()
    print("✓ Cleared PyTorch models from RAM to protect main website stability.")

# ---------------------------------------------------------------------------
# API View
# ---------------------------------------------------------------------------

class EvaluateResponseAPIView(APIView):
    """
    DRF View to replace views.evaluate_response.
    Expected usage via POST:
    {
        "question": "Does this person communicate clearly?",
        "answer": "Yes, very clearly."
    }
    """
    def post(self, request, *args, **kwargs):
        question = request.data.get('question', '').strip()
        answer = request.data.get('answer', '').strip()

        if not question or not answer:
            return Response({"error": "Question and answer required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            q_bundle = get_question_bundle()
            a_bundle = get_answer_bundle()

            if not q_bundle or not a_bundle:
                return Response({"error": "Models not loaded globally."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Predict question category
            category, conf_q = q_bundle.predict(question)

            # Predict rating based on answer
            if category.lower() != "out of scope":
                prediction, conf_a = a_bundle.predict(answer)
                confidence = float(conf_a)
            else:
                prediction, conf_a = a_bundle.predict(answer)
                confidence = float(conf_q) # Question confidence for out of scope

            return Response({
                'category': category,
                'confidence': confidence,
                'prediction': str(prediction),
                'status': 'success'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
