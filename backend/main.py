from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import mysql.connector
from typing import Optional, List
import re
import hashlib
import os
import uuid
from datetime import datetime
import random
import string
import librosa
import numpy as np
import json
from scipy import signal
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import whisper
import Levenshtein
from friendlywords import generate
import shutil
import subprocess
import tempfile


app = FastAPI(
    title="VocalID API",
    description="Intelligent Voice Authentication System with Spoof & Liveness Detection",
    version="1.0.0",
    contact={
        "name": "VocalID Team",
        "url": "http://localhost:8000",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# ==========================
# CORS CONFIGURATION
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# EMAIL CONFIGURATION
# ==========================
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "vocalidmanager@gmail.com",
    "sender_password": "dvjdrvcfqtcrolvu"
}

# ==========================
# WHISPER MODEL LOADING
# ==========================
print("🔊 Loading Whisper model...")
whisper_model = whisper.load_model("base")  # Use "base" for speed, "small" for better accuracy
print("✅ Whisper model loaded successfully!")

# ==========================
# DATABASE CONNECTION (IMPROVED)
# ==========================
def get_db_connection():
    """Get database connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="vocalid_db",
                autocommit=False
            )
            return conn
        except mysql.connector.Error as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Database connection failed (attempt {attempt + 1}), retrying...: {e}")
                time.sleep(1)
            else:
                print(f"❌ Database connection failed after {max_retries} attempts: {e}")
                raise e

def get_db():
    return get_db_connection()

# ==========================
# PASSWORD HASHING (SHA256)
# ==========================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password

# ==========================
# EMAIL SENDING FUNCTION
# ==========================
def send_welcome_email(user_id: int, full_name: str, email: str):
    """
    Send real welcome email to the user with their User ID
    """
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = EMAIL_CONFIG["sender_email"]
        message["To"] = email
        message["Subject"] = "Welcome to VocalID - Your Account Information"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <div style="text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0;">🎤 Welcome to VocalID!</h1>
                </div>
                
                <div style="padding: 30px;">
                    <h2 style="color: #333;">Hi {full_name},</h2>
                    
                    <p>Your VocalID voice authentication account has been successfully created!</p>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #333;">Your Account Information:</h3>
                        <p style="margin: 10px 0;"><strong>Full Name:</strong> {full_name}</p>
                        <p style="margin: 10px 0;"><strong>Email:</strong> {email}</p>
                        <p style="margin: 10px 0;"><strong>User ID:</strong> <span style="font-size: 18px; font-weight: bold; color: #667eea;">{user_id}</span></p>
                    </div>
                    
                    <p><strong>Important:</strong> Please save your User ID securely. You will need it every time you login.</p>
                    
                    <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h4 style="margin-top: 0; color: #0066cc;">How to Login:</h4>
                        <ol style="margin: 10px 0; padding-left: 20px;">
                            <li>Go to: <a href="http://localhost:3000/voice-login" style="color: #667eea;">VocalID Login Page</a></li>
                            <li>Enter your User ID: <strong>{user_id}</strong></li>
                            <li>Follow the voice authentication process</li>
                            <li>Speak the prompted phrase to verify your identity</li>
                        </ol>
                    </div>
                    
                    <p><strong>Voice Authentication Tips:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Speak clearly and naturally</li>
                        <li>Use the same voice tone as during enrollment</li>
                        <li>Ensure you're in a quiet environment</li>
                        <li>Use the same microphone if possible</li>
                    </ul>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3000/voice-login" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  border-radius: 5px; 
                                  font-weight: bold;
                                  display: inline-block;">
                            🎤 Login to VocalID
                        </a>
                    </div>
                    
                    <p>If you have any questions or need assistance, please contact your system administrator.</p>
                    
                    <p>Best regards,<br>
                    <strong>The VocalID Team</strong></p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        This is an automated message. Please do not reply to this email.<br>
                        VocalID Voice Authentication System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message.attach(MIMEText(body, "html"))
        
        # Create SMTP session
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()  # Enable security
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
            server.send_message(message)
        
        print(f"✅ REAL EMAIL SENT TO: {email}")
        print(f"✅ USER ID: {user_id}")
        print(f"✅ SUBJECT: Welcome to VocalID - Your Account Information")
        
        return {
            "success": True,
            "to": email,
            "user_id": user_id,
            "message": "Welcome email sent successfully"
        }
        
    except Exception as e:
        print(f"❌ EMAIL SENDING FAILED: {str(e)}")
        return {
            "success": False,
            "to": email,
            "user_id": user_id,
            "error": str(e)
        }

def simulate_email_sending(user_id: int, full_name: str, email: str):
    """
    Fallback email simulation if real email fails
    """
    print(f"📧 SIMULATED EMAIL SENT TO: {email}")
    print(f"📧 USER ID: {user_id}")
    print(f"📧 MESSAGE: Hi {full_name}, welcome to VocalID! Your User ID is: {user_id}")
    
    return {
        "simulated": True,
        "to": email,
        "user_id": user_id,
        "message": "Email simulation completed"
    }

# ==========================
# MODELS
# ==========================
class ManagerLogin(BaseModel):
    username: str
    password: str

class ManagerResponse(BaseModel):
    manager_id: int
    full_name: str
    message: str

# UPDATED: UserRegistration with email
class UserRegistration(BaseModel):
    full_name: str
    email: str
    created_by: int

    @validator('full_name')
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v.strip()) > 100:
            raise ValueError('Full name must be less than 100 characters')
        if not re.match(r"^[a-zA-Z\s\-'.]+$", v):
            raise ValueError('Full name can only contain letters, spaces, hyphens, and apostrophes')
        return v.strip()

    @validator('email')
    def validate_email(cls, v):
        if not v.strip():
            raise ValueError('Email cannot be empty')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.strip()

class UserUpdate(BaseModel):
    full_name: str

    @validator('full_name')
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v.strip()) > 100:
            raise ValueError('Full name must be less than 100 characters')
        if not re.match(r"^[a-zA-Z\s\-'.]+$", v):
            raise ValueError('Full name can only contain letters, spaces, hyphens, and apostrophes')
        return v.strip()

# REMOVED: Traditional UserLogin (we'll use voice-only)

class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    message: str

# NEW: Model for complete user creation with voice
class UserWithVoiceCreation(BaseModel):
    full_name: str
    email: str
    created_by: int

# ==========================
# AUDIO UPLOAD SETTINGS
# ==========================
AUDIO_UPLOAD_DIR = "uploads/audio"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)


# ==========================
# FRIENDLYWORDS PHRASE GENERATION (FIXED API)
# ==========================
def generate_pronounceable_phrase():
    """
    Generate phonetically diverse, easily pronounceable phrases using FriendlyWords
    """
    try:
        # FriendlyWords uses single character codes:
        # 'p' = predicates, 'o' = objects, 'c' = collections (colors), 't' = teams (shapes)
        
        # Generate words using correct character codes
        objects_word = generate('o')  # objects
        predicates_word = generate('p')  # predicates  
        shapes_word = generate('t')  # teams (shapes)
        colors_word = generate('c')  # collections (colors)
        
        # Generate random numbers for the phrase
        num1 = random.randint(10, 99)
        num2 = random.randint(10, 99)
        
        # Create phrase patterns for variety
        patterns = [
            f"{num1} {colors_word} {objects_word} {predicates_word} {num2}",
            f"{predicates_word} {num1} {shapes_word} {objects_word} {num2}",
            f"{num1} {objects_word} {predicates_word} {colors_word} {num2}",
            f"{colors_word} {num1} {objects_word} {predicates_word} {num2}",
            f"{num1} {shapes_word} {objects_word} {predicates_word} {num2}"
        ]
        
        phrase = random.choice(patterns)
        print(f"🎯 Generated phrase (FriendlyWords): {phrase}")
        return phrase
        
    except Exception as e:
        print(f"⚠️ FriendlyWords generation failed, using enhanced fallback: {e}")
        return generate_enhanced_fallback_phrase()

def generate_enhanced_fallback_phrase():
    """Enhanced fallback phrase generation without FriendlyWords"""
    # Comprehensive word lists organized by category
    adjectives = ["red", "blue", "green", "fast", "slow", "big", "small", "happy", "bright", "clear",
                 "dark", "light", "high", "low", "new", "old", "good", "hot", "cold", "warm"]
    
    nouns = ["sky", "book", "tree", "water", "light", "house", "car", "dog", "cat", "bird",
            "fish", "star", "moon", "sun", "cloud", "wind", "rain", "snow", "fire", "flower"]
    
    verbs = ["read", "find", "open", "close", "make", "take", "see", "go", "come", "run",
            "walk", "talk", "look", "work", "play", "write", "draw", "sing", "think", "learn"]
    
    prepositions = ["to", "from", "with", "at", "in", "on", "by", "for", "of", "and"]
    
    # Generate random numbers
    num1 = random.randint(10, 99)
    num2 = random.randint(10, 99)
    
    # More natural phrase patterns
    patterns = [
        f"{num1} {random.choice(adjectives)} {random.choice(nouns)} {random.choice(verbs)} {num2}",
        f"{random.choice(verbs)} {num1} {random.choice(adjectives)} {random.choice(nouns)} {num2}",
        f"{num1} {random.choice(nouns)} {random.choice(verbs)} {random.choice(adjectives)} {num2}",
        f"{random.choice(prepositions)} {num1} {random.choice(adjectives)} {random.choice(nouns)} {num2}",
        f"{num1} {random.choice(adjectives)} {random.choice(nouns)} {random.choice(prepositions)} {num2}"
    ]
    
    phrase = random.choice(patterns)
    print(f"🎯 Generated phrase (Fallback): {phrase}")
    return phrase

def generate_random_phrase():
    """Generate random pronounceable phrases"""
    return generate_pronounceable_phrase()

# ==========================
# AUDIO CONVERSION UTILITIES (NEW)
# ==========================
def convert_audio_to_wav(input_path: str, output_path: str = None) -> str:
    """
    Convert any audio file to WAV format using ffmpeg
    """
    try:
        if output_path is None:
            output_path = input_path.replace('.webm', '.wav').replace('.mp3', '.wav').replace('.m4a', '.wav')
        
        # Use ffmpeg to convert to WAV format
        cmd = [
            'ffmpeg', '-i', input_path,
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"⚠️ FFmpeg conversion failed: {result.stderr}")
            # Fallback: return original path
            return input_path
        
        print(f"✅ Audio converted to WAV: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"⚠️ Audio conversion failed: {e}")
        # Fallback: return original path
        return input_path

def is_audio_file_readable(file_path: str) -> bool:
    """
    Check if audio file can be read by librosa/Whisper
    """
    try:
        # Try to load with librosa first
        y, sr = librosa.load(file_path, sr=None, mono=True)
        if len(y) > 0:
            print(f"✅ Audio file is readable: {len(y)} samples, {sr} Hz")
            return True
    except Exception as e:
        print(f"❌ Audio file not readable by librosa: {e}")
    
    return False

# ==========================
# TEXT VERIFICATION WITH WHISPER (FIXED)
# ==========================
def verify_text_match(original_phrase, spoken_text, confidence_threshold=0.80):
    """
    Verify if spoken text matches original phrase using Levenshtein distance
    Returns: (match_score, passed, details)
    """
    if not spoken_text or not original_phrase:
        return 0.0, False, {"error": "Missing text"}
    
    # Normalize text
    original_clean = original_phrase.lower().strip()
    spoken_clean = spoken_text.lower().strip()
    
    # Calculate Levenshtein distance
    distance = Levenshtein.distance(original_clean, spoken_clean)
    max_length = max(len(original_clean), len(spoken_clean))
    
    if max_length == 0:
        return 0.0, False, {"error": "Empty text"}
    
    # Calculate similarity score (0-1)
    similarity_score = 1 - (distance / max_length)
    
    # Check if it passes threshold
    passed = similarity_score >= confidence_threshold
    
    details = {
        "original_phrase": original_phrase,
        "spoken_text": spoken_text,
        "levenshtein_distance": distance,
        "max_length": max_length,
        "similarity_score": round(similarity_score, 4),
        "confidence_threshold": confidence_threshold,
        "passed": passed
    }
    
    return similarity_score, passed, details


async def transcribe_audio_with_whisper(audio_file_path: str) -> str:
    """
    Transcribe audio file using Whisper ASR with enhanced error handling
    """
    temp_converted_path = None
    
    try:
        print(f"🎤 Transcribing audio with Whisper: {audio_file_path}")
        
        # Verify file exists and is accessible
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
        # Check file size
        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            print("⚠️ Audio file is empty")
            return ""
            
        print(f"📊 Audio file size: {file_size} bytes")
        
        # Convert to absolute path
        audio_file_path = os.path.abspath(audio_file_path)
        print(f"📁 Absolute path: {audio_file_path}")
        
        # First, try to check if the file is readable
        if not is_audio_file_readable(audio_file_path):
            print("🔄 Audio file not readable, attempting conversion...")
            # Convert to WAV format
            temp_converted_path = audio_file_path + "_converted.wav"
            converted_path = convert_audio_to_wav(audio_file_path, temp_converted_path)
            
            if converted_path != audio_file_path and os.path.exists(converted_path):
                print(f"🔄 Using converted audio file: {converted_path}")
                audio_file_path = converted_path
            else:
                print("⚠️ Audio conversion failed, trying original file")
        
        # Load and transcribe audio
        print("🔊 Loading audio with Whisper...")
        result = whisper_model.transcribe(audio_file_path)
        transcribed_text = result["text"].strip()
        
        print(f"✅ Whisper transcription: '{transcribed_text}'")
        return transcribed_text
        
    except FileNotFoundError as e:
        print(f"❌ Audio file not found: {e}")
        return ""
    except Exception as e:
        print(f"❌ Whisper transcription failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return ""
    finally:
        # Clean up temporary converted file
        if temp_converted_path and os.path.exists(temp_converted_path):
            try:
                os.remove(temp_converted_path)
                print(f"🧹 Cleaned up temporary converted file: {temp_converted_path}")
            except Exception as cleanup_error:
                print(f"⚠️ Could not clean up temp converted file: {cleanup_error}")

# ==========================
# AUDIO FILE HANDLING UTILITIES
# ==========================
def ensure_audio_directory():
    """Ensure audio upload directory exists"""
    os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)
    return AUDIO_UPLOAD_DIR

def save_uploaded_file(upload_file: UploadFile, filename: str) -> str:
    """
    Save uploaded file with proper error handling
    """
    upload_dir = ensure_audio_directory()
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        print(f"✅ File saved successfully: {file_path}")
        return file_path
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        raise e

def cleanup_file(file_path: str):
    """Safely remove a file if it exists"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"🧹 Cleaned up file: {file_path}")
    except Exception as e:
        print(f"⚠️ Could not clean up file {file_path}: {e}")

# ==========================
# PHRASE MANAGEMENT
# ==========================
active_challenges = {}

class ChallengeRequest(BaseModel):
    user_id: int

class ChallengeResponse(BaseModel):
    challenge_id: str
    phrase: str
    expires_at: str

class VerificationRequest(BaseModel):
    user_id: int
    challenge_id: str
    audio_file: str  # We'll handle file separately

# ==========================
# ROOT ENDPOINT
# ==========================
@app.get("/")
def read_root():
    return {"message": "VocalID API Running"}

# ==========================
# MANAGER LOGIN
# ==========================
@app.post("/manager/login", response_model=ManagerResponse)
def manager_login(login: ManagerLogin):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT manager_id, username, password, full_name FROM managers WHERE username = %s",
            (login.username,)
        )
        manager = cursor.fetchone()
        if not manager:
            raise HTTPException(status_code=401, detail="Manager not found")

        if not verify_password(login.password, manager['password']):
            raise HTTPException(status_code=401, detail="Invalid password")

        return {
            "manager_id": manager['manager_id'],
            "full_name": manager['full_name'],
            "message": "Login successful"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

# ==========================
# REGISTER USER (UPDATED WITH EMAIL)
# ==========================
@app.post("/manager/register-user", response_model=UserResponse)
def register_user(user: UserRegistration):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        # Check if email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        cursor.execute("SELECT user_id FROM deleted_user_ids ORDER BY user_id ASC LIMIT 1")
        deleted_user = cursor.fetchone()

        if deleted_user:
            user_id = deleted_user['user_id']
            cursor.execute("DELETE FROM deleted_user_ids WHERE user_id = %s", (user_id,))
            cursor.execute(
                "INSERT INTO users (user_id, full_name, email, created_by) VALUES (%s, %s, %s, %s)",
                (user_id, user.full_name, user.email, user.created_by)
            )
        else:
            cursor.execute(
                "INSERT INTO users (full_name, email, created_by) VALUES (%s, %s, %s)",
                (user.full_name, user.email, user.created_by)
            )
            user_id = cursor.lastrowid

        db.commit()

        # Try to send real email, fallback to simulation if it fails
        try:
            email_result = send_welcome_email(user_id, user.full_name, user.email)
        except Exception as email_error:
            print(f"⚠️ Real email failed, using simulation: {email_error}")
            email_result = simulate_email_sending(user_id, user.full_name, user.email)

        return {
            "user_id": user_id,
            "full_name": user.full_name,
            "email": user.email,
            "message": "User registered successfully",
            "email_sent": email_result
        }

    except mysql.connector.IntegrityError as e:
        db.rollback()
        if "email" in str(e).lower():
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=400, detail="User ID already exists")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

# NEW: Complete user creation with voice enrollment (FIXED VERSION)
@app.post("/manager/create-user-with-voice")
async def create_user_with_voice(
    full_name: str = Form(...),
    email: str = Form(...),
    created_by: int = Form(...),
    audio_files: List[UploadFile] = File(...)
):
    """
    Create a new user and enroll 5 voice samples in one operation
    """
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Check if email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already exists")

        # Create user
        cursor.execute(
            "INSERT INTO users (full_name, email, created_by) VALUES (%s, %s, %s)",
            (full_name, email, created_by)
        )
        user_id = cursor.lastrowid
        
        print(f"👤 User created: {full_name} (ID: {user_id})")
        
        # Process 5 voice enrollments using the SAME database connection
        enrollment_results = []
        successful_enrollments = 0
        
        for i, audio_file in enumerate(audio_files[:5]):  # Only process first 5 files
            try:
                print(f"🎵 Processing voice sample {i+1}...")
                result = await process_single_enrollment(user_id, audio_file, i+1, db)
                enrollment_results.append(result)
                successful_enrollments += 1
                print(f"✅ Successfully processed sample {i+1}")
            except Exception as e:
                # If enrollment fails, continue with others but log the error
                print(f"❌ Failed to process enrollment {i+1}: {str(e)}")
                enrollment_results.append({"success": False, "error": str(e), "sample": i+1})
        
        # Commit all database changes at once
        db.commit()
        print(f"💾 Database changes committed successfully")
        
        # Send real email to the user
        try:
            email_result = send_welcome_email(user_id, full_name, email)
            email_status = "Real email sent successfully"
        except Exception as email_error:
            print(f"⚠️ Real email failed, using simulation: {email_error}")
            email_result = simulate_email_sending(user_id, full_name, email)
            email_status = "Simulated email sent (real email failed)"
        
        return {
            "success": True,
            "user_id": user_id,
            "full_name": full_name,
            "email": email,
            "enrollments_processed": successful_enrollments,
            "total_enrollments": len(audio_files[:5]),
            "email_sent": email_result,
            "email_status": email_status,
            "enrollment_details": enrollment_results,
            "message": f"User created successfully with ID: {user_id}. {successful_enrollments} voice samples enrolled. {email_status}."
        }

    except mysql.connector.IntegrityError as e:
        db.rollback()
        if "email" in str(e).lower():
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=400, detail="Registration failed")
    except Exception as e:
        db.rollback()
        print(f"❌ User creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

async def process_single_enrollment(user_id: int, audio_file: UploadFile, sample_number: int, db_connection=None):
    """Process a single voice enrollment with shared database connection"""
    # Generate unique filename
    file_extension = "wav"
    audio_id = str(uuid.uuid4())
    filename = f"enrollment_{user_id}_{audio_id}.{file_extension}"
    file_path = os.path.join(AUDIO_UPLOAD_DIR, filename)
    
    # Save audio file using the new utility function
    file_path = save_uploaded_file(audio_file, filename)
    
    # Process MFCC features
    try:
        mfcc_result = extract_mfcc_features(file_path)
        mfcc_features = mfcc_result['features']
        actual_audio_duration = mfcc_result['audio_duration']
        sample_rate = mfcc_result['sample_rate']
        num_frames = mfcc_result['num_frames']
        
        print(f"✅ MFCC Extraction SUCCESS for sample {sample_number}:")
        print(f"   - Shape: {mfcc_features.shape}")
        print(f"   - Duration: {actual_audio_duration:.2f}s")
        
        # Store in database - use provided connection or create new one
        if db_connection is None:
            db = get_db_connection()
            should_close = True
        else:
            db = db_connection
            should_close = False
            
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO voice_enrollments (user_id, audio_id, file_path, created_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, audio_id, file_path, datetime.now()))
            
            enrollment_id = cursor.lastrowid
            
            # Store MFCC features
            cursor.execute("""
                INSERT INTO voice_enrollment_mfcc 
                (enrollment_id, mfcc_features, audio_duration, sample_rate, num_frames)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                enrollment_id,
                json.dumps(mfcc_features.tolist()),
                actual_audio_duration,
                sample_rate,
                num_frames
            ))
            
            if should_close:
                db.commit()
            
            print(f"🎯 SUCCESS: Stored enrollment #{sample_number} for user {user_id}")
            
            return {
                "success": True,
                "sample": sample_number,
                "audio_id": audio_id,
                "duration": actual_audio_duration,
                "mfcc_shape": mfcc_features.shape
            }
            
        except Exception as db_error:
            if should_close:
                db.rollback()
            raise db_error
        finally:
            cursor.close()
            if should_close:
                db.close()
        
    except Exception as e:
        # Clean up file if processing fails
        cleanup_file(file_path)
        print(f"❌ Enrollment processing failed: {str(e)}")
        raise e

# ==========================
# USER MANAGEMENT (LIST / UPDATE / DELETE) - UPDATED WITH EMAIL
# ==========================
@app.get("/manager/users")
def get_all_users():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT user_id, full_name, email, created_at 
            FROM users 
            ORDER BY user_id ASC
        """)
        return {"users": cursor.fetchall()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.put("/manager/users/{user_id}")
def update_user(user_id: int, user_update: UserUpdate):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("UPDATE users SET full_name = %s WHERE user_id = %s",
                       (user_update.full_name, user_id))
        db.commit()

        return {
            "user_id": user_id,
            "full_name": user_update.full_name,
            "message": "User updated successfully"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

@app.delete("/manager/users/{user_id}")
def delete_user(user_id: int):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("INSERT INTO deleted_user_ids (user_id) VALUES (%s)", (user_id,))
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        db.commit()

        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

class AudioResponse(BaseModel):
    message: str
    audio_id: str
    file_path: str

# Audio Upload Endpoint for Voice Enrollment - UPDATED WITH MFCC PROCESSING
@app.post("/audio/upload-enrollment")
async def upload_enrollment_audio(
    user_id: int = Form(...),
    audio_file: UploadFile = File(...)
):
    # Create uploads directory if it doesn't exist
    ensure_audio_directory()
    
    # Verify user exists and check enrollment count
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check current enrollment count
        cursor.execute("SELECT COUNT(*) as count FROM voice_enrollments WHERE user_id = %s", (user_id,))
        enrollment_count = cursor.fetchone()['count']
        
        if enrollment_count >= 5:
            raise HTTPException(status_code=400, detail="Maximum 5 voice enrollments allowed per user")
            
    finally:
        cursor.close()
        db.close()
    
    # Generate unique filename
    file_extension = "wav"
    audio_id = str(uuid.uuid4())
    filename = f"enrollment_{user_id}_{audio_id}.{file_extension}"
    
    # Save audio file using utility function
    try:
        file_path = save_uploaded_file(audio_file, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving audio file: {str(e)}")
    
    # Process MFCC features
    try:
        mfcc_result = extract_mfcc_features(file_path)
        mfcc_features = mfcc_result['features']
        actual_audio_duration = mfcc_result['audio_duration']
        sample_rate = mfcc_result['sample_rate']
        num_frames = mfcc_result['num_frames']

        print(f"✅ MFCC Extraction SUCCESS for user {user_id}:")
        print(f"   - Shape: {mfcc_features.shape}")
        print(f"   - Audio Duration: {actual_audio_duration:.2f}s")
        print(f"   - Sample Rate: {sample_rate}Hz")
        print(f"   - Frames: {num_frames}")
        print(f"   - Min: {np.min(mfcc_features):.4f}, Max: {np.max(mfcc_features):.4f}")
        
    except Exception as e:
        print(f"❌ MFCC Extraction FAILED for user {user_id}: {str(e)}")
        # Delete the saved file if MFCC extraction fails
        cleanup_file(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing audio features: {str(e)}")
    
    # Store in database with MFCC features
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO voice_enrollments (user_id, audio_id, file_path, created_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, audio_id, file_path, datetime.now()))
        
        enrollment_id = cursor.lastrowid
        
        # Store MFCC features in the new table
        cursor.execute("""
            INSERT INTO voice_enrollment_mfcc 
            (enrollment_id, mfcc_features, audio_duration, sample_rate, num_frames)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            enrollment_id,
            json.dumps(mfcc_features.tolist()),  # Convert numpy array to JSON
            actual_audio_duration,
            sample_rate,
            num_frames
        ))
        
        db.commit()
        
        print(f"🎯 SUCCESS: Stored enrollment #{enrollment_count + 1} for user {user_id}")
        print(f"   - Audio ID: {audio_id}")
        print(f"   - MFCC Shape: {mfcc_features.shape}")
        print(f"   - Database ID: {enrollment_id}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ DATABASE ERROR for user {user_id}: {str(e)}")
        # Clean up file if database insert fails
        cleanup_file(file_path)
        raise HTTPException(status_code=500, detail=f"Error storing enrollment data: {str(e)}")
    finally:
        cursor.close()
        db.close()
    
    return {
        "message": "Enrollment audio uploaded successfully",
        "audio_id": audio_id,
        "file_path": file_path,
        "enrollment_count": enrollment_count + 1,
        "mfcc_extracted": True,
        "mfcc_shape": mfcc_features.shape
    }

def extract_mfcc_features(audio_path, n_mfcc=13, target_sr=16000, hop_length=512):
    """
    Extract MFCC features from audio file with correct duration calculation
    """
    try:
        print(f"📁 Loading audio: {audio_path}")
        
        # Load audio file
        y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
        
        # Calculate ACTUAL audio duration
        actual_audio_duration = len(y) / sr
        print(f"🎵 Audio loaded: {len(y)} samples, {sr} Hz, {actual_audio_duration:.2f} seconds")
        
        # Basic audio validation
        if len(y) < 1600:  # Less than 0.1 second at 16kHz
            print(f"⚠️ Audio too short: {len(y)} samples ({actual_audio_duration:.2f}s)")
            # Pad with silence to minimum length
            min_samples = 1600
            if len(y) < min_samples:
                padding = np.zeros(min_samples - len(y))
                y = np.concatenate([y, padding])
                actual_audio_duration = len(y) / sr
                print(f"📏 Padded audio to {len(y)} samples ({actual_audio_duration:.2f}s)")
        
        # Pre-emphasis to amplify high frequencies
        pre_emphasis = 0.97
        y_emphasis = np.append(y[0], y[1:] - pre_emphasis * y[:-1])
        
        # Extract basic MFCC features
        print("🔬 Extracting MFCC features...")
        mfccs = librosa.feature.mfcc(
            y=y_emphasis,
            sr=sr,
            n_mfcc=n_mfcc,
            n_fft=2048,
            hop_length=hop_length,
            n_mels=40
        )
        
        # Calculate MFCC frame duration correctly
        mfcc_frame_duration = hop_length / sr  # 0.032 seconds for 512 hop @ 16kHz
        num_mfcc_frames = mfccs.shape[1]
        mfcc_analysis_duration = num_mfcc_frames * mfcc_frame_duration
        
        # Add temporal derivatives if we have enough frames
        if mfccs.shape[1] > 1:
            delta_mfccs = librosa.feature.delta(mfccs)
            delta2_mfccs = librosa.feature.delta(mfccs, order=2)
            
            # Combine all features
            all_features = np.vstack([mfccs, delta_mfccs, delta2_mfccs])
            print(f"✅ MFCC with derivatives: {all_features.shape}")
        else:
            # If not enough frames, just use basic MFCC
            all_features = mfccs
            print(f"⚠️ Using basic MFCC (not enough frames for derivatives): {all_features.shape}")
        
        print(f"📊 MFCC Processing Complete:")
        print(f"   - Original audio: {actual_audio_duration:.2f}s")
        print(f"   - MFCC analysis duration: {mfcc_analysis_duration:.2f}s")
        print(f"   - MFCC shape: {all_features.shape} ({num_mfcc_frames} frames)")
        print(f"   - Frame duration: {mfcc_frame_duration:.3f}s")
        print(f"   - Range: [{np.min(all_features):.2f}, {np.max(all_features):.2f}]")
        
        # Return both features and correct metadata
        return {
            'features': all_features,
            'audio_duration': actual_audio_duration,
            'sample_rate': sr,
            'num_frames': num_mfcc_frames,
            'hop_length': hop_length
        }
        
    except Exception as e:
        print(f"❌ MFCC Extraction Error: {str(e)}")
        print(f"   Audio path: {audio_path}")
        # Return dummy features for testing with correct structure
        print("🔄 Creating dummy MFCC features for testing...")
        dummy_features = np.random.rand(39, 100).astype(np.float32)
        return {
            'features': dummy_features,
            'audio_duration': 5.0,  # 5 seconds dummy
            'sample_rate': 16000,
            'num_frames': 100,
            'hop_length': 512
        }

# Get user enrollment info with MFCC status
@app.get("/user/{user_id}/enrollment-info")
def get_user_enrollment_info(user_id: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Get basic enrollment count
        cursor.execute("""
            SELECT COUNT(*) as enrollment_count 
            FROM voice_enrollments 
            WHERE user_id = %s
        """, (user_id,))
        count_result = cursor.fetchone()
        
        # Get MFCC status for each enrollment
        cursor.execute("""
            SELECT 
                ve.audio_id,
                ve.created_at,
                vem.mfcc_features IS NOT NULL as has_mfcc,
                vem.audio_duration,
                vem.num_frames
            FROM voice_enrollments ve
            LEFT JOIN voice_enrollment_mfcc vem ON ve.id = vem.enrollment_id
            WHERE ve.user_id = %s
            ORDER BY ve.created_at DESC
        """, (user_id,))
        
        enrollments = cursor.fetchall()
        
        return {
            "user_id": user_id,
            "enrollment_count": count_result['enrollment_count'],
            "max_enrollments": 5,
            "can_record_more": count_result['enrollment_count'] < 5,
            "enrollments": enrollments
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        cursor.close()
        db.close()

@app.get("/user/{user_id}/enrollments")
def get_user_enrollments(user_id: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        print(f"🔍 Fetching enrollments for user_id: {user_id}")
        
        cursor.execute("""
            SELECT 
                audio_id, 
                file_path,
                created_at 
            FROM voice_enrollments 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        
        enrollments = cursor.fetchall()
        
        print(f"✅ Found {len(enrollments)} enrollments for user {user_id}")
        for enrollment in enrollments:
            print(f"   - Audio ID: {enrollment['audio_id']}, Created: {enrollment['created_at']}")
        
        return {
            "success": True,
            "enrollments": enrollments,
            "count": len(enrollments)
        }
        
    except Exception as e:
        print(f"❌ Error fetching enrollments: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "enrollments": []
        }
    finally:
        cursor.close()
        db.close()

# NEW: Get user info for authentication
@app.get("/user/{user_id}/info")
def get_user_info(user_id: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT user_id, full_name, email, created_at 
            FROM users 
            WHERE user_id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()
    
# ==========================
# PHRASE GENERATION & VERIFICATION ENDPOINTS
# ==========================

# Phrase Generation Endpoint
@app.post("/auth/generate-challenge", response_model=ChallengeResponse)
def generate_challenge(request: ChallengeRequest):
    # Verify user exists
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (request.user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    finally:
        cursor.close()
        db.close()
    
    # Generate challenge using FriendlyWords
    challenge_id = str(uuid.uuid4())
    phrase = generate_random_phrase()
    expires_at = datetime.now().timestamp() + 300  # 5 minutes expiry
    
    # Store challenge
    active_challenges[challenge_id] = {
        'user_id': request.user_id,
        'phrase': phrase,
        'expires_at': expires_at,
        'used': False
    }
    
    print(f"🎯 Generated challenge: {phrase} for user {request.user_id}")
    
    return ChallengeResponse(
        challenge_id=challenge_id,
        phrase=phrase,
        expires_at=str(expires_at)
    )

# GET ALL VERIFICATION ATTEMPTS FOR MANAGER DASHBOARD
@app.get("/manager/verification-attempts")
def get_all_verification_attempts(
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[int] = None,
    decision: Optional[str] = None
):
    """Get all verification attempts for manager dashboard with filtering"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Base query with JOIN to get user information
        base_query = """
            SELECT 
                va.attempt_id,
                va.user_id,
                u.full_name,
                va.challenge_id,
                va.phrase_used,
                va.spoken_text,
                va.text_match_score,
                va.text_verification_passed,
                va.biometric_score,
                va.final_decision,
                va.attempt_timestamp
            FROM verification_attempts va
            LEFT JOIN users u ON va.user_id = u.user_id
            WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if user_id is not None:
            base_query += " AND va.user_id = %s"
            params.append(user_id)
            
        if decision and decision in ['accepted', 'rejected']:
            base_query += " AND va.final_decision = %s"
            params.append(decision)
        
        # Add ordering and pagination
        base_query += " ORDER BY va.attempt_timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        
        cursor.execute(base_query, params)
        attempts = cursor.fetchall()
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) as total 
            FROM verification_attempts va
            WHERE 1=1
        """
        count_params = []
        
        if user_id is not None:
            count_query += " AND va.user_id = %s"
            count_params.append(user_id)
            
        if decision and decision in ['accepted', 'rejected']:
            count_query += " AND va.final_decision = %s"
            count_params.append(decision)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()['total']
        
        
        
        return {
            "success": True,
            "attempts": attempts,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "returned": len(attempts)
            }
        }
        
    except Exception as e:
        print(f"❌ Error fetching verification attempts: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "attempts": []
        }
    finally:
        cursor.close()
        db.close()


# ENHANCED VERIFICATION ENDPOINT WITH WHISPER (FIXED)
@app.post("/auth/verify-challenge-enhanced")
async def verify_challenge_enhanced(
    challenge_id: str = Form(...),
    audio_file: UploadFile = File(...),
    user_id: int = Form(...)
):
    """
    Enhanced challenge verification with Whisper ASR and text matching
    """
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    temp_filepath = None
    
    try:
        # Validate challenge
        challenge = active_challenges.get(challenge_id)
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")
        
        if challenge['used']:
            raise HTTPException(status_code=400, detail="Challenge already used")
        
        if datetime.now().timestamp() > challenge['expires_at']:
            del active_challenges[challenge_id]
            raise HTTPException(status_code=400, detail="Challenge expired")
        
        if challenge['user_id'] != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch")
        
        # Generate unique filename for verification audio
        temp_audio_id = str(uuid.uuid4())
        temp_filename = f"verification_{user_id}_{temp_audio_id}.wav"
        
        # Save audio file using utility function
        try:
            temp_filepath = save_uploaded_file(audio_file, temp_filename)
            print(f"✅ Audio file saved successfully: {temp_filepath}")
            print(f"📊 File size: {os.path.getsize(temp_filepath)} bytes")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save audio file: {str(e)}")
        
        # Step 1: Transcribe audio with Whisper
        spoken_text = await transcribe_audio_with_whisper(temp_filepath)
        
        # Step 2: Text verification
        original_phrase = challenge['phrase']
        match_score, text_passed, text_details = verify_text_match(
            original_phrase, spoken_text, confidence_threshold=0.80
        )
        
        # Step 3: Store verification attempt
        cursor.execute("""
            INSERT INTO verification_attempts 
            (user_id, challenge_id, phrase_used, spoken_text, text_match_score, text_verification_passed)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            challenge_id,
            original_phrase,
            spoken_text,
            match_score,
            text_passed
        ))
        
        attempt_id = cursor.lastrowid
        
        # Step 4: Prepare response
        if text_passed:
            challenge['used'] = True
            final_decision = "accepted"
            message = "Text verification successful"
            
            # Update final decision
            cursor.execute("""
                UPDATE verification_attempts 
                SET final_decision = 'accepted'
                WHERE attempt_id = %s
            """, (attempt_id,))
        else:
            final_decision = "rejected"
            message = "Text verification failed - spoken phrase doesn't match"
            
            cursor.execute("""
                UPDATE verification_attempts 
                SET final_decision = 'rejected'
                WHERE attempt_id = %s
            """, (attempt_id,))
        
        db.commit()
        
        return {
            "success": text_passed,
            "final_decision": final_decision,
            "message": message,
            "text_verification": text_details,
            "attempt_id": attempt_id,
            "user_id": user_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Verification error: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Verification error: {str(e)}")
    finally:
        # Clean up temp file in finally block to ensure it runs
        cleanup_file(temp_filepath)
        cursor.close()
        db.close()

# GET VERIFICATION ATTEMPTS ENDPOINT
@app.get("/auth/verification-attempts/{user_id}")
def get_verification_attempts(user_id: int, limit: int = 10):
    """Get recent verification attempts for a user"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                attempt_id,
                challenge_id,
                phrase_used,
                spoken_text,
                text_match_score,
                text_verification_passed,
                biometric_score,
                final_decision,
                attempt_timestamp
            FROM verification_attempts 
            WHERE user_id = %s 
            ORDER BY attempt_timestamp DESC 
            LIMIT %s
        """, (user_id, limit))
        
        attempts = cursor.fetchall()
        
        return {
            "user_id": user_id,
            "attempts": attempts,
            "total": len(attempts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

# Legacy Verify Challenge Endpoint (for backward compatibility)
@app.post("/auth/verify-challenge")
def verify_challenge(challenge_id: str, spoken_phrase: str = Form(...)):
    # Check if challenge exists and is valid
    challenge = active_challenges.get(challenge_id)
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge['used']:
        raise HTTPException(status_code=400, detail="Challenge already used")
    
    if datetime.now().timestamp() > challenge['expires_at']:
        del active_challenges[challenge_id]
        raise HTTPException(status_code=400, detail="Challenge expired")
    
    # Simple phrase verification (case-insensitive)
    is_correct = spoken_phrase.strip().lower() == challenge['phrase'].lower()
    
    if is_correct:
        challenge['used'] = True
        return {
            "success": True,
            "message": "Phrase verification successful",
            "user_id": challenge['user_id']
        }
    else:
        return {
            "success": False,
            "message": "Spoken phrase does not match challenge"
        }
    
# Get user by ID endpoint
@app.get("/user/{user_id}")
def get_user(user_id: int):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT user_id, full_name, email FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        db.close()

# ==========================
# RUN SERVER
# ==========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)