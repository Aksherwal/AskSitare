from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from groq import Groq
from sentence_transformers import SentenceTransformer
import os
model = SentenceTransformer('all-MiniLM-L6-v2')

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# queary=""" From the text given above, write a vey brief and precise anaswer of this question(if it can be answered from the text) in a formal language but do not mension that you are giving the answer from any text and also give the link if any(otherwise dont mention about the link) in the text only in clickable fromat at the last of answer to know more, if the question is irrelevent, show appropriate message, the question is: """
queary=""" From this text, answer shortly the question given next (if the text contains the answer) without mentioning the text,
if text has link, give the link in the end of answer only in clickable format otherwise don't mension about the link that it is present or not,
if the question is irrelevant, show appropriate message,
the question is: """
# Function to generate embedding for user question
def generate_embedding(question):
    return model.encode(question).tolist()

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

if __name__ == '__main__':
    # app.run(debug=True)
    # port = int(os.environ.get("PORT", 4000))  # Default to 5000 if PORT is not set
    port = 4000
    app.run(host="0.0.0.0", port=port)

# from flask import Flask, render_template, request, redirect, url_for, session, jsonify
# import psycopg2
# from psycopg2.extras import RealDictCursor
# from groq import Groq
# from sentence_transformers import SentenceTransformer
# import os
# import logging

# # Initialize logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# # Initialize SentenceTransformer model
# model = SentenceTransformer('all-MiniLM-L6-v2')

# # Initialize the Groq client with API key from environment variables
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# # Prompt template
# QUERY_TEMPLATE = """
# From this text, answer shortly the question given next (if the text contains the answer) without mentioning the text.
# If the text has a link, give the link in the end of the answer only in clickable format; otherwise, do not mention the link.
# If the question is irrelevant, show an appropriate message.
# The question is: """

# # Database connection parameters
# DB_PARAMS = {
#     "dbname": "suchatbot",
#     "user": "avnadmin",
#     "password": os.getenv("DB_PASSWORD"),
#     "host": os.getenv("DB_HOST"),
#     "port": 13189
# }

# # Flask app initialization
# app = Flask(__name__)
# app.secret_key = os.getenv("SECRET_KEY", 'su-sitare-chatbot')

# # Generate embedding for a user question
# def generate_embedding(question):
#     return model.encode(question).tolist()

# # Retrieve top similar questions and corresponding paragraphs
# def get_top_similar_questions(user_question, top_n=5):
#     user_embedding = generate_embedding(user_question)
#     try:
#         conn = psycopg2.connect(**DB_PARAMS)
#         cursor = conn.cursor(cursor_factory=RealDictCursor)

#         # Query for top similar questions
#         query = """
#             SELECT sr_no, topic_id, question, 1 - (embedding <=> %s::VECTOR) AS similarity
#             FROM questions
#             ORDER BY similarity DESC
#             LIMIT %s;
#         """
#         cursor.execute(query, (user_embedding, top_n))
#         top_questions = cursor.fetchall()

#         # Retrieve paragraphs for the corresponding topic_ids
#         topic_ids = tuple(q['topic_id'] for q in top_questions)
#         paragraphs_query = """
#             SELECT topic_id, paragraph
#             FROM topics
#             WHERE topic_id IN %s;
#         """
#         cursor.execute(paragraphs_query, (topic_ids,))
#         paragraphs = cursor.fetchall()

#         paragraphs_dict = {p['topic_id']: p['paragraph'] for p in paragraphs}

#         result = [
#             {
#                 "sr_no": question["sr_no"],
#                 "question": question["question"],
#                 "similarity": question["similarity"],
#                 "paragraph": paragraphs_dict.get(question["topic_id"], "No paragraph found")
#             }
#             for question in top_questions
#         ]

#         return result
#     except Exception as e:
#         logging.error(f"Error retrieving similar questions: {e}")
#         return []
#     finally:
#         conn.close()

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/chat', methods=['POST'])
# def chat():
#     user_message = request.json.get('message')
#     if not user_message:
#         return jsonify({'error': 'No message provided'}), 400

#     # Retrieve top similar questions and paragraphs
#     top_results = get_top_similar_questions(user_message)
#     sourcetext = " ".join(set(r['paragraph'] for r in top_results))

#     try:
#         # Generate completion using Groq API
#         completion = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {"role": "system", "content": "You are a University chatbot assistant specialized in English language."},
#                 {"role": "user", "content": sourcetext + QUERY_TEMPLATE + user_message}
#             ],
#             temperature=1,
#             max_tokens=1024,
#             top_p=1,
#             stream=True
#         )

#         response_message = ""
#         for chunk in completion:
#             response_message += chunk.choices[0].delta.content or ""

#         return jsonify({'response': response_message})
#     except Exception as e:
#         logging.error(f"Error during Groq API call: {e}")
#         return jsonify({'error': 'Failed to process request'}), 500

# @app.route('/feedback', methods=['POST'])
# def record_feedback():
#     data = request.json
#     question_text = data.get('question_text')
#     feedback = data.get('feedback')

#     if not question_text or feedback not in [0, 1]:
#         return jsonify({'error': 'Invalid data'}), 400

#     try:
#         conn = psycopg2.connect(**DB_PARAMS)
#         cursor = conn.cursor()

#         cursor.execute(
#             """
#             INSERT INTO feedback (question_text, feedback)
#             VALUES (%s, %s)
#             """,
#             (question_text, feedback)
#         )
#         conn.commit()
#         return jsonify({'success': True})
#     except Exception as e:
#         conn.rollback()
#         logging.error(f"Error recording feedback: {e}")
#         return jsonify({'error': 'Failed to record feedback'}), 500
#     finally:
#         conn.close()

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error = None
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == "admin" and password == os.getenv("ADMIN_PASSWORD", "aks@sitare123"):
#             session['username'] = username
#             return redirect(url_for('admin'))
#         else:
#             error = 'Invalid username or password'
#     return render_template('login.html', error=error)

# @app.route('/logout')
# def logout():
#     session.pop('username', None)
#     return redirect(url_for('login'))

# @app.route('/admin')
# def admin():
#     try:
#         conn = psycopg2.connect(**DB_PARAMS)
#         cursor = conn.cursor(cursor_factory=RealDictCursor)
#         cursor.execute("SELECT * FROM feedback")
#         data = cursor.fetchall()
#         return render_template('admin.html', data=data)
#     except Exception as e:
#         logging.error(f"Error fetching feedback: {e}")
#         return "Error fetching feedback", 500
#     finally:
#         conn.close()

# if __name__ == '__main__':
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)
