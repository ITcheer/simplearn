from typing import Dict, List, Optional
import re
from logger import log_event

class PromptEngineering:
    def __init__(self):
        self.system_prompt = self._create_system_prompt()
        self.conversation_history: List[Dict[str, str]] = []
        
    def _create_system_prompt(self) -> List[Dict[str, str]]:
        return [{
            "role": "system",
            "content": [{
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
            }]
        }]

    def get_system_prompt(self) -> List[Dict[str, str]]:
        return self.system_prompt

    def add_message(self, role: str, content: str) -> None:
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def clear_conversation(self) -> None:
        self.conversation_history.clear()
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.system_prompt + self.conversation_history

    def parse_lesson_data(self, response: str) -> Optional[Dict[str, any]]:
        try:
            # Extract topic details
            topic_match = re.search(r'Topic Details:\s*([^\n]+)', response, re.IGNORECASE)
            topic = topic_match.group(1).strip() if topic_match else "Unknown Topic"
            
            # Extract lessons
            lessons = []
            lessons_section = re.search(r'Lessons:(.*?)(?=\n\n|$)', response, re.DOTALL | re.IGNORECASE)
            if lessons_section:
                lesson_matches = re.findall(r'-\s*([^\n]+)', lessons_section.group(1))
                lessons = [lesson.strip() for lesson in lesson_matches]
            
            log_event(f"Parsed topic: {topic}")
            log_event(f"Parsed lessons: {lessons}")
            
            return {
                "topic": topic,
                "lessons": lessons
            }
        except Exception as e:
            log_event(f"Error parsing lesson data: {e}", level='error')
            return None

    def validate_math_answer(self, question: str, user_answer: str) -> bool:
        try:
            numbers = re.findall(r'\d+', question)
            operator = re.findall(r'[\+\-\*\/]', question)
            
            if len(numbers) == 2 and operator:
                num1, num2 = map(int, numbers)
                expected = None
                
                if '+' in operator:
                    expected = num1 + num2
                elif '-' in operator:
                    expected = num1 - num2
                elif '*' in operator:
                    expected = num1 * num2
                    
                return int(user_answer) == expected
        except:
            return False
        return False

    def generate_lesson_progress_message(self, current_lesson: str, next_lesson: Optional[str] = None) -> str:
        if next_lesson:
            return f"Great job on completing {current_lesson}! Ready to start {next_lesson}? Say 'yes' when ready."
        return f"Great job on completing {current_lesson}!"

    def generate_completion_message(self, topic: str) -> str:
        return f"Congratulations! You've completed all lessons on {topic}! Would you like to start a new topic?"

    def generate_question_prompt(self, topic: str, lesson: str) -> str:
        return f"""Generate a multiple choice question about {topic}, specifically about {lesson}.
        Format the response exactly like this:
        {{
            "question": "your question here",
            "options": {{
                "A": "first option",
                "B": "second option",
                "C": "third option",
                "D": "fourth option"
            }},
            "correct": "A"
        }}
        Make sure the question is appropriate for the topic and lesson."""

    def parse_question_response(self, response: str) -> Optional[Dict]:
        try:
            # Extract the JSON structure from the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                question_data = json.loads(json_match.group(0))
                return question_data
            return None
        except Exception as e:
            log_event(f"Error parsing question response: {e}", level='error')
            return None

    def validate_answer(self, question_data: Dict, user_answer: str) -> bool:
        return question_data.get('correct', '').upper() == user_answer.upper()

    def generate_question_feedback(self, is_correct: bool, question_data: Dict) -> str:
        if is_correct:
            return "Correct! Great job! Let's continue with the lesson."
        correct_answer = question_data['options'][question_data['correct']]
        return f"That's not quite right. The correct answer was {question_data['correct']}: {correct_answer}. Let's continue learning!"
