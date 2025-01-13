from flask import Flask, render_template, request, jsonify, session
import os
import re
from openai import AzureOpenAI # type: ignore
from prompt_engineering import PromptEngineering

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Add more detailed conversation states
CONVERSATION_STATES = {
    'INITIAL': 0,
    'TOPIC_REQUESTED': 1,
    'GRADE_REQUESTED': 2,
    'LESSONS_GENERATED': 3,
    'LESSON_IN_PROGRESS': 4,
    'LESSON_COMPLETING': 5,
    'QUESTION_ASKED': 6,
    'ANSWER_RECEIVED': 7
}

endpoint = os.getenv("https://azureopened.openai.azure.com/", "https://azureopened.openai.azure.com/")  
deployment = os.getenv("azureopened", "gpt-35-turbo")  
subscription_key = os.getenv("0eb926c2cc344a3587daf5f024deebd4", "0eb926c2cc344a3587daf5f024deebd4")  

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2024-05-01-preview",
)

# Initialize prompt engineering
prompt_engine = PromptEngineering()

@app.route("/")
def home():
    initial_message = "I'm your educational assistant. I'll help guide you through problems rather than giving direct answers. This helps you learn better! Ask me anything."
    return render_template("index.html", system_message=initial_message)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    answer_option = request.json.get("answer_option")  # New field for multiple choice answers
    lesson_data = None
    
    if 'state' not in session:
        session['state'] = CONVERSATION_STATES['INITIAL']
        session['current_topic'] = None
        session['current_lesson_index'] = 0
        session['lessons'] = []
        session['completed_lessons'] = set()
    
    if session['state'] == CONVERSATION_STATES['INITIAL'] and re.match(r'^(hi|hello|hey|let\'s start|start|begin)', user_message.lower()):
        session.clear()
        session['state'] = CONVERSATION_STATES['INITIAL']
        prompt_engine.clear_conversation()
    
    prompt_engine.add_message("user", user_message)
    
    # Handle answer option if provided
    if answer_option and session.get('current_question'):
        current_question = session['current_question']
        is_correct = prompt_engine.validate_answer(current_question, answer_option)
        ai_response = prompt_engine.generate_question_feedback(is_correct, current_question)
        session['current_question'] = None  # Clear the current question
        session['state'] = CONVERSATION_STATES['LESSON_IN_PROGRESS']
        
        prompt_engine.add_message("user", f"Selected option {answer_option}")
        prompt_engine.add_message("assistant", ai_response)
        
        return jsonify({
            "response": ai_response,
            "role": "assistant",
            "state": session['state']
        })

    completion = client.chat.completions.create(
        model=deployment,
        messages=prompt_engine.get_conversation_history(),
        max_tokens=500,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )
    
    ai_response = completion.choices[0].message.content
    
    # State machine logic
    if session['state'] == CONVERSATION_STATES['INITIAL'] and "what topic" in ai_response.lower():
        session['state'] = CONVERSATION_STATES['TOPIC_REQUESTED']
    
    elif session['state'] == CONVERSATION_STATES['TOPIC_REQUESTED'] and "what grade" in ai_response.lower():
        session['state'] = CONVERSATION_STATES['GRADE_REQUESTED']
    
    elif session['state'] == CONVERSATION_STATES['GRADE_REQUESTED'] and "topic details:" in ai_response.lower():
        if not session.get('current_topic'):
            lesson_data = prompt_engine.parse_lesson_data(ai_response)
            if lesson_data:
                session['current_topic'] = lesson_data['topic']
                session['lessons'] = lesson_data['lessons']
                session['current_lesson_index'] = 0
                session['state'] = CONVERSATION_STATES['LESSONS_GENERATED']
                ai_response = f"Shall we begin learning about {session['lessons'][0]}? Say 'yes' when you're ready."
    
    elif session['state'] == CONVERSATION_STATES['LESSONS_GENERATED']:
        if user_message.lower() in ['yes', "sure, let's proceed.", "let's proceed to the next chapter..."]:
            session['state'] = CONVERSATION_STATES['LESSON_IN_PROGRESS']
    
    elif session['state'] == CONVERSATION_STATES['LESSON_IN_PROGRESS']:
        prev_message = prompt_engine.get_conversation_history()[-2]['content'] if len(prompt_engine.get_conversation_history()) > 1 else ""
        if "what is" in prev_message.lower() and any(op in prev_message for op in ['+', '-', '*']):
            if not prompt_engine.validate_math_answer(prev_message, user_message):
                ai_response = "That's not correct. Let's try again. " + prev_message
                prompt_engine.add_message("assistant", ai_response)
                return jsonify({
                    "response": ai_response,
                    "role": "assistant",
                    "state": session['state']
                })

        if "great job on completing" in ai_response.lower():
            current_lesson = session['lessons'][session['current_lesson_index']]
            session['completed_lessons'].add(current_lesson)
            
            session['current_lesson_index'] += 1
            if session['current_lesson_index'] < len(session['lessons']):
                next_lesson = session['lessons'][session['current_lesson_index']]
                ai_response = prompt_engine.generate_lesson_progress_message(current_lesson, next_lesson)
                session['state'] = CONVERSATION_STATES['LESSONS_GENERATED']
            else:
                ai_response = prompt_engine.generate_completion_message(session['current_topic'])
                session['state'] = CONVERSATION_STATES['INITIAL']
        else:
            current_topic = session['current_topic']
            current_lesson = session['lessons'][session['current_lesson_index']]
            
            # Generate question
            question_prompt = prompt_engine.generate_question_prompt(current_topic, current_lesson)
            question_completion = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": question_prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            question_response = question_completion.choices[0].message.content
            question_data = prompt_engine.parse_question_response(question_response)
            
            if question_data:
                session['current_question'] = question_data
                session['state'] = CONVERSATION_STATES['QUESTION_ASKED']
                
                return jsonify({
                    "response": ai_response,
                    "question": question_data,
                    "role": "assistant",
                    "state": session['state']
                })
    
    prompt_engine.add_message("assistant", ai_response)
    
    response_data = {
        "response": ai_response,
        "role": "assistant",
        "state": session['state'],
        "lesson_progress": {
            "current_topic": session.get('current_topic'),
            "completed_lessons": list(session.get('completed_lessons', set())),
            "total_lessons": len(session.get('lessons', []))
        }
    }
    
    # Add current question if it exists
    if session.get('current_question'):
        response_data["question"] = session['current_question']
    
    return jsonify(response_data)

if __name__ == "__main__":
    app.run(debug=True)