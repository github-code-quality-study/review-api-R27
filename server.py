import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            
            # Write your code here
            query = parse_qs(environ["QUERY_STRING"])
            location = query.get('location', [None])[0]
            start_date = query.get('start_date', [None])[0]
            end_date = query.get('end_date', [None])[0]

            filtered_reviews = reviews
            # Filter by location
            if location:
                filtered_reviews = [review for review in reviews if review['Location'] == location]
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if end_date:
                 end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            filtered_reviews = [review for review in filtered_reviews if ((not start_date or datetime.strptime(review['Timestamp'], '%Y-%m-%d %H:%M:%S') >= start_date) and (not end_date or datetime.strptime(review['Timestamp'], '%Y-%m-%d %H:%M:%S') <= end_date))]
            for review in filtered_reviews:
                review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])
            filtered_reviews.sort(key=lambda x: x['sentiment']['compound'], reverse=True)

            response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")
            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                content_length = 0
            if content_length > 0:
                request_body = environ['wsgi.input'].read(content_length)
                try:
                    review_data = json.loads(request_body)
                except ValueError:
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [json.dumps({"error": "Invalid JSON format"}).encode("utf-8")]
                if 'Location' not in review_data or 'ReviewBody' not in review_data:
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [json.dumps({"error": "Location and ReviewBody are required fields"}).encode("utf-8")]
                #adding the new review
                review_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_review = {
                'ReviewId': review_id,
                'Location': review_data['Location'],
                'Timestamp': timestamp,
                'ReviewBody': review_data['ReviewBody']
                }
                reviews.append(new_review)

                #analysing sentiment for the new review
                new_review['sentiment'] = self.analyze_sentiment(new_review['ReviewBody'])

                #response body with the new data
                response_body = json.dumps(new_review, indent=2).encode("utf-8")

            start_response("201 Created", [("Content-Type", "application/json"),("Content-Length", str(len(response_body)))])

            return [response_body]
        else:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [json.dumps({"error": "Empty request body"}).encode("utf-8")]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()