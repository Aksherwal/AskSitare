from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from groq import Groq
from sentence_transformers import SentenceTransformer
import os
model = SentenceTransformer('all-MiniLM-L6-v2')

api=os.getenv("api_key")
# Initialize the Groq client with your API key
# client = Groq(api_key="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")
client = Groq(api_key=api)
# queary=""" From the text given above, write a brief anaswer of this question(if it can be answered) in a formal language but do not mension that you are giving the answer from any text and also give the link if any(otherwise dont mention about the link) in the text only in clickable fromat at the last of answer to know more, if the question is irrelevent, show appropriate message, the question is: """
queary=""" From this text, answer briefly the question given next (if the text contains the answer) without mentioning the text,
if text has link, give the link in the end of answer only in clickable format,
if the question is irrelevant, show appropriate message,
the question is: """
# Function to generate embedding for user question
def generate_embedding(question):
    return model.encode(question).tolist()

# Database connection parameters
DB_PARAMS = {
    "dbname": "suchatbot",
    "user": "postgres",
    "password": "aks@sitare",
    "host": "localhost",
    "port": 5432
}
# Connect to the database
conn = psycopg2.connect(**DB_PARAMS)
cursor = conn.cursor(cursor_factory=RealDictCursor)

def get_top_similar_questions(user_question, top_n=5):
    # Step 1: Generate embedding for the user question
    user_embedding = generate_embedding(user_question)

    # Step 2: Query to calculate similarity and retrieve top N questions
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

    # Step 3: Retrieve paragraphs for the corresponding topic_ids
    topic_ids = tuple(q['topic_id'] for q in top_questions)
    paragraphs_query = """
    SELECT topic_id, paragraph
    FROM topics
    WHERE topic_id IN %s;
    """
    cursor.execute(paragraphs_query, (topic_ids,))
    paragraphs = cursor.fetchall()

    # Step 4: Map topic_id to paragraphs for display
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
        model="llama-3.1-70b-versatile",  # Specify the model
        messages=[
            {"role": "system", "content": "You are a University chatbot assistent specialized in English language"},
            {"role": "user", "content": sourcetext+queary+user_message}
            ],
            temperature=1,       # Controls creativity (higher = more creative)
            max_tokens=1024,     # Limit on response length
            top_p=1,             # Sampling parameter for diverse outputs
            stream=True,         # Enables streaming
            stop=None            # No stop sequence
        )
    # Process and print the streamed response
    response_message=""
    for chunk in completion:
        response_message+=chunk.choices[0].delta.content or ""
    # response_message = f"You said: {user_message}"  # Replace with your processing logic
    
    return jsonify({'response': response_message})

@app.route('/feedback', methods=['POST'])
def record_feedback():
    data = request.json
    question_text = data.get('question_text')
    feedback = data.get('feedback')  # 1 for like, 0 for dislike

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
    app.run(debug=True)
