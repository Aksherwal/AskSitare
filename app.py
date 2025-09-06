from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from groq import Groq
import os
import requests
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from collections import Counter
import json
from datetime import datetime, timedelta
import re

# Load environment variables from .env if present (local dev)
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# queary=""" From the text given above, write a vey brief and precise anaswer of this question(if it can be answered from the text) in a formal language but do not mension that you are giving the answer from any text and also give the link if any(otherwise dont mention about the link) in the text only in clickable fromat at the last of answer to know more, if the question is irrelevent, show appropriate message, the question is: """
queary=""" From this text, answer shortly the question given next (if the text contains the answer) without mentioning the text,
if text has link, give the link in the end of answer only as plain text otherwise don't mention about the link if it's not present,
if the question is irrelevant, show appropriate message,
the question is: """
# Remote embeddings via your hf.space endpoint (keeps 384-dim vectors)
EMBED_API_URL = os.getenv("EMBED_API_URL", "https://aksherwal110-transformer.hf.space/embed")
_requests_session = requests.Session()

# Function to generate embedding for user question
def generate_embedding(question: str):
    response = _requests_session.post(
        EMBED_API_URL,
        json={"text": question},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list):
        raise ValueError("Invalid embedding response from embedding service")
    return embedding

# Database connection parameters
DB_PARAMS = {
    "dbname": "suchatbot",
    "user": "avnadmin",
    "password": os.getenv("password"),
    "host": os.getenv("host"),
    "port": 13189
}
# Connect to the database
conn = psycopg2.connect(**DB_PARAMS)
cursor = conn.cursor(cursor_factory=RealDictCursor)

def get_top_similar_questions(user_question, top_n=5):
    # Generate embedding for the user question
    user_embedding = generate_embedding(user_question)

    # Query to calculate similarity and retrieve top N questions
    query = f"""
        SELECT
            sr_no,
            topic_id,
            question,
            1 - (embedding <=> %s::VECTOR) AS similarity  -- Cast to VECTOR
        FROM
            questions
        ORDER BY
            similarity DESC
        LIMIT %s;
        """

    cursor.execute(query, (user_embedding, top_n))
    top_questions = cursor.fetchall()

    # Retrieve paragraphs for the corresponding topic_ids
    topic_ids = tuple(q['topic_id'] for q in top_questions)
    paragraphs_query = """
    SELECT topic_id, paragraph
    FROM topics
    WHERE topic_id IN %s;
    """
    cursor.execute(paragraphs_query, (topic_ids,))
    paragraphs = cursor.fetchall()

    # Map topic_id to paragraphs for display
    paragraphs_dict = {p['topic_id']: p['paragraph'] for p in paragraphs}

    # Combine the questions and paragraphs
    result = []
    for question in top_questions:
        result.append({
            "sr_no": question["sr_no"],
            "question": question["question"],
            "similarity": question["similarity"],
            "paragraph": paragraphs_dict.get(question["topic_id"], "No paragraph found")
        })

    # cursor.close()
    # conn.close()
    return result

app = Flask(__name__)

app.secret_key = 'su-sitare-chatbot' 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    # Process the message here and generate a response
    top_results=get_top_similar_questions(user_message)

    sourcetext=""
    for i in range(len(top_results)):
        if top_results[i]['paragraph'] not in sourcetext:
            sourcetext+=(" "+top_results[i]['paragraph'])

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",                          # model
        messages=[
            {"role": "system", "content": "You are a University chatbot assistent specialized in English language"},
            {"role": "user", "content": sourcetext+queary+user_message}
            ],
            temperature=1,                                       # Controls creativity (higher = more creative)
            max_tokens=1024,                                     # Limit on response length
            top_p=1,                                             # Sampling parameter for diverse outputs
            stream=True,                                         # Enables streaming
            stop=None                                            # No stop sequence
        )
    # Process and print the streamed response
    response_message=""
    for chunk in completion:
        response_message+=chunk.choices[0].delta.content or ""
  
    
    return jsonify({'response': response_message})

@app.route('/feedback', methods=['POST'])
def record_feedback():
    data = request.json
    question_text = data.get('question_text')
    feedback = data.get('feedback')                               # 1 for like, 0 for dislike

    if not question_text or feedback not in [0, 1]:
        return jsonify({'error': 'Invalid data'}), 400

    try:
        # Insert feedback into the database
        cursor.execute(
            """
            INSERT INTO feedback (question_text, feedback)
            VALUES (%s, %s)
            """,
            (question_text, feedback)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == "admin" and password=="aks@sitare123":
            session['username'] = username
            return redirect(url_for('admin'))
        else:
            error = 'Invalid username or password'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    cursor.execute(" select * from feedback")
    data=cursor.fetchall()
    return render_template('admin.html', data=data)


@app.route('/feedback-analysis')
def feedback_analysis():
    """Route for the feedback analysis page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('feedback_analysis.html')

@app.route('/api/feedback-analytics')
def get_feedback_analytics():
    """API endpoint to get all analytics data"""
    try:
        # Get all feedback data
        cursor.execute("SELECT * FROM feedback ORDER BY timestamp DESC")
        feedback_data = cursor.fetchall()
        
        if not feedback_data:
            return jsonify({'error': 'No feedback data available'})
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(feedback_data)
        
        # 1. Satisfaction Rate Analysis
        satisfaction_stats = calculate_satisfaction_rate(df)
        
        # 2. Feedback Distribution
        feedback_distribution = calculate_feedback_distribution(df)
        
        # 3. Topic Modeling
        topic_analysis = perform_topic_modeling(df)
        
        # 4. Knowledge Gaps Analysis
        knowledge_gaps = identify_knowledge_gaps(df)
        
        # 5. FAQ Generation
        faq_suggestions = generate_faq_suggestions(df)
        
        # 6. Temporal Analysis
        temporal_analysis = analyze_temporal_patterns(df)
        
        analytics_data = {
            'satisfaction_rate': satisfaction_stats,
            'feedback_distribution': feedback_distribution,
            'topic_modeling': topic_analysis,
            'knowledge_gaps': knowledge_gaps,
            'faq_suggestions': faq_suggestions,
            'temporal_analysis': temporal_analysis,
            'total_responses': len(df)
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_satisfaction_rate(df):
    """Calculate satisfaction metrics - Fixed JSON serialization"""
    total_feedback = len(df)
    positive_feedback = len(df[df['feedback'] == 1])
    negative_feedback = len(df[df['feedback'] == 0])
    
    satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0
    
    # Calculate trends over time
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_satisfaction = df.groupby('date').agg({
        'feedback': ['mean', 'count']
    }).reset_index()
    
    # Flatten column names
    daily_satisfaction.columns = ['date', 'mean_feedback', 'count_feedback']
    daily_satisfaction['satisfaction_rate'] = daily_satisfaction['mean_feedback'] * 100
    
    # Convert to list for JSON serialization
    trend_data = []
    for _, row in daily_satisfaction.iterrows():
        trend_data.append({
            'date': row['date'].strftime('%Y-%m-%d'),
            'satisfaction_rate': round(float(row['satisfaction_rate']), 2), 
            'total_responses': int(row['count_feedback'])
        })
    
    return {
        'overall_satisfaction': round(float(satisfaction_rate), 2),
        'positive_count': int(positive_feedback),
        'negative_count': int(negative_feedback),
        'total_count': int(total_feedback),
        'trend_data': trend_data
    }

def calculate_feedback_distribution(df):
    """Calculate feedback distribution metrics"""
    feedback_counts = df['feedback'].value_counts().to_dict()
    
    # Hour-wise distribution
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    hourly_dist = df.groupby('hour').size().to_dict()
    
    # Day-wise distribution
    df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.day_name()
    daily_dist = df.groupby('day_of_week').size().to_dict()
    
    return {
        'feedback_counts': {str(k): int(v) for k, v in feedback_counts.items()},  # Add int() conversion
        'hourly_distribution': {str(k): int(v) for k, v in hourly_dist.items()},  # Add int() conversion
        'daily_distribution': {str(k): int(v) for k, v in daily_dist.items()}  # Add int() conversion
    }

def perform_topic_modeling(df):
    """Perform topic modeling on questions"""
    questions = df['question_text'].tolist()
    
    # Clean and preprocess text
    cleaned_questions = [clean_text(q) for q in questions]
    
    # Remove empty questions
    cleaned_questions = [q for q in cleaned_questions if q.strip()]
    
    if len(cleaned_questions) < 2:
        return {'topics': [], 'question_topics': []}
    
    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(
        max_features=100,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=1
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(cleaned_questions)
        
        # Determine optimal number of topics (max 5 for clarity)
        n_topics = min(5, max(2, len(set(cleaned_questions)) // 3))
        
        # LDA Topic Modeling
        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            max_iter=100
        )
        lda.fit(tfidf_matrix)
        
        # Extract topics
        feature_names = vectorizer.get_feature_names_out()
        topics = []
        
        for topic_idx, topic in enumerate(lda.components_):
            top_words_idx = topic.argsort()[-10:][::-1]
            top_words = [feature_names[i] for i in top_words_idx]
            topic_name = generate_topic_name(top_words)
            
            topics.append({
            'id': int(topic_idx),  # Add int() conversion
            'name': str(topic_name),  # Add str() conversion
            'words': [str(word) for word in top_words[:5]],  # Add str() conversion
            'weight': float(topic.sum())
            })
        
        # Assign topics to questions
        topic_assignments = lda.transform(tfidf_matrix)
        question_topics = []
        
        for i, (question, topic_dist) in enumerate(zip(questions, topic_assignments)):
            main_topic = topic_dist.argmax()
            confidence = float(topic_dist[main_topic])
            
            question_topics.append({
            'question': str(question),  # Add str() conversion
            'topic_id': int(main_topic),
            'topic_name': str(topics[main_topic]['name']),  # Add str() conversion
            'confidence': float(confidence),
            'feedback': int(df.iloc[i]['feedback'])
        })
        
        return {
            'topics': topics,
            'question_topics': question_topics
        }
        
    except Exception as e:
        return {'topics': [], 'question_topics': [], 'error': str(e)}

def identify_knowledge_gaps(df):
    """Identify areas where the chatbot performs poorly"""
    # Questions with negative feedback
    negative_feedback = df[df['feedback'] == 0]
    
    if len(negative_feedback) == 0:
        return {'poor_performance_areas': [], 'common_failure_patterns': []}
    
    # Analyze common patterns in failed questions
    negative_questions = negative_feedback['question_text'].tolist()
    
    # Extract keywords from negative feedback
    all_negative_text = ' '.join(negative_questions)
    keywords = extract_keywords(all_negative_text)
    
    # Group similar failing questions
    failure_patterns = []
    
    # Common question types that fail
    question_types = categorize_questions(negative_questions)
    
    for q_type, questions in question_types.items():
        if len(questions) > 1:  # Only include patterns with multiple instances
            failure_patterns.append({
                'pattern': q_type,
                'count': len(questions),
                'examples': questions[:3],  # Show first 3 examples
                'percentage': round(len(questions) / len(negative_feedback) * 100, 2)
            })
    
    return {
        'poor_performance_areas': keywords[:10],
        'common_failure_patterns': failure_patterns,
        'total_negative_feedback': len(negative_feedback)
    }

def generate_faq_suggestions(df):
    """Generate FAQ suggestions based on common questions"""
    # Get most common questions
    question_counts = df['question_text'].value_counts()
    
    # Get questions with high positive feedback
    positive_questions = df[df['feedback'] == 1]['question_text'].value_counts()
    
    # Combine and analyze
    faq_candidates = []
    
    # Most frequently asked questions
    for question, count in question_counts.head(10).items():
        feedback_for_question = df[df['question_text'] == question]['feedback']
        avg_feedback = feedback_for_question.mean() if len(feedback_for_question) > 0 else 0
        
        faq_candidates.append({
            'question': question,
            'frequency': int(count),
            'avg_feedback': round(avg_feedback, 2),
            'category': categorize_single_question(question),
            'priority': calculate_faq_priority(count, avg_feedback)
        })
    
    # Sort by priority
    faq_candidates.sort(key=lambda x: x['priority'], reverse=True)
    
    return {
        'suggested_faqs': faq_candidates[:15],
        'categories': get_question_categories(df)
    }

def analyze_temporal_patterns(df):
    """Analyze temporal patterns in feedback - Fixed JSON serialization"""
    df['datetime'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['datetime'].dt.date
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.day_name()
    
    # Weekly patterns - Fixed to return JSON-serializable dict
    weekly_stats = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        day_data = df[df['day_of_week'] == day]
        if len(day_data) > 0:
            weekly_stats[day] = {
                'count': int(day_data['feedback'].count()),
                'mean_satisfaction': float(day_data['feedback'].mean())
            }
        else:
            weekly_stats[day] = {'count': 0, 'mean_satisfaction': 0.0}
    
    # Hourly patterns - Fixed to return JSON-serializable dict
    hourly_stats = {}
    for hour in range(24):
        hour_data = df[df['hour'] == hour]
        if len(hour_data) > 0:
            hourly_stats[str(hour)] = {
                'count': int(hour_data['feedback'].count()),
                'mean_satisfaction': float(hour_data['feedback'].mean())
            }
        else:
            hourly_stats[str(hour)] = {'count': 0, 'mean_satisfaction': 0.0}
    
    # Recent trends (last 7 days)
    recent_date = df['datetime'].max() - timedelta(days=7)
    recent_data = df[df['datetime'] >= recent_date]
    
    return {
        'weekly_patterns': weekly_stats,
        'hourly_patterns': hourly_stats,
        'recent_trend': {
            'total_questions': int(len(recent_data)),
            'satisfaction_rate': float(recent_data['feedback'].mean() * 100) if len(recent_data) > 0 else 0.0
        }
    }

# Helper functions
def clean_text(text):
    """Clean and preprocess text"""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_keywords(text):
    """Extract keywords using TF-IDF"""
    try:
        vectorizer = TfidfVectorizer(
            max_features=20,
            stop_words='english',
            ngram_range=(1, 2)
        )
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        keyword_scores = list(zip(feature_names, scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [kw[0] for kw in keyword_scores if kw[1] > 0]
    except:
        return []

def categorize_questions(questions):
    """Categorize questions into types"""
    categories = {
        'admission': [],
        'fees': [],
        'courses': [],
        'facilities': [],
        'contact': [],
        'general': []
    }
    
    keywords_map = {
        'admission': ['admission', 'apply', 'eligibility', 'entrance', 'requirement'],
        'fees': ['fee', 'cost', 'payment', 'scholarship', 'finance'],
        'courses': ['course', 'program', 'curriculum', 'syllabus', 'subject'],
        'facilities': ['facility', 'hostel', 'library', 'lab', 'infrastructure'],
        'contact': ['contact', 'phone', 'email', 'address', 'location']
    }
    
    for question in questions:
        question_lower = question.lower()
        categorized = False
        
        for category, keywords in keywords_map.items():
            if any(keyword in question_lower for keyword in keywords):
                categories[category].append(question)
                categorized = True
                break
        
        if not categorized:
            categories['general'].append(question)
    
    return {k: v for k, v in categories.items() if v}

def categorize_single_question(question):
    """Categorize a single question"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['admission', 'apply', 'eligibility']):
        return 'Admission'
    elif any(word in question_lower for word in ['fee', 'cost', 'payment']):
        return 'Fees'
    elif any(word in question_lower for word in ['course', 'program', 'curriculum']):
        return 'Courses'
    elif any(word in question_lower for word in ['facility', 'hostel', 'library']):
        return 'Facilities'
    elif any(word in question_lower for word in ['contact', 'phone', 'email']):
        return 'Contact'
    else:
        return 'General'

def generate_topic_name(top_words):
    """Generate a meaningful topic name from top words"""
    # Simple heuristic to generate topic names
    first_word = top_words[0] if top_words else "Topic"
    return f"{first_word.title()} Related"

def calculate_faq_priority(frequency, avg_feedback):
    """Calculate priority score for FAQ suggestions"""
    return frequency * (1 + avg_feedback)

def get_question_categories(df):
    """Get distribution of question categories"""
    categories = {}
    for question in df['question_text']:
        category = categorize_single_question(question)
        categories[category] = categories.get(category, 0) + 1
    return categories

if __name__ == '__main__':
    port = 4000
    app.run(host="0.0.0.0", port=port)

