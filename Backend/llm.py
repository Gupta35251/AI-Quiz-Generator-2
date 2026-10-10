import os
from google import genai
from pathlib import Path
from dotenv import load_dotenv
from settings import User, Evaluation, Quiz
import time
from google.genai import errors

MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


load_dotenv(Path(__file__).resolve().parent / ".env")
# def get_client():
#     api_key = os.getenv("GEMINI_API_KEY")
#     if not api_key:
#         raise RuntimeError(
#             "GEMINI_API_KEY is not set. Set it as an environment variable before starting the backend."
#         )
#     return genai.Client(api_key=api_key)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from Backend/.env")

client = genai.Client(api_key=api_key)

def generate_answer(user: User):
    prompt = f"""
    Create exactly {user.no_of_questions} questions about: {user.content}
    Difficulty: {user.level}
    Return the topic name and questions.

    Include a balanced mix of these question types where suitable:
    mcq, multiple_answer, code, theory.
    Each question must include its correct answer, a clear explanation in description,
    and its difficulty. For mcq and multiple_answer, include options.
    For multiple_answer, clearly design questions that have more than one correct answer.
    Make questions accurate and appropriate for the requested difficulty.
    Each question must include a short "concept" (2-4 words, e.g. "Python loops").
    Reuse the exact same concept name for related questions.
    """
    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": Quiz,
                    },
                )
                return response.parsed
            except errors.ServerError as e:      # 503 / 500
                last_error = e
                time.sleep(2 ** attempt)         # wait 1s, 2s, 4s
    raise last_error
def evaluate_answer(question, user_answer):
    prompt = f"""
    Evaluate the learner's answer fairly. Accept equivalent correct wording or code when appropriate.
    Question: {question.question}
    Question type: {question.type}
    Expected answer: {question.answer}
    Learner's answer: {user_answer}

    Return whether it is correct and a helpful explanation.
    If incorrect, explain the underlying concept simply and show the correct answer.
    Do not mark a substantially correct answer wrong merely because of minor wording differences.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": Evaluation,
        },
    )
    return response.parsed


def evaluate_answer(question, user_answer):
    prompt = f"""
    Evaluate the learner's answer fairly. Accept equivalent correct wording or code when appropriate.
    Question: {question.question}
    Question type: {question.type}
    Expected answer: {question.answer}
    Learner's answer: {user_answer}

    Return whether it is correct and a helpful explanation.
    If incorrect, explain the underlying concept simply and show the correct answer.
    Do not mark a substantially correct answer wrong merely because of minor wording differences.
    """
    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": Evaluation,
                    },
                )
                return response.parsed
            except errors.ServerError as e:      # 503 / 500
                last_error = e
                time.sleep(2 ** attempt)         # wait 1s, 2s, 4s
    raise last_error

def check_answer(question, user_answer):
    expected = {answer.strip().casefold() for answer in question.answer}
    given = {answer.strip().casefold() for answer in user_answer}
    return bool(expected) and expected == given
