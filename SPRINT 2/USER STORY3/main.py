from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import os
import random

from models import SessionLocal, Feedback, Base, engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload-claim")
async def upload_claim(
    file: UploadFile = File(...),
    description: str = Form(""),
    userId: str = Form(...)
):
    """
    Receive user-uploaded PDF/JPG/PNG files, simulate an AI-generated prediction value,
    and return the result along with confidence information.
    """
    try:
        if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
            return JSONResponse(
                status_code=400,
                content={"message": "Unsupported file type"}
            )

        file_extension = file.filename.split(".")[-1]
        new_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        prediction_id = str(uuid.uuid4())
        prediction_value = round(random.uniform(8000, 20000), 2)
        confidence = round(random.uniform(0.7, 0.95), 3)

        return {
            "message": "File uploaded successfully",
            "predictionId": prediction_id,
            "filename": new_filename,
            "userId": userId,
            "description": description,
            "prediction": prediction_value,
            "confidence": confidence
        }

    except Exception as e:
        print("Upload error:", str(e))
        raise HTTPException(
            status_code=500,
            detail="Server error during upload."
        )

@app.post("/submit-feedback")
async def submit_feedback(
    predictionId: str = Form(...),
    feedbackText: str = Form(""),
    rating: str = Form(""),
    userId: str = Form("")
):
    """
    Receive user feedback regarding a prediction result:
    - predictionId: The prediction ID (required)
    - feedbackText: The user feedback text (optional)
    - rating: Satisfaction rating (1~5) (optional)
    - userId: The user ID (optional)
    """
    db = SessionLocal()
    try:
        feedback_id = str(uuid.uuid4())

        new_feedback = Feedback(
            feedback_id=feedback_id,
            prediction_id=predictionId,
            feedback_text=feedbackText,
            rating=rating,
            user_id=userId
        )

        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)

        return {
            "message": "Feedback received & stored in DB",
            "feedbackId": feedback_id,
            "predictionId": predictionId,
            "feedbackText": feedbackText,
            "rating": rating,
            "userId": userId
        }
    except Exception as e:
        db.rollback()
        print("Error saving feedback:", e)
        raise HTTPException(status_code=500, detail="Failed to save feedback.")
    finally:
        db.close()
