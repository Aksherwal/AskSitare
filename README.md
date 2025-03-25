# AskSitare

AskSitare is an intelligent chatbot web application designed specifically for Sitare University. It uses natural language processing and semantic search to provide accurate responses to university-related queries.

## Features

- Real-time chat interface for student queries
- Semantic search using sentence transformers
- Integration with Groq's LLaMA 3.3 70B model for generating responses
- Feedback system for response quality tracking
- Admin dashboard for monitoring feedback
- PostgreSQL database for storing questions and feedback
- Vector similarity search for finding relevant responses

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with psycopg2
- **AI/ML**:
  - Groq API for LLM integration
  - Sentence Transformers for text embeddings
  - LLaMA 3.3 70B model for response generation
- **Frontend**: HTML/Templates

## Live Link:
👉[click here ](https://asksitare.onrender.com/)
## Installation

1. Clone the repository
2. Install the required dependencies:
```bash
pip install flask psycopg2-binary groq sentence-transformers
```

3. Set up environment variables:
```bash
export GROQ_API_KEY="your_groq_api_key"
export PORT=5000  # Optional, defaults to 5000
```

4. Configure the database connection in the code by updating `DB_PARAMS`:
```python
DB_PARAMS = {
    "dbname": "your_db_name",
    "user": "your_db_user",
    "password": "your_db_password",
    "host": "your_db_host",
    "port": 5432
}
```

## Usage

1. Start the server:
```bash
python app.py
```

2. Access the chatbot interface at `http://localhost:5000`

3. For admin access:
   - Navigate to `/login`
   - Use the admin credentials to access the dashboard
   - View user feedback and interaction data

## Features in Detail

### Semantic Search
- Uses sentence transformers to convert questions into embeddings
- Performs vector similarity search to find relevant matches
- Returns top 5 most similar questions and their associated answers

### Chat Interface
- Real-time response generation
- Streaming responses for better user experience
- Feedback system for users to rate responses

### Admin Dashboard
- Secure login system
- View and analyze user feedback
- Monitor chatbot performance

### Database Schema

The application uses the following main tables:
- `questions`: Stores questions and their embeddings
- `topics`: Stores detailed answers/paragraphs
- `feedback`: Stores user feedback on responses

## ML Analysis
Click here to see the ML analysis of the datasets we have👉 @ [ML Analysis](https://github.com/deepalitomar021/ML_Analysis_SU_Chatbot)

## Security
- Secure admin login system
- Environment variable based configuration
- Database connection security
- Session management for admin access

## Contributing

Please follow these steps to contribute:
1. Fork the repository
2. Create a new branch for your feature
3. Submit a pull request with a clear description of your changes

