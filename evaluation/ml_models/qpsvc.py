import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from .genprocess import Brain  # Import the Brain class

class QuestionClassifier:
    def __init__(self):
        # Fixed CSV file and threshold
        self.csv_file = 'clean_slate/prodvi-random-questionset.csv'
        self.threshold = 0.9
        
        # Load the dataset
        self.df = pd.read_csv(self.csv_file)
        self.df['Label'] = self.df['Label'].replace(r'\)', '', regex=True)
        self.df['Label'] = self.df['Label'].replace(r'\(', '', regex=True)
        
        self.x = self.df['Question']  # Features 
        self.y = self.df['Label']  # Target
        
        # Split the data into training and test sets
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(self.x, self.y, test_size=0.3, random_state=31929)
        
        # Create and fit the SVC pipeline
        self.pipeSVC = Pipeline([('tfidf', TfidfVectorizer()), ('clf', LinearSVC())])
        self.pipeSVC.fit(self.X_train, self.y_train)

    def classify(self, input_question):
        decision_scores = self.pipeSVC.decision_function([input_question])
        decision_scores = abs(decision_scores)
        max_score = max(decision_scores[0])  # Get the first decision function score
        
        # Check the maximum score
        if max_score < self.threshold:
            return "Out of Scope", 0.0
        else:
            predicted_label = self.pipeSVC.predict([input_question])
            confidence = max_score  # Confidence score based on the decision function
            return predicted_label[0], confidence

# Example usage
if __name__ == "__main__":
    classifier = QuestionClassifier()
    question = "Is the employee open to feedback from other team members?"
    comment = "No he's absolutely not"

    result, confidence = classifier.classify(question)
    print(f"Predicted label: {result}")
    
    # Create an instance of Brain and call the brain method
    brain_model = Brain()
    brain_result = brain_model.brain(result, comment)  # Pass predicted label and comment
    print(f"Brain model result: {brain_result}")
