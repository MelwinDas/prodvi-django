import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from nltk.sentiment.vader import SentimentIntensityAnalyzer

class Brain:
    def brain(self, column, comment):  
        if column == "Out of Scope": 
            score = SentimentIntensityAnalyzer().polarity_scores(comment) 
            print(score) 
            return score  # Return the sentiment score for out-of-scope comments
        else: 
            # Load the dataset
            df = pd.read_csv('clean_slate/prodvi-dataset-new4.csv')

            # Split the column
            df[['Text', 'Label']] = df[column].str.split('(', expand=True)
            df['Label'] = df['Label'].replace(r'\)', '', regex=True)

            # Define features and target as Series
            x = df['Text']  # x is a Series (1D)
            y = df['Label']  # y is also a Series (1D)

            columnlist = {
                'Ease_of_Working_Together': 7374,
                'Cooperation': 48482,
                'Work_Ethics': 15053,
                'Areas_to_Improve': 28509,
                'Helps_Others': 563,
                'Punctuality': 6758,
                'Work_Efficiency': 33691,
                'Problem_Solving': 1475,
                'Adaptability': 4633,
                'Communication': 10425,
                'Innovation': 5086,
                'Leadership': 1237, 
                'Self_Motivation': 1643, 
                'Emotional_Intelligence': 18730
            }
            
            # Ensure correct random_state based on column key
            random_state = columnlist.get(column, 42)  # Default random state if column not found

            # Split the data into training and test sets
            X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=random_state)

            # Define and train the SVC pipeline
            pipeSVC = Pipeline([('tfidf', TfidfVectorizer()), ('clf', LinearSVC())])
            pipeSVC.fit(X_train, y_train)

            # Predict using the SVC model
            prediction = pipeSVC.predict([comment])
            
            return prediction[0]  # Return the predicted label



# Example usage
model = Brain()
result = model.brain("Cooperation", "Crazy good at lifting up the mood")
print(result)
