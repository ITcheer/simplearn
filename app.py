from flask import Flask, render_template, request, jsonify, session
import os
import base64
import re
from openai import AzureOpenAI # type: ignore

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Add this for session management

# Add more detailed conversation states
CONVERSATION_STATES = {
    'INITIAL': 0,
    'TOPIC_REQUESTED': 1,
    'GRADE_REQUESTED': 2,
    'LESSONS_GENERATED': 3,
    'LESSON_IN_PROGRESS': 4,
    'LESSON_COMPLETING': 5
}

endpoint = os.getenv("https://azureopened.openai.azure.com/", "https://azureopened.openai.azure.com/")  
deployment = os.getenv("azureopened", "gpt-35-turbo")  
subscription_key = os.getenv("0eb926c2cc344a3587daf5f024deebd4", "0eb926c2cc344a3587daf5f024deebd4")  

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)

# System prompt for the AI
chat_prompt = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": """You are an intelligent and helpful educational assistant. Follow these steps strictly:

1. When user greets with any greeting (like hi, hello, hey, etc.), ask ONLY: "What topic would you like to learn about today?"
   Wait for topic response.

2. After receiving topic, ask ONLY: "What grade are you in?"
   Wait for grade response.

3. After receiving both topic and grade, ONCE generate the lesson structure EXACTLY in this format:
   Topic Details: [topic_name]
   Lessons:
   - [Lesson 1]
   - [Lesson 2]
   - [Lesson 3]

   Then immediately ask: "Shall we begin learning about [Lesson 1]?"

4. For each lesson:
   - Wait for user's confirmation
   - Provide a brief introduction
   - Ask a simple question to check understanding
   - Wait for user's response
   - If response shows understanding, say exactly: "Great job on completing [Current Lesson]!"
   - Then ask: "Ready to start [Next Lesson]?"

Remember: Format the topic and lessons structure EXACTLY as shown above."""
            }
        ]
    }
]

def parse_lesson_data(response):
    try:
        # Extract topic details
        topic_match = re.search(r'topic_details:\s*([^\n]+)', response)
        topic = topic_match.group(1).strip() if topic_match else "Unknown Topic"
        
        # Extract lessons using a more flexible pattern
        # This will match both "- Lesson X: Text" and "- Text" formats
        lessons = []
        # Find the lessons section
        lessons_section = re.search(r'lessons:(.*?)(?=\n\n|$)', response, re.DOTALL)
        if lessons_section:
            # Extract all bullet points after "lessons:"
            lesson_matches = re.findall(r'-\s*(?:Lesson \d+:)?\s*([^\n]+)', lessons_section.group(1))
            lessons = [lesson.strip() for lesson in lesson_matches]
        
        print("Parsed topic:", topic)  # Debug print
        print("Parsed lessons:", lessons)  # Debug print
        
        return {
            "topic": topic,
            "lessons": lessons
        }
    except Exception as e:
        print(f"Error parsing lesson data: {e}")
        return None

@app.route("/")
def home():
    # Send initial system message to frontend
    initial_message = "I'm your educational assistant. I'll help guide you through problems rather than giving direct answers. This helps you learn better! Ask me anything."
    return render_template("index.html", system_message=initial_message)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    lesson_data = None
    
    # Initialize or get session data
    if 'state' not in session:
        session['state'] = CONVERSATION_STATES['INITIAL']
        session['current_topic'] = None
        session['current_lesson_index'] = 0
        session['lessons'] = []
        session['completed_lessons'] = set()
    
    # Reset for new conversation
    if session['state'] == CONVERSATION_STATES['INITIAL'] and re.match(r'^(hi|hello|hey|let\'s start|start|begin)', user_message.lower()):
        session.clear()
        session['state'] = CONVERSATION_STATES['INITIAL']
        chat_prompt.clear()
        chat_prompt.append({"role": "system", "content": chat_prompt[0]["content"]})
    
    chat_prompt.append({"role": "user", "content": user_message})
    
    # Generate AI response
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_tokens=500,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )
    
    ai_response = completion.choices[0].message.content
    role_returned = completion.choices[0].message.role
    
    # State machine logic
    if session['state'] == CONVERSATION_STATES['INITIAL'] and "what topic" in ai_response.lower():
        session['state'] = CONVERSATION_STATES['TOPIC_REQUESTED']
    
    elif session['state'] == CONVERSATION_STATES['TOPIC_REQUESTED'] and "what grade" in ai_response.lower():
        session['state'] = CONVERSATION_STATES['GRADE_REQUESTED']
    
    elif session['state'] == CONVERSATION_STATES['GRADE_REQUESTED'] and "topic_details:" in ai_response:
        if not session.get('current_topic'):  # Only parse if not already done
            lesson_data = parse_lesson_data(ai_response)
            if lesson_data:
                session['current_topic'] = lesson_data['topic']
                session['lessons'] = lesson_data['lessons']
                session['current_lesson_index'] = 0
                session['state'] = CONVERSATION_STATES['LESSONS_GENERATED']
                # Modify response to immediately ask about first lesson
                ai_response = f"Shall we begin learning about {session['lessons'][0]}? Say 'yes' when you're ready."
    
    elif session['state'] == CONVERSATION_STATES['LESSONS_GENERATED']:
        if user_message.lower() == 'yes':
            session['state'] = CONVERSATION_STATES['LESSON_IN_PROGRESS']
    
    elif session['state'] == CONVERSATION_STATES['LESSON_IN_PROGRESS']:
        if "great job on completing" in ai_response.lower():
            current_lesson = session['lessons'][session['current_lesson_index']]
            session['completed_lessons'].add(current_lesson)
            
            # Move to next lesson
            session['current_lesson_index'] += 1
            if session['current_lesson_index'] < len(session['lessons']):
                next_lesson = session['lessons'][session['current_lesson_index']]
                ai_response = f"Great job on completing {current_lesson}! Ready to start {next_lesson}? Say 'yes' when ready."
                session['state'] = CONVERSATION_STATES['LESSONS_GENERATED']
            else:
                ai_response = f"Congratulations! You've completed all lessons on {session['current_topic']}! Would you like to start a new topic?"
                session['state'] = CONVERSATION_STATES['INITIAL']
    
    chat_prompt.append({"role": "assistant", "content": ai_response})
    
    return jsonify({
        "response": ai_response,
        "role": "assistant",
        "state": session['state'],
        "lesson_progress": {
            "current_topic": session.get('current_topic'),
            "completed_lessons": list(session.get('completed_lessons', set())),
            "total_lessons": len(session.get('lessons', []))
        }
    })

#okay new head
if __name__ == "__main__":
    app.run(debug=True)