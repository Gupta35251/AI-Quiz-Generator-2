# import json
# import uuid
# from datetime import datetime
# from typing import Literal
# import re   
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field,EmailStr

# from settings import User, Quiz, QuizResult
# from llm import generate_answer, evaluate_answer, check_answer
# from database import (
#     save_quiz,
#     create_quiz_session,
#     get_quiz_session,
#     mark_quiz_session_submitted,
#     get_all_history,
#     get_history_by_id,
# )

# from auth import (
#     hash_password,
#     verify_password,
#     create_access_token,
# )

# from database import (
#     init_auth_db,
#     create_user,
#     find_user_by_email,
# )

# app = FastAPI(title="Quizwise API", version="1.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# class GenerateRequest(BaseModel):
#     content: str = Field(min_length=1, max_length=8000)
#     no_of_questions: int = Field(ge=1, le=30)
#     level: Literal["easy", "medium", "hard"]


# class SubmitRequest(BaseModel):
#     session_id: str
#     answers: list[list[str]]

# class SignupRequest(BaseModel):
#     email: EmailStr
#     password: str = Field(min_length=8, max_length=128)


# class LoginRequest(BaseModel):
#     email: EmailStr
#     password: str = Field(min_length=1, max_length=128)


# @app.get("/api/health")
# def health():
#     return {"status": "ok"}


# @app.post("/api/quiz/generate")
# def generate_quiz(payload: GenerateRequest):
#     try:
#         user = User(
#             content=payload.content.strip(),
#             no_of_questions=payload.no_of_questions,
#             level=payload.level,
#         )
#         quiz = generate_answer(user)
#         if quiz is None or not quiz.questions:
#             raise HTTPException(status_code=502, detail="The AI could not generate a quiz. Please try again.")
#         if len(quiz.questions) != payload.no_of_questions:
#             # Keep the generated result if the model returns a slightly different count.
#             pass

#         session_id = str(uuid.uuid4())
#         create_quiz_session(session_id, datetime.now().isoformat(timespec="seconds"), quiz.model_dump())

#         # Never send the answer key to the browser before the quiz is submitted.
#         safe_quiz = {
#             "topic": quiz.topic,
#             "questions": [
#                 {
#                     "question": q.question,
#                     "type": q.type,
#                     "options": q.options,
#                     "difficulty": q.difficulty,
#                 }
#                 for q in quiz.questions
#             ],
#         }
#         return {"session_id": session_id, "quiz": safe_quiz}
#     except HTTPException:
#         raise
#     except Exception as exc:
#         raise HTTPException(status_code=502, detail=f"Quiz generation failed: {exc}") from exc


# @app.post("/api/quiz/submit")
# def submit_quiz(payload: SubmitRequest):
#     stored = get_quiz_session(payload.session_id)
#     if not stored:
#         raise HTTPException(status_code=404, detail="Quiz session not found. Please generate a new quiz.")
#     if stored["submitted"]:
#         raise HTTPException(status_code=409, detail="This quiz has already been submitted.")

#     quiz = Quiz.model_validate(json.loads(stored["quiz"]))
#     if len(payload.answers) != len(quiz.questions):
#         raise HTTPException(status_code=400, detail="Please submit an answer for every question.")

#     results = []
#     for question, raw_answer in zip(quiz.questions, payload.answers):
#         user_answer = [str(answer).strip() for answer in raw_answer if str(answer).strip()]

#         if question.type in ("mcq", "multiple_answer"):
#             is_correct = check_answer(question, user_answer)
#             result = QuizResult(
#                 question=question.question,
#                 is_correct=is_correct,
#                 user_answer=user_answer,
#                 correct_answer=question.answer,
#                 description=question.description,
#             )
#         else:
#             try:
#                 evaluation = evaluate_answer(question, user_answer)
#                 if evaluation is None:
#                     raise RuntimeError("AI evaluation returned no result.")
#                 result = QuizResult(
#                     question=question.question,
#                     is_correct=evaluation.is_correct,
#                     user_answer=evaluation.user_answer,
#                     correct_answer=evaluation.correct_answer,
#                     description=evaluation.description,
#                 )
#             except Exception as exc:
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"Could not evaluate a coding/theory answer. Please try submitting again. Details: {exc}",
#                 ) from exc

#         results.append(result)

#     score = sum(1 for result in results if result.is_correct)
#     save_quiz(
#         stored["date"],
#         quiz.model_dump(),
#         [result.model_dump() for result in results],
#         score,
#     )
#     mark_quiz_session_submitted(payload.session_id)
#     return {
#         "score": score,
#         "total": len(results),
#         "results": [result.model_dump() for result in results],
#     }


# @app.get("/api/history")
# def history():
#     try:
#         return {"items": get_all_history()}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail="Could not load quiz history.") from exc


# @app.get("/api/history/{quiz_id}")
# def history_item(quiz_id: int):
#     item = get_history_by_id(quiz_id)
#     if not item:
#         raise HTTPException(status_code=404, detail="Quiz history entry not found.")
#     return item


# @app.on_event("startup")
# def startup():
#     init_auth_db()


# @app.post("/api/auth/signup")
# def signup(payload: SignupRequest):
#     password = payload.password

#     if not re.search(r"[A-Za-z]", password) or not re.search(
#         r"\d", password
#     ):
#         raise HTTPException(
#             status_code=400,
#             detail="Password must contain at least one letter and one number.",
#         )

#     if find_user_by_email(payload.email):
#         raise HTTPException(
#             status_code=409,
#             detail="An account with this email already exists.",
#         )

#     try:
#         user_id = create_user(
#             payload.email,
#             hash_password(password),
#         )
#     except Exception as error:
#         # The UNIQUE database constraint also protects against
#         # two signup requests arriving at the same time.
#         if find_user_by_email(payload.email):
#             raise HTTPException(
#                 status_code=409,
#                 detail="An account with this email already exists.",
#             ) from error
#         raise

#     token = create_access_token(user_id)

#     return {
#         "message": "Account created successfully",
#         "access_token": token,
#         "token_type": "bearer",
#         "user": {
#             "id": user_id,
#             "email": payload.email.lower(),
#         },
#     }


# @app.post("/api/auth/login")
# def login(payload: LoginRequest):
#     user = find_user_by_email(payload.email)

#     if not user or not verify_password(
#         payload.password,
#         user["password_hash"],
#     ):
#         raise HTTPException(
#             status_code=401,
#             detail="Incorrect email or password.",
#         )

#     token = create_access_token(user["id"])

#     return {
#         "message": "Login successful",
#         "access_token": token,
#         "token_type": "bearer",
#         "user": {
#             "id": user["id"],
#             "email": user["email"],
#         },
#     }


import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Literal

import jwt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

from settings import User, Quiz, QuizResult
from llm import generate_answer, evaluate_answer, check_answer

from database import (
    init_db,
    create_user,
    find_user_by_email,
    find_user_by_id,
    create_quiz_session,
    get_quiz_session,
    mark_quiz_session_submitted,
    save_quiz,
    get_all_history,
    get_history_by_id,
    record_concept_result,
    get_weak_concepts,
    get_last_weekly_quiz,
    save_weekly_quiz,
)

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_user_id_from_token,
    SECRET_KEY,
    ALGORITHM,
)

app = FastAPI(title="Quizwise API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


# ---------------- REQUEST MODELS ----------------

class GenerateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    no_of_questions: int = Field(ge=1, le=30)
    level: Literal["easy", "medium", "hard"]


class SubmitRequest(BaseModel):
    session_id: str
    answers: list[list[str]]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ---------------- AUTHENTICATION ----------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Please log in to continue.",
        )

    try:
        user_id = get_user_id_from_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired login token. Please log in again.",
        )

    user = find_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account not found. Please log in again.",
        )

    return user


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    password = payload.password

    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one letter and one number.",
        )

    email = payload.email.lower().strip()

    if find_user_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    try:
        user_id = create_user(email, hash_password(password))
    except Exception as exc:
        if find_user_by_email(email):
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            ) from exc
        raise

    return {
        "message": "Account created successfully",
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
        "user": {"id": user_id, "email": email},
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = find_user_by_email(payload.email)

    if not user or not verify_password(
        payload.password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
        )

    return {
        "message": "Login successful",
        "access_token": create_access_token(user["id"]),
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"]},
    }


@app.get("/api/auth/me")
def current_user(user=Depends(get_current_user)):
    return {"user": user}


# ---------------- QUIZ HELPERS ----------------

def make_safe_quiz(quiz):
    """Do not reveal correct answers before submission."""
    return {
        "topic": quiz.topic,
        "questions": [
            {
                "question": q.question,
                "type": q.type,
                "options": q.options,
                "difficulty": q.difficulty,
                "concept": getattr(q, "concept", None),
            }
            for q in quiz.questions
        ],
    }


def create_quiz_for_user(payload, user_id):
    user_request = User(
        content=payload.content.strip(),
        no_of_questions=payload.no_of_questions,
        level=payload.level,
    )

    quiz = generate_answer(user_request)

    if quiz is None or not quiz.questions:
        raise HTTPException(
            status_code=502,
            detail="The AI could not generate a quiz. Please try again.",
        )

    session_id = str(uuid.uuid4())
    quiz_date = datetime.now().isoformat(timespec="seconds")

    create_quiz_session(
        session_id,
        user_id,
        quiz_date,
        quiz.model_dump(),
    )

    return {
        "session_id": session_id,
        "quiz": make_safe_quiz(quiz),
    }


# ---------------- QUIZ GENERATION ----------------

import traceback

@app.post("/api/quiz/generate")
def generate_quiz(payload: GenerateRequest, user=Depends(get_current_user)):
    try:
        return create_quiz_for_user(payload, user["id"])
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()   # prints the real error in the terminal
        raise HTTPException(status_code=502, detail="Quiz generation failed. Please try again.") from exc

# ---------------- QUIZ SUBMISSION ----------------

@app.post("/api/quiz/submit")
def submit_quiz(
    payload: SubmitRequest,
    user=Depends(get_current_user),
):
    user_id = user["id"]

    # Only this user's session can be accessed.
    stored = get_quiz_session(payload.session_id, user_id)

    if not stored:
        raise HTTPException(
            status_code=404,
            detail="Quiz session not found. Please generate a new quiz.",
        )

    if stored["submitted"]:
        raise HTTPException(
            status_code=409,
            detail="This quiz has already been submitted.",
        )

    quiz = Quiz.model_validate(stored["quiz"])

    if len(payload.answers) != len(quiz.questions):
        raise HTTPException(
            status_code=400,
            detail="Please submit an answer for every question.",
        )

    results = []

    for question, raw_answer in zip(quiz.questions, payload.answers):
        user_answer = [
            str(answer).strip()
            for answer in raw_answer
            if str(answer).strip()
        ]

        if question.type in ("mcq", "multiple_answer"):
            is_correct = check_answer(question, user_answer)

            result = QuizResult(
                question=question.question,
                is_correct=is_correct,
                user_answer=user_answer,
                correct_answer=question.answer,
                description=question.description,
            )
        else:
            try:
                evaluation = evaluate_answer(question, user_answer)

                if evaluation is None:
                    raise RuntimeError("AI evaluation returned no result.")

                result = QuizResult(
                    question=question.question,
                    is_correct=evaluation.is_correct,
                    user_answer=evaluation.user_answer,
                    correct_answer=evaluation.correct_answer,
                    description=evaluation.description,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail="Could not evaluate an answer. Please try again.",
                ) from exc

        results.append(result)

    score = sum(1 for result in results if result.is_correct)

    # Save the result under the logged-in user.
    save_quiz(
        user_id,
        stored["date"],
        quiz.model_dump(),
        [result.model_dump() for result in results],
        score,
    )

    # Record correct and incorrect attempts by concept.
    # The Question model must include a concept field for
    # meaningful concept-level tracking.
    for question, result in zip(quiz.questions, results):
        concept = getattr(question, "concept", None) or quiz.topic
        record_concept_result(
            user_id,
            concept,
            result.is_correct,
        )

    if not mark_quiz_session_submitted(payload.session_id, user_id):
        raise HTTPException(
            status_code=409,
            detail="This quiz has already been submitted.",
        )

    return {
        "score": score,
        "total": len(results),
        "results": [result.model_dump() for result in results],
    }


# ---------------- PERSONAL QUIZ HISTORY ----------------

@app.get("/api/history")
def history(user=Depends(get_current_user)):
    return {"items": get_all_history(user["id"])}


@app.get("/api/history/{quiz_id}")
def history_item(
    quiz_id: int,
    user=Depends(get_current_user),
):
    item = get_history_by_id(quiz_id, user["id"])

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Quiz history entry not found.",
        )

    return item


# ---------------- WEAK CONCEPTS ----------------

@app.get("/api/weak-concepts")
def weak_concepts(user=Depends(get_current_user)):
    return {"items": get_weak_concepts(user["id"])}


# ---------------- WEEKLY QUIZ ----------------

@app.post("/api/weekly-quiz/generate")
def generate_weekly_quiz(user=Depends(get_current_user)):
    user_id = user["id"]

    last_quiz = get_last_weekly_quiz(user_id)

    if last_quiz:
        last_date = datetime.fromisoformat(last_quiz["created_at"])
        now = datetime.utcnow()

        if now - last_date < timedelta(days=7):
            next_date = last_date + timedelta(days=7)
            return {
                "message": "Your weekly quiz has already been generated.",
                "available_after": next_date.isoformat(timespec="seconds"),
            }

    weak = get_weak_concepts(user_id)

    if not weak:
        raise HTTPException(
            status_code=400,
            detail="Complete a quiz first so we can identify concepts to practise.",
        )

    concepts = [
        item["concept"]
        for item in weak[:5]
    ]

    request = GenerateRequest(
        content=(
            "Create a practice quiz focusing on these concepts the learner "
            "needs to improve: " + ", ".join(concepts)
        ),
        no_of_questions=10,
        level="medium",
    )

    generated = create_quiz_for_user(request, user_id)

    save_weekly_quiz(user_id, generated["session_id"])

    return {
        "message": "Weekly practice quiz generated successfully.",
        "weak_concepts": concepts,
        **generated,
    }
