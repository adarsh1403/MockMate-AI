import os
import json
import logging
from openai import OpenAI

# Configure logger for this module
logger = logging.getLogger(__name__)

# Get API key from environment variable
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# Model to use for AI-powered features
MODEL = "openai/gpt-oss-120b"

# Generate questions for interview
def generate_questions(field, difficulty):

    prompt = f"""
Generate exactly 5 {field} interview questions for a {difficulty} level candidate.

Return ONLY valid JSON:

{{
  "questions": [
    "Question 1",
    "Question 2",
    "Question 3",
    "Question 4",
    "Question 5"
  ]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        questions = data.get("questions", [])
        
        if len(questions) != 5:
            raise ValueError("AI did not return 5 questions")
        
        return questions
    
    except Exception as e:
        logger.error(f"Error generating questions: {e}", exc_info=True)
        # Fallback questions in case of API failure
        return [
            f"What is {field} and why is it important?",
            f"Explain a key concept or technology in {field}.",
            f"Describe your experience or knowledge with {field}.",
            f"What are some common challenges in {field}?",
            f"How would you approach solving a problem in {field}?"
        ]

# Evaluate answers for interview
def evaluate_answers(qa_log):

    formatted = "\n".join(
        [f"Q: {q}\nA: {a}\n" for q, a in qa_log]
    )

    prompt = f"""
You are a strict technical interviewer.

Evaluate the candidate based ONLY on the answers below:

{formatted}

Return ONLY valid JSON:

{{
 "score": "x",
 "strengths": ["point1", "point2"],
 "weaknesses": ["point1", "point2"],
 "improvements": ["tip1", "tip2"],
 "hire_recommendation": "Yes or No"
}}

Score strictly from 0–10 using the FULL range.

9-10 → Expert-level, detailed, includes examples  
7-8 → Strong answer with clarity  
5-6 → Correct but lacks depth  
3-4 → Partial understanding  
0-2 → Incorrect or irrelevant

"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    except Exception as e:
        logger.error(f"Error evaluating answers: {e}", exc_info=True)
        # Fallback evaluation
        return {
            "score": "5",
            "strengths": ["Attempted all questions", "Showed effort and engagement"],
            "weaknesses": ["Evaluation temporarily unavailable due to technical error"],
            "improvements": ["Please try the interview again to get detailed feedback"],
            "hire_recommendation": "Pending - Retry recommended"
        }
