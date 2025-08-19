import pandas as pd
import os
from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from .genprocess import Brain

class QuestionClassifier:
    def __init__(self):
        # Get the correct path to the CSV file
        self.base_path = os.path.join(settings.BASE_DIR, 'evaluation', 'data')
        self.csv_file = os.path.join(self.base_path, 'prodvi-random-questionset.csv')
        self.threshold = 0.9
        
        # Load the dataset
        self.df = pd.read_csv(self.csv_file)
        self.df['Label'] = self.df['Label'].replace(r'\)', '', regex=True)
        self.df['Label'] = self.df['Label'].replace(r'\(', '', regex=True)
        
        self.x = self.df['Question']
        self.y = self.df['Label']
        
        # Split the data into training and test sets
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.x, self.y, test_size=0.3, random_state=31929
        )
        
        # Create and fit the SVC pipeline
        self.pipeSVC = Pipeline([('tfidf', TfidfVectorizer()), ('clf', LinearSVC())])
        self.pipeSVC.fit(self.X_train, self.y_train)
    
    def classify(self, input_question):
        decision_scores = self.pipeSVC.decision_function([input_question])
        decision_scores = abs(decision_scores)
        max_score = max(decision_scores[0])
        
        if max_score < self.threshold:
            return "Out of Scope", 0.0
        else:
            predicted_label = self.pipeSVC.predict([input_question])
            confidence = max_score
            return predicted_label, confidence

# Remove the example usage code that runs during import
