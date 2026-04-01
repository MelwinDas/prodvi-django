import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import traceback

# Import the inference wrapper
from .ml_models.train import ModelBundle

# ---------------------------------------------------------------------------
# Global Singleton Loading
# ---------------------------------------------------------------------------

print("Loading PyTorch Models into WSGI memory...")

Q_MODEL_PATH = os.path.join(settings.BASE_DIR, 'new_models', 'question_classifier.pt')
A_MODEL_PATH = os.path.join(settings.BASE_DIR, 'new_models', 'answer_classifier.pt')

try:
    if os.path.exists(Q_MODEL_PATH):
        question_bundle = ModelBundle.load(Q_MODEL_PATH)
        print("✓ Question classifier loaded successfully globally.")
    else:
        question_bundle = None
        print(f"Warning: {Q_MODEL_PATH} not found.")

    if os.path.exists(A_MODEL_PATH):
        answer_bundle = ModelBundle.load(A_MODEL_PATH)
        print("✓ Answer classifier loaded successfully globally.")
    else:
        answer_bundle = None
        print(f"Warning: {A_MODEL_PATH} not found.")
except Exception as e:
    print(f"Error loading models globally: {e}")
    traceback.print_exc()
    question_bundle = None
    answer_bundle = None

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
            if not question_bundle or not answer_bundle:
                return Response({"error": "Models not loaded globally."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Predict question category
            category, conf_q = question_bundle.predict(question)

            # Predict rating based on answer
            if category.lower() != "out of scope":
                prediction, conf_a = answer_bundle.predict(answer)
                confidence = float(conf_a)
            else:
                prediction, conf_a = answer_bundle.predict(answer)
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
