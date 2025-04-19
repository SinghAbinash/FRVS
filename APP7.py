import os
import sqlite3
import sys
import cv2
import face_recognition
import time
import requests
from flask import Response, jsonify, url_for, request, redirect
from werkzeug.utils import secure_filename
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
from difflib import SequenceMatcher
from dotenv import load_dotenv
import json
from flask_session import Session
import csv
from datetime import datetime
from threading import Timer
import threading

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import create_voting_room, register_user, record_vote
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
import re
import smtplib
import random
import pickle
import numpy as np
import string
import os
import csv
import time
from datetime import datetime, timedelta
from sklearn.neighbors import KNeighborsClassifier
from win32com.client import Dispatch
from datetime import datetime, timedelta
from pkg_resources import resource_filename
import re
import base64

import bz2
import requests
import sys

# Add these lines after imports
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for development

# Set the path to tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Define allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

from flask_wtf.csrf import CSRFProtect
from flask import Flask
from datetime import datetime, timedelta
from flask_session import Session

# Define reCAPTCHA keys
RECAPTCHA_SITE_KEY = "6Ldr9BwrAAAAAH7lQbGirPpJO3kiAmyZR2nxMNWF"
RECAPTCHA_SECRET_KEY = "6Ldr9BwrAAAAAIoAWQE-wa0T5fL0tcP8xSjHqcL-"

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a strong random key

# Add this after app initialization
app.config.update(
    RECAPTCHA_SITE_KEY=RECAPTCHA_SITE_KEY,
    RECAPTCHA_SECRET_KEY=RECAPTCHA_SECRET_KEY
)

# Update the upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frvs.db')

# Model paths configuration
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')

def ensure_models_dir():
    """Ensure models directory exists"""
    os.makedirs(MODELS_DIR, exist_ok=True)

def get_model_path(model_name):
    """Get full path for a model file"""
    return os.path.join(MODELS_DIR, model_name)

def pose_predictor_model_location():
    """Get path for 68 point face landmarks predictor"""
    model_path = get_model_path("shape_predictor_68_face_landmarks.dat")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Required model file not found: {model_path}\n"
            "Please download from: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
        )
    return model_path

def pose_predictor_five_point_model_location():
    """Get path for 5 point face landmarks predictor"""
    model_path = get_model_path("shape_predictor_5_face_landmarks.dat")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Required model file not found: {model_path}\n"
            "Please download from: http://dlib.net/files/shape_predictor_5_face_landmarks.dat.bz2"
        )
    return model_path

def face_recognition_model_location():
    """Get path for face recognition model"""
    model_path = get_model_path("dlib_face_recognition_resnet_model_v1.dat")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Required model file not found: {model_path}\n"
            "Please download from: http://dlib.net/files/dlib_face_recognition_resnet_model_v1.dat.bz2"
        )
    return model_path

def cnn_face_detector_model_location():
    """Get path for CNN face detector model"""
    model_path = get_model_path("mmod_human_face_detector.dat")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Required model file not found: {model_path}\n"
            "Please download from: http://dlib.net/files/mmod_human_face_detector.dat.bz2"
        )
    return model_path

def download_shape_predictor():
    """Download the shape predictor file if it doesn't exist"""
    import bz2
    import requests
    import os

    predictor_path = "shape_predictor_68_face_landmarks.dat"
    
    if not os.path.exists(predictor_path):
        print("Downloading shape predictor file...")
        url = "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
        
        try:
            # Download the file
            response = requests.get(url, stream=True)
            decompressor = bz2.BZ2Decompressor()
            
            with open(predictor_path, 'wb') as f:
                for data in response.iter_content(100*1024):
                    if data:
                        f.write(decompressor.decompress(data))
            
            print("Shape predictor file downloaded successfully")
            return True
        except Exception as e:
            print(f"Error downloading shape predictor: {str(e)}")
            return False
    return True

# Initialize models directory on startup
ensure_models_dir()

def initialize_webcam(retries=3):
    """Initialize the webcam with retries and proper error handling."""
    for attempt in range(retries):
        try:
            print(f"Attempting to initialize webcam (Attempt {attempt + 1}/{retries})...")
            
            # Release any existing camera instance
            cv2.destroyAllWindows()
            
            # Initialize with DirectShow backend
            video = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            # Set camera properties
            video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            video.set(cv2.CAP_PROP_FPS, 30)
            video.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            # Verify camera is working
            if video.isOpened():
                ret, test_frame = video.read()
                if ret and test_frame is not None:
                    print("Webcam initialized successfully.")
                    return video
            
            time.sleep(1)  # Wait before retry
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            time.sleep(1)
    
    print("Failed to initialize webcam after multiple attempts.")
    return None

def speak(text):
    """Text-to-speech functionality using Windows SAPI."""
    try:
        sapi_voice = Dispatch("SAPI.SpVoice")
        sapi_voice.Speak(text)
    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        flash("Text-to-speech functionality is not available on this system.")

def get_camera():
    """Get or create camera instance"""
    if not hasattr(app, 'camera'):
        app.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        app.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        app.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        app.camera.set(cv2.CAP_PROP_FPS, 30)
    return app.camera

def create_voting_room(election_name, host_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate room ID
        room_id = generate_room_id()
        
        # Get current time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert room with expiration time (2 hours from creation)
        cursor.execute('''
            INSERT INTO voting_rooms 
            (room_id, election_name, host_id, created_time, expiration_time, is_active) 
            VALUES (?, ?, ?, ?, datetime(?, '+2 hours'), 1)
        ''', (room_id, election_name, host_id, current_time, current_time))
        
        conn.commit()
        return room_id
        
    except Exception as e:
        print(f"Error creating voting room: {str(e)}")
        raise
    finally:
        conn.close()

def save_candidate(room_id, name, logo_data):
    """Save candidate information to the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if candidate already exists in this room
        cursor.execute('''
            SELECT COUNT(*) FROM Candidates 
            WHERE room_id = ? AND name = ?
        ''', (room_id, name))
        
        if cursor.fetchone()[0] > 0:
            print(f"Candidate {name} already exists in room {room_id}")
            return False

        # Insert new candidate
        cursor.execute('''
            INSERT INTO Candidates (room_id, name, logo, votes)
            VALUES (?, ?, ?, 0)
        ''', (room_id, name, logo_data))
        
        conn.commit()
        print(f"Successfully saved candidate {name} for room {room_id}")
        return True

    except Exception as e:
        print(f"Error saving candidate: {str(e)}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

room_candidates = {}
expired_rooms = set()
voted_rooms = {}
voted_face_encodings = []  # List to store encodings of voters who have already voted

def generate_room_id():
    """Generate a unique 6-character room ID"""
    while True:
        # Generate a random 6-character string (letters and numbers)
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Check if this ID already exists
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT room_id FROM voting_rooms WHERE room_id = ?', (room_id,))
        exists = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if not exists:
            return room_id

def get_db_connection():
    """Get a database connection with error handling"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise



@app.route('/')
@app.route('/index')
def index():
    
    return render_template('index.html')



@app.route('/host_login', methods=['GET', 'POST'])
def host_login():
    """Handle host login and room creation"""
    if request.method == 'GET':
        return render_template('hostlogin.html')
        
    try:
        host_id = request.form.get('host_id', '').strip()
        election_name = request.form.get('election_name', '').strip()

        # Validate host_id format
        if not re.match("^[A-Za-z0-9]{6,12}$", host_id):
            return jsonify({
                'success': False,
                'message': 'Invalid Host ID format'
            })

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Check if host already has an active room
            cursor.execute('''
                SELECT room_id FROM voting_rooms 
                WHERE host_id = ? AND is_active = 1
            ''', (host_id,))
            
            existing_room = cursor.fetchone()
            if existing_room:
                return jsonify({
                    'success': False,
                    'message': 'You already have an active voting room'
                })

            # Generate room ID and create new room
            room_id = generate_room_id()
            
            cursor.execute('''
                INSERT INTO voting_rooms (room_id, host_id, election_name)
                VALUES (?, ?, ?)
            ''', (room_id, host_id, election_name))
            
            conn.commit()
            
            # Store in session
            session['host_id'] = host_id
            session['room_id'] = room_id
            session['election_name'] = election_name

            return jsonify({
                'success': True,
                'message': 'Room created successfully',
                'redirect_url': url_for('voting_room')
            })

        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({
                'success': False,
                'message': 'Error creating room: Host ID already in use'
            })
        
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Error in host_login: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })

@app.route('/verify_recaptcha', methods=['POST'])
def verify_recaptcha(response):
    """Verify reCAPTCHA response"""
    if not response:
        return False
    
    data = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': response
    }
    
    try:
        r = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5
        )
        result = r.json()
        return result.get('success', False)
    except Exception as e:
        print(f"reCAPTCHA verification error: {e}")
        return False

@app.route('/voting_room', methods=['GET', 'POST'])
def voting_room():
    if 'host_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('host_login'))

    room_id = session.get('room_id')
    host_id = session.get('host_id')

    # For GET requests, fetch candidates from database
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.candidate_id, c.name, cl.logo_data 
                FROM Candidates c 
                LEFT JOIN CandidateLogos cl ON c.candidate_id = cl.candidate_id
                WHERE c.room_id = ?
                ORDER BY c.candidate_id
            ''', (room_id,))
            
            candidates = []
            for row in cursor.fetchall():
                candidates.append({
                    'id': row['candidate_id'],
                    'name': row['name'],
                    'logo': base64.b64encode(row['logo_data']).decode('utf-8') if row['logo_data'] else None
                })
            
            return render_template('votingroom.html',
                                room_id=room_id,
                                host_id=host_id,
                                election_name=session.get('election_name'),
                                candidates=candidates)
        finally:
            cursor.close()
            conn.close()

    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('BEGIN')
                
                # Get existing candidates
                cursor.execute('''
                    SELECT c.candidate_id, c.name, l.logo_data 
                    FROM Candidates c 
                    LEFT JOIN CandidateLogos l ON c.candidate_id = l.candidate_id
                    WHERE c.room_id = ?
                ''', (room_id,))
                existing_candidates = {row['candidate_id']: row for row in cursor.fetchall()}
                updated_candidates = set()
                
                index = 0
                new_candidates = 0
                while f'candidate_name_{index}' in request.form:
                    name = request.form[f'candidate_name_{index}']
                    candidate_id = request.form.get(f'candidate_id_{index}')
                    
                    if candidate_id:  # Existing candidate
                        candidate_id = int(candidate_id)
                        # Update name if changed
                        if name != existing_candidates[candidate_id]['name']:
                            cursor.execute('''
                                UPDATE Candidates 
                                SET name = ? 
                                WHERE candidate_id = ?
                            ''', (name, candidate_id))
                        
                        # Update logo if new one provided
                        if f'candidate_logo_{index}' in request.files:
                            logo_file = request.files[f'candidate_logo_{index}']
                            if logo_file and logo_file.filename:
                                logo_data = logo_file.read()
                                cursor.execute('''
                                    UPDATE CandidateLogos 
                                    SET logo_data = ?, upload_date = CURRENT_TIMESTAMP
                                    WHERE candidate_id = ?
                                ''', (logo_data, candidate_id))
                                
                        updated_candidates.add(candidate_id)
                    else:  # New candidate
                        # Insert new candidate
                        cursor.execute('''
                            INSERT INTO Candidates (room_id, name)
                            VALUES (?, ?)
                        ''', (room_id, name))
                        
                        new_candidate_id = cursor.lastrowid
                        
                        # Handle logo for new candidate
                        if f'candidate_logo_{index}' in request.files:
                            logo_file = request.files[f'candidate_logo_{index}']
                            if logo_file and logo_file.filename:
                                logo_data = logo_file.read()
                                cursor.execute('''
                                    INSERT INTO CandidateLogos (candidate_id, logo_data)
                                    VALUES (?, ?)
                                ''', (new_candidate_id, logo_data))
                        new_candidates += 1
                    
                    index += 1

                conn.commit()
                
                message = 'Candidates updated successfully'
                if new_candidates > 0:
                    message = f'{new_candidates} new candidate(s) added successfully'

                return jsonify({
                    'success': True,
                    'message': message
                })

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            print(f"Error in voting_room: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

@app.route('/flash_message')
def flash_message():
    message = request.args.get('message')
    category = request.args.get('category', 'message')
    flash(message, category)
    return redirect(url_for('index'))

@app.route('/validate_room', methods=['POST'])
def validate_room():
    data = request.get_json()
    room_id = data.get('room_id')
    
    if room_id not in room_candidates:
        return jsonify({'message': 'Invalid Room ID.'}), 400
    if room_id in expired_rooms:
        return jsonify({'message': 'This Room ID has expired.'}), 400
    
    return jsonify({'message': 'Room ID is valid.'}), 200



@app.route('/vote/<room_id>')
def vote(room_id):
    if 'user_id' not in session:
        flash('Please complete voter registration first', 'error')
        return redirect(url_for('voter_login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Updated query to use created_at instead of created_time
        cursor.execute('''
            SELECT election_name, created_at, 
                   datetime(created_at, '+2 hours') as expiration_time 
            FROM voting_rooms 
            WHERE room_id = ? AND is_active = 1
        ''', (room_id,))
        
        election = cursor.fetchone()
        
        if not election:
            flash('Invalid or expired voting room', 'error')
            return redirect(url_for('index'))
        
        # Get candidates with their logos
        cursor.execute('''
            SELECT c.candidate_id, c.name, cl.logo_data as logo
            FROM Candidates c
            LEFT JOIN CandidateLogos cl ON c.candidate_id = cl.candidate_id
            WHERE c.room_id = ?
        ''', (room_id,))
        
        candidates_raw = cursor.fetchall()
        
        # Process candidates data
        candidates = []
        for candidate in candidates_raw:
            candidate_dict = dict(candidate)
            logo_b64 = base64.b64encode(candidate_dict['logo']).decode('utf-8') if candidate_dict['logo'] else None
            
            candidates.append({
                'candidate_id': candidate_dict['candidate_id'],
                'name': candidate_dict['name'],
                'logo': logo_b64
            })
        
        return render_template('vote.html',
                             room_id=room_id,
                             election_name=election['election_name'],
                             candidates=candidates,
                             created_at=election['created_at'],
                             expiration_time=election['expiration_time'])
                             
    except Exception as e:
        print(f"Error in vote route: {str(e)}")
        flash(f'Error loading voting page: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

@app.template_filter('b64encode')
def b64encode_filter(s):
    return base64.b64encode(s).decode()

@app.route('/voter_login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip().upper()
        room_id = request.form.get('room_id', '').strip()
        aadhar = request.form.get('aadhar', '').strip()

        # Input validation
        if not name or not re.match(r'^[A-Z\s]+$', name):
            flash("Please enter a valid name (uppercase letters and spaces only)", "error")
            return redirect(url_for('voter_login'))

        if not room_id or not re.match(r'^[A-Z0-9]+$', room_id):
            flash("Please enter a valid Room ID (digits or capital letters only)", "error")
            return redirect(url_for('voter_login'))

        # Validate Aadhar number - exactly 12 digits
        if not aadhar or not re.match(r'^\d{12}$', aadhar):
            flash("Please enter exactly 12 digits for Aadhar number", "error")
            return redirect(url_for('voter_login'))

        # Check if room exists and is active
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM VotingRooms WHERE room_id = ? AND is_active = 1', (room_id,))
            room = cursor.fetchone()
            
            if not room:
                flash("Invalid or expired Room ID", "error")
                return redirect(url_for('voter_login'))

            # Store data in session for face recognition step
            session['name'] = name
            session['aadhar'] = aadhar
            session['room_id'] = room_id

            # Redirect to face capture page
            return redirect(url_for('add_faces'))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('voter_login'))
        finally:
            conn.close()

    # GET request - display the login form
    return render_template('voterlogin.html')



    
@app.route('/cast_vote/<room_id>', methods=['POST'])
def cast_vote(room_id):
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'message': 'Please login first'
        })

    try:
        candidate_id = request.form.get('candidate_id')
        user_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('BEGIN')
            
            # Check if user has already voted
            cursor.execute('''
                SELECT COUNT(*) FROM Votes 
                WHERE voter_id = ? AND room_id = ?
            ''', (user_id, room_id))
            
            if cursor.fetchone()[0] > 0:
                return jsonify({
                    'success': False,
                    'message': 'You have already voted in this election'
                })

            # Get voter details
            cursor.execute('''
                SELECT name, unique_id_number 
                FROM Users 
                WHERE user_id = ?
            ''', (user_id,))
            voter = cursor.fetchone()

            # Get candidate and election details
            cursor.execute('''
                SELECT c.name as candidate_name, 
                       vr.election_name 
                FROM Candidates c
                JOIN voting_rooms vr ON c.room_id = vr.room_id
                WHERE c.candidate_id = ?
            ''', (candidate_id,))
            details = cursor.fetchone()

            # Prepare vote data
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            vote_data = [
                timestamp,           # Timestamp
                room_id,            # Room ID
                details['election_name'],  # Election Name
                user_id,            # Voter ID
                voter['name'],      # Voter Name
                voter['unique_id_number'],  # Voter Aadhar
                candidate_id,       # Candidate ID
                details['candidate_name']   # Candidate Name
            ]

            # Record vote in database
            cursor.execute('''
                INSERT INTO Votes (room_id, candidate_id, voter_id)
                VALUES (?, ?, ?)
            ''', (room_id, candidate_id, user_id))

            # Write to CSV
            if not write_vote_to_csv(vote_data):
                raise Exception("Failed to write vote to CSV")

            cursor.execute('COMMIT')
            
            # Clear voting session
            session.pop('user_id', None)
            session.pop('face_verified', None)

            return jsonify({
                'success': True,
                'message': 'Your vote has been recorded successfully!',
                'redirect': url_for('votecasted')
            })

        except Exception as e:
            cursor.execute('ROLLBACK')
            print(f"Error recording vote: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error recording vote. Please try again.'
            })
            
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Error in cast_vote: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your vote'
        })

@app.route('/votecasted')
def votecasted():
    return render_template('votecasted.html')

def save_voted_face(face_encoding):
    """Save a face encoding of someone who has voted to prevent duplicate voting."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Convert numpy array to binary for storage
        encoding_binary = pickle.dumps(face_encoding)
        cursor.execute('INSERT INTO VotedFaces (face_encoding) VALUES (?)', (encoding_binary,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving voted face: {e}")
        return False
    finally:
        conn.close()

def cast_vote():
    try:
        # Connect to database and get voted faces
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT face_encoding FROM VotedFaces')
        voted_face_encodings = [pickle.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        
        # Load the pre-trained KNN model
        knn_model_path = 'data/knn_model.pkl'
        if not os.path.exists(knn_model_path) or os.path.getsize(knn_model_path) == 0:
            flash("KNN model not found or is corrupted. Please train the model first.")
            return redirect(url_for('index'))
        try:
            with open(knn_model_path, 'rb') as model_file:
                knn = pickle.load(model_file)
        except (pickle.UnpicklingError, EOFError):
            flash("KNN model file is corrupted. Please retrain the model.")
            return redirect(url_for('index'))

        # Initialize webcam
        video = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not video.isOpened():
            flash("Webcam not accessible. Ensure it's connected and not in use by other applications.")
            return redirect(url_for('vote', room_id=request.form.get('room_id')))

        # Attempt to capture frame
        ret, frame = video.read()
        if not ret or frame is None:
            flash("Failed to receive video feed. Check camera permissions and functionality.")
            return redirect(url_for('vote', room_id=request.form.get('room_id')))

        # Convert the frame to RGB (required by face_recognition)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face locations and encodings
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        if len(face_encodings) == 0:
            flash("No face detected. Please ensure your face is clearly visible to the camera.")
            return redirect(url_for('vote', room_id=request.form.get('room_id')))

        # Draw rectangle around face and add text
        for (top, right, bottom, left) in face_locations:
            # Draw rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Add text overlays
        cv2.putText(frame, "Verifying Faces", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Compare the detected face with the KNN model and check if it has already voted
        voter_status = "New Voter"
        for face_encoding in face_encodings:
            # Check if the face has already voted
            if voted_face_encodings:
                matches = face_recognition.compare_faces(voted_face_encodings, face_encoding, tolerance=0.6)
                if True in matches:
                    voter_status = "Already Voted"
                    speak("YOU HAVE ALREADY VOTED")
                    flash("You have already voted with this face.")
                    return redirect(url_for('index'))

            # Retrieve data from session
            name = session.get('name', '').strip().upper()
            aadhar = session.get('aadhar', '').strip()
            room_id = session.get('room_id', '').strip()
            vote_choice = request.form.get('vote')

            # Validate input
            if not name or not aadhar or not room_id or not vote_choice:
                flash("Invalid input. Please try again.")
                return redirect(url_for('vote', room_id=room_id))

            # Check if voter has already voted
            vote_status = check_if_exists(name, aadhar, room_id)
            if vote_status == "already_voted":
                voter_status = "Already Voted"
                speak("YOU HAVE ALREADY VOTED")
                flash("You have already voted with this name and Aadhar number")
                return redirect(url_for('index'))

            # Save voted face in database
            if not save_voted_face(face_encoding):
                flash("Failed to record vote")
                return redirect(url_for('index'))
            
            # Record the vote
            ts = time.time()
            date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
            timestamp = datetime.fromtimestamp(ts).strftime("%H:%M-%S")
            election_name = session.get('election_name', 'Election')
            votes_file = f"{election_name}_Votes.csv"

            file_exists = os.path.exists(votes_file)
            with open(votes_file, "a", newline='') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(["Name", "Aadhar", "Vote", "Date", "Timestamp", "Room ID"])
                attendance = [name, aadhar, vote_choice, date, timestamp, room_id]
                writer.writerow(attendance)

            # Announce successful face recognition
            speak("FACE RECOGNITION SUCCESSFUL")
            speak("YOUR VOTE HAS BEEN RECORDED")
            flash(f"Vote casted for {vote_choice}")

        # Update the frame in the global variable for the video feed
        cv2.putText(frame, voter_status, (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        app.frames = buffer.tobytes()

        

        return redirect(url_for('votecasted'))

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for('vote', room_id=request.form.get('room_id')))

    finally:
        if video and video.isOpened():
            video.release()
        cv2.destroyAllWindows()

def save_face_encodings(user_id, face_encodings):
    """Save face encodings for a user in the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for encoding in face_encodings:
            # Convert numpy array to binary for storage
            encoding_binary = pickle.dumps(encoding)
            cursor.execute('INSERT INTO FaceEncodings (user_id, encoding) VALUES (?, ?)',
                         (user_id, encoding_binary))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving face encodings: {e}")
        return False
    finally:
        conn.close()

        
def get_all_face_encodings():
    """Retrieve all face encodings and corresponding names from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.name, f.encoding 
            FROM FaceEncodings f 
            JOIN Users u ON f.user_id = u.user_id
        ''')
        results = cursor.fetchall()
        names = []
        encodings = []
        for name, encoding_binary in results:
            names.append(name)
            encodings.append(pickle.loads(encoding_binary))
        return encodings, names
    except Exception as e:
        print(f"Error retrieving face encodings: {e}")
        return [], []
    finally:
        conn.close()

def load_pickle_file(file_path, default_value):
    """Safely load a pickle file. If the file is empty or corrupted, reinitialize it."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        # If the file doesn't exist or is empty, initialize it with the default value
        with open(file_path, 'wb') as f:
            pickle.dump(default_value, f)
        return default_value
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except (pickle.UnpicklingError, EOFError):
        # If the file is corrupted, reinitialize it
        flash(f"File {file_path} is corrupted or empty. Reinitializing it.")
        with open(file_path, 'wb') as f:
            pickle.dump(default_value, f)
        return default_value



@app.route('/join_room', methods=['POST'])
def join_room():
    if request.method == 'POST':
        try:
            room_id = request.form.get('room_id')
            host_id = request.form.get('host_id')

            if not room_id or not host_id:
                return jsonify({
                    'success': False,
                    'message': 'Room ID and Host ID are required'
                }), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            # First check if room exists and is active
            cursor.execute('''
                SELECT r.room_id, r.host_id, r.election_name, r.is_active
                FROM voting_rooms r
                WHERE r.room_id = ? AND r.host_id = ? AND r.is_active = 1
            ''', (room_id, host_id))
            
            room = cursor.fetchone()
            
            if not room:
                return jsonify({
                    'success': False,
                    'message': 'Invalid Room ID or Host ID'
                }), 404

            # Store only essential data in session
            session['room_id'] = room_id
            session['host_id'] = host_id
            session['election_name'] = room['election_name']

            return jsonify({
                'success': True,
                'message': 'Room joined successfully',
                'redirect': url_for('voting_room')
            })

        except Exception as e:
            print(f"Error in join_room: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'An error occurred while joining the room'
            }), 500
        finally:
            cursor.close()
            conn.close()

@app.route('/host_room_login', methods=['POST'])
def get_room_by_id(room_id):
    """Get room information from database by room ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT room_id, election_name, created_by as host_id, folder_id
            FROM VotingRooms 
            WHERE room_id = ? AND is_active = 1
        ''', (room_id,))
        room = cursor.fetchone()
        return dict(room) if room else None
    except Exception as e:
        print(f"Error getting room: {str(e)}")
        return None
    finally:
        conn.close()

def host_room_login():
    room_id = request.form.get('room_id')
    host_gmail = request.form.get('host_gmail')
    
    if not room_id or not host_gmail:
        flash('Please provide both Room ID and Gmail', 'error')
        return redirect(url_for('index'))
    
    # Verify room exists and belongs to host
    room = get_room_by_id(room_id)
    if not room:
        flash('Invalid Room ID', 'error')
        return redirect(url_for('index'))
    
    if room['host_id'] != host_gmail:
        flash('You are not authorized to access this room', 'error')
        return redirect(url_for('index'))
    
    # Store room data in session
    session['room_id'] = room_id
    session['election_name'] = room['election_name']
    session['host_id'] = host_gmail
    session['folder_id'] = room['folder_id']
    
    return redirect(url_for('voting_room'))

def register_user(name, aadhar, room_id):
    """Register a new user without face encoding."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Users (name, unique_id_number, room_id)
            VALUES (?, ?, ?)
        ''', (name, aadhar, room_id))
        
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except Exception as e:
        print(f"Error registering user: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_aadhar_exists(aadhar):
    """Check if an Aadhar number already exists in the database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM Users WHERE unique_id_number = ?', (aadhar,))
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        conn.close()

def save_user_data(name, aadhar, room_id, face_encoding):
    """Save user data and face encoding to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = None
    
    try:
        # First check if user already exists
        cursor.execute('SELECT user_id FROM Users WHERE unique_id_number = ?', (aadhar,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Check if user is already registered for this room
            cursor.execute('''
                SELECT * FROM Users 
                WHERE unique_id_number = ? AND room_id = ?
            ''', (aadhar, room_id))
            
            if cursor.fetchone():
                raise Exception("You have already registered for this voting room")
            else:
                user_id = existing_user[0]
                cursor.execute('''
                    UPDATE Users 
                    SET room_id = ? 
                    WHERE user_id = ?
                ''', (room_id, user_id))
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO Users (name, unique_id_number, room_id)
                VALUES (?, ?, ?)
            ''', (name, aadhar, room_id))
            user_id = cursor.lastrowid

        # Save face encoding
        if face_encoding is not None:
            # Convert face encoding to bytes directly
            face_encoding_bytes = face_encoding.tobytes()
            
            cursor.execute('''
                INSERT INTO FaceEncodings (user_id, face_encoding)
                VALUES (?, ?)
            ''', (user_id, face_encoding_bytes))

        conn.commit()
        print(f"Successfully saved user with ID: {user_id}")
        return user_id

    except Exception as e:
        conn.rollback()
        print(f"Error in save_user_data: {str(e)}")
        raise

    finally:
        cursor.close()
        conn.close()

def save_face_encoding(user_id, face_encoding):
    """Save face encoding for a user"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO FaceEncodings (user_id, face_encoding)
            VALUES (?, ?)
        ''', (user_id, pickle.dumps(face_encoding)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving face encoding: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_face_storage(user_id):
    """Verify that face encoding was stored correctly"""
    if user_id is None:
        print("No user_id provided for verification")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT face_encoding 
            FROM FaceEncodings 
            WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            try:
                # Convert bytes back to numpy array
                face_encoding = np.frombuffer(result[0], dtype=np.float64)
                
                # Reshape the array to match face encoding dimensions
                face_encoding = face_encoding.reshape(-1)
                
                print(f"Retrieved face encoding of type: {type(face_encoding)}")
                print(f"Retrieved face encoding shape: {face_encoding.shape}")
                
                if isinstance(face_encoding, np.ndarray) and face_encoding.shape[0] == 128:
                    return True
                    
                print("Invalid face encoding shape or type")
                return False
                
            except Exception as e:
                print(f"Error loading face encoding: {str(e)}")
                return False
        else:
            print(f"No face encoding found for user_id: {user_id}")
            return False
            
    except Exception as e:
        print(f"Error verifying face storage: {str(e)}")
        return False
    finally:
        conn.close()

@app.teardown_appcontext
def cleanup(exception=None):
    """Cleanup camera resources"""
    if hasattr(app, 'camera'):
        app.camera.release()
    cv2.destroyAllWindows()

# Add these error handlers
@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html',
        error_code="400",
        error_message="Bad Request - The CSRF token is missing or invalid.",
        show_additional_info=True,
        error_id=generate_error_id()
    ), 400

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html',
        error_code="404",
        error_message="Page Not Found - The requested resource could not be found.",
        show_additional_info=False
    ), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('error.html',
        error_code="500",
        error_message="Internal Server Error - Something went wrong on our end.",
        show_additional_info=True,
        error_id=generate_error_id()
    ), 500

from sqlite3 import IntegrityError

@app.errorhandler(IntegrityError)
def handle_db_error(error):
    if "UNIQUE constraint failed: Users.unique_id_number" in str(error):
        return render_template('error.html',
            error_code="409",  # Conflict status code
            error_message="This Aadhar number has already been registered for voting.",
            show_additional_info=True,
            error_type="database",
            error_id=generate_error_id()
        ), 409
    return render_template('error.html',
        error_code="500",
        error_message="A database error occurred. Please try again.",
        show_additional_info=True,
        error_type="database",
        error_id=generate_error_id()
    ), 500

def generate_error_id():
    return f"ERR-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

# Simplify the setup_storage function
def setup_storage():
    """Create upload directory in project folder if it doesn't exist"""
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        raise Exception(f"Error creating upload directory: {e}")



def process_id_card_image(image_data):
    """Process ID card image to extract face and text"""
    try:
        print("Starting image processing...")
        
        # Convert image data to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("Failed to decode image")
            return None, None, "Failed to decode image data"
        
        print(f"Image shape: {img.shape}")
        
        # Convert to RGB for face_recognition
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_img)
        print(f"Found {len(face_locations)} faces")
        
        if not face_locations:
            return None, None, "No face detected on ID card"
            
        # Get face encoding
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        if not face_encodings:
            return None, None, "Could not encode face from ID card"
        
        # Extract text using OCR
        text = pytesseract.image_to_string(Image.fromarray(rgb_img))
        print(f"Extracted text: {text}")
        
        return face_encodings[0], text, None
        
    except Exception as e:
        print(f"Error in process_id_card_image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, f"Error processing image: {str(e)}"

def validate_id_card_text(extracted_text, input_name, input_aadhar):
    """Validate extracted text against input data"""
    try:
        # Clean and normalize the texts
        extracted_text = extracted_text.upper()
        input_name = input_name.upper()
        
        # Remove common OCR errors and special characters
        extracted_text = re.sub(r'[^A-Z0-9\s]', '', extracted_text)
        input_name = re.sub(r'[^A-Z\s]', '', input_name)
        
        print(f"Cleaned Extracted Text: {extracted_text}")
        print(f"Cleaned Input Name: {input_name}")
        
        # Check for name match using fuzzy matching
        name_parts = input_name.split()
        name_match = False
        for part in name_parts:
            if len(part) > 2 and part in extracted_text:  # Only check parts longer than 2 characters
                name_match = True
                break
        
        # Check for Aadhar number match - remove spaces from both
        aadhar_match = False
        clean_input_aadhar = input_aadhar.replace(" ", "")
        clean_extracted_text = extracted_text.replace(" ", "")
        
        # Find any 12-digit number in the text
        aadhar_numbers = re.findall(r'\d{12}', clean_extracted_text)
        if clean_input_aadhar in aadhar_numbers:
            aadhar_match = True
            
        print(f"Name Match: {name_match}, Aadhar Match: {aadhar_match}")
        
        # Return True if EITHER name OR Aadhar matches
        return name_match or aadhar_match
        
    except Exception as e:
        print(f"Validation Error: {str(e)}")
        return False

@app.route('/process_id_card', methods=['POST'])
def process_id_card():
    try:
        if 'id_card' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
            
        file = request.files['id_card']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'})
            
        # Read the file data
        file_data = file.read()
        
        # Get form data
        input_name = request.form.get('name', '').strip().upper()
        input_aadhar = request.form.get('aadhar', '').strip()
        room_id = request.form.get('room_id', '').strip()
        
        if not input_name or not input_aadhar or not room_id:
            return jsonify({
                'success': False, 
                'error': 'Missing required form data'
            })
        
        # Process the image
        face_encoding, extracted_text, error = process_id_card_image(file_data)
        if error:
            return jsonify({'success': False, 'error': error})
            
        # Validate extracted text against input data
        validation_result = validate_id_card_text(extracted_text, input_name, input_aadhar)
        if not validation_result:
            return jsonify({
                'success': False, 
                'error': 'Neither name nor Aadhar number matched with the ID card'
            })
            
        try:
            # Store user data and face encoding - returns user_id
            user_id = save_user_data(input_name, input_aadhar, room_id, face_encoding)
            
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save user data'
                })
                
            # Verify storage
            if verify_face_storage(user_id):
                print("Face encoding verified successfully")
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to verify face encoding storage'
                })
                
            # Store session data
            session['face_verified'] = True
            session['user_id'] = user_id
            session['name'] = input_name
            session['aadhar'] = input_aadhar
            session['room_id'] = room_id
            
            # Redirect to vote page
            return jsonify({
                'success': True,
                'redirect': url_for('vote', room_id=room_id)
            })
            
        except Exception as e:
            print(f"Error saving user data: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e) if "already registered" in str(e) else 'Error saving user data'
            })
            
    except Exception as e:
        print(f"Error in process_id_card: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred while processing the ID card: {str(e)}'
        })

def ensure_database_exists():
    """Ensure database exists and all tables are created"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if Users table exists
        cursor.execute("""
            SELECT count(name) FROM sqlite_master 
            WHERE type='table' AND name='Users'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("Creating database tables...")
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    unique_id_number TEXT UNIQUE NOT NULL,
                    room_id TEXT NOT NULL,
                    registration_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS FaceEncodings (
                    encoding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    face_encoding BLOB NOT NULL,
                    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES Users(user_id)
                );
            ''')
            conn.commit()
            print("Database tables created successfully")
        
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise
    finally:
        conn.close()

# Add this route after your other route definitions

@app.route('/video_feed')
def video_feed():
    """Generate live video feed."""
    def generate_frames():
        video = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        try:
            # Optimize video capture
            video.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            video.set(cv2.CAP_PROP_FPS, 30)
            
            while True:
                success, frame = video.read()
                if not success:
                    break
                    
                # Convert frame to RGB for face detection
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces
                face_locations = face_recognition.face_locations(rgb_frame)
                
                # Draw rectangles around faces
                for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Convert frame to JPEG format
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Yield the frame in bytes
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                       
        except Exception as e:
            print(f"Video feed error: {str(e)}")
        finally:
            video.release()
            cv2.destroyAllWindows()
            
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def check_if_exists(name, aadhar, room_id):
    """Check if a voter has already voted in a specific room."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM Users 
            WHERE name = ? AND unique_id_number = ? AND room_id = ?
        ''', (name, aadhar, room_id))
        count = cursor.fetchone()[0]
        return "already_voted" if count > 0 else "new_voter"
    except Exception as e:
        print(f"Error checking voter existence: {str(e)}")
        return "error"
    finally:
        conn.close()

def save_host_login(host_gmail, election_name):
    """Save host login details to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO HostLogins (host_gmail, election_name)
            VALUES (?, ?)
        ''', (host_gmail, election_name))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error saving host login: {str(e)}")
        return None
    finally:
        conn.close()

def get_host_login(host_gmail):
    """Get the most recent active login for a host"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT election_name, host_gmail
            FROM HostLogins
            WHERE host_gmail = ? AND is_active = 1
            ORDER BY login_timestamp DESC
            LIMIT 1
        ''', (host_gmail,))
        result = cursor.fetchone()
        return result if result else None
    except Exception as e:
        print(f"Error getting host login: {str(e)}")
        return None
    finally:
        conn.close()

# Add security headers
@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Enable CSRF protection
csrf = CSRFProtect(app)

@app.before_request
def check_session():
    if request.endpoint and request.endpoint != 'static':
        # Exclude static files and routes that don't require host session
        excluded_routes = ['host_login', 'index', 'voter_login', 'vote', 'process_id_card', 'cast_vote']
        if request.endpoint not in excluded_routes:
            if 'host_id' not in session:
                flash('Your session has expired. Please login again.', 'error')
                return redirect(url_for('host_login'))
            

def write_vote_to_csv(vote_data):
    """Helper function to write vote data to room-specific CSV file"""
    try:
        # Get current working directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        votes_dir = os.path.join(base_dir, 'votes')
        os.makedirs(votes_dir, exist_ok=True)
        
        room_id = vote_data[1]  # room_id is second element in vote_data
        csv_file = os.path.join(votes_dir, f"{room_id}_votes.csv")
        
        # Debug print
        print(f"Writing vote to: {csv_file}")
        print(f"Vote data: {vote_data}")
        
        file_exists = os.path.exists(csv_file)
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'Timestamp',
                    'Room ID',
                    'Election Name',
                    'Voter ID',
                    'Voter Name',
                    'Voter Aadhar',
                    'Candidate ID',
                    'Candidate Name'
                ])
            writer.writerow(vote_data)
            
        print(f"Vote successfully recorded in {csv_file}")
        return True
        
    except Exception as e:
        print(f"Error writing to CSV: {str(e)}")
        print(f"Vote data was: {vote_data}")
        return False


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create or update voting_rooms table (keep existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voting_rooms (
            room_id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            election_name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expired_at DATETIME DEFAULT NULL,
            expiration_time DATETIME DEFAULT NULL
        )
    ''')

    # Create or update user_sessions table (keep existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            room_id TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES voting_rooms (room_id)
        )
    ''')

    # Update candidates table (keep existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Candidates (
            candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES voting_rooms (room_id)
        )
    ''')

    # Update CandidateLogos table (keep existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS CandidateLogos (
            logo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            logo_data BLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES Candidates(candidate_id)
        )
    ''')

    # Add FaceEncodings table with capture_timestamp
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FaceEncodings (
            encoding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            face_encoding BLOB NOT NULL,
            capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully")



@app.route('/expire_room', methods=['POST'])
def expire_room():
    try:
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Invalid request format'
            }), 400

        data = request.get_json()
        room_id = data.get('room_id')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('BEGIN')
            
            # First check if room exists and is active
            cursor.execute('''
                SELECT room_id, host_id, is_active 
                FROM voting_rooms 
                WHERE room_id = ?
            ''', (room_id,))
            
            room = cursor.fetchone()
            if not room:
                return jsonify({
                    'success': False,
                    'message': 'Room not found'
                }), 404

            if not room['is_active']:
                return jsonify({
                    'success': False,
                    'message': 'Room is already terminated'
                }), 400

            # Delete candidate logos first
            cursor.execute('''
                DELETE FROM CandidateLogos 
                WHERE candidate_id IN (
                    SELECT candidate_id 
                    FROM Candidates 
                    WHERE room_id = ?
                )
            ''', (room_id,))

            # Delete candidates
            cursor.execute('DELETE FROM Candidates WHERE room_id = ?', (room_id,))

            # Update room status and clear host_id constraint
            cursor.execute('''
                UPDATE voting_rooms 
                SET is_active = 0,
                    expired_at = CURRENT_TIMESTAMP,
                    host_id = host_id || '_expired_' || strftime('%s', 'now')
                WHERE room_id = ?
            ''', (room_id,))

            cursor.execute('COMMIT')
            
            return jsonify({
                'success': True,
                'message': 'Room terminated successfully. You can now use both the Room ID and Host ID for a new election.',
                'redirect': url_for('index')
            })

        except Exception as e:
            cursor.execute('ROLLBACK')
            raise e
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Error in expire_room: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while terminating the room'
        }), 500


@app.route('/results/<room_id>')
def results(room_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get election details
        cursor.execute('''
            SELECT election_name
            FROM voting_rooms
            WHERE room_id = ?
        ''', (room_id,))
        election = cursor.fetchone()

        # Get candidates with vote counts
        cursor.execute('''
            SELECT c.candidate_id, c.name, cl.logo_data,
                   COUNT(v.voter_id) as vote_count
            FROM Candidates c
            LEFT JOIN CandidateLogos cl ON c.candidate_id = cl.candidate_id
            LEFT JOIN Votes v ON c.candidate_id = v.candidate_id
            WHERE c.room_id = ?
            GROUP BY c.candidate_id
        ''', (room_id,))
        
        candidates_data = cursor.fetchall()
        
        # Calculate total votes
        total_votes = sum(c['vote_count'] for c in candidates_data)
        
        candidates = []
        for candidate in candidates_data:
            percentage = (candidate['vote_count'] / total_votes * 100) if total_votes > 0 else 0
            candidates.append({
                'name': candidate['name'],
                'logo': base64.b64encode(candidate['logo_data']).decode('utf-8') if candidate['logo_data'] else None,
                'votes': candidate['vote_count'],
                'percentage': percentage
            })

        # Read votes from CSV with proper column mapping
        votes = []
        csv_path = os.path.join(app.root_path, 'votes', f'{room_id}_votes.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                for row in csv_reader:
                    votes.append({
                        'timestamp': row['Timestamp'],
                        'voter_name': row['Voter Name'],
                        'voter_id': row['Voter ID'],
                        'candidate_name': row['Candidate Name']
                    })

        return render_template('results.html',
                             room_id=room_id,
                             election_name=election['election_name'],
                             candidates=candidates,
                             votes=votes)

    except Exception as e:
        print(f"Error reading votes CSV: {str(e)}")
        flash('Error loading voting records', 'error')
        return redirect(url_for('voting_room'))
    finally:
        cursor.close()
        conn.close()




@app.route('/verify_face', methods=['POST'])
def verify_face():
    try:
        data = request.get_json()
        image_data = data['image_data']
        user_id = data['user_id']
        previous_face_location = data.get('previous_location', None)  # Track face movement
        
        # Convert base64 image to OpenCV format
        encoded_data = image_data.split(',')[1]
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Get stored face encoding
        stored_encoding = None
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT face_encoding 
                FROM FaceEncodings 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if result and result[0]:
                stored_encoding = np.frombuffer(result[0], dtype=np.float64).reshape(-1)
        finally:
            cursor.close()
            conn.close()

        if stored_encoding is None:
            return jsonify({
                'success': False,
                'message': 'No stored face encoding found',
                'redirect': url_for('index'),
                'closeVideo': True
            })

        # Convert frame to RGB for face_recognition
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, faces)

        if not faces:
            return jsonify({
                'success': False,
                'message': 'No face detected',
                'closeVideo': False
            })

        # Get current face location (using the first face detected)
        current_face_location = faces[0]  # (top, right, bottom, left)
        
        # Calculate face center
        face_center = (
            (current_face_location[3] + current_face_location[1]) // 2,  # x coordinate
            (current_face_location[0] + current_face_location[2]) // 2   # y coordinate
        )

        # Initialize movement detection variables
        movement_detected = False
        movement_threshold = 30  # Adjust this value based on testing
        movement_text = "Move your face slightly"

        if previous_face_location:
            # Convert previous_face_location from string back to tuple
            prev_loc = eval(previous_face_location)
            prev_center = (
                (prev_loc[3] + prev_loc[1]) // 2,
                (prev_loc[0] + prev_loc[2]) // 2
            )
            
            # Calculate movement distance
            movement_distance = np.sqrt(
                (face_center[0] - prev_center[0])**2 + 
                (face_center[1] - prev_center[1])**2
            )
            
            if movement_distance > movement_threshold:
                movement_detected = True
                movement_text = "Movement Detected!"

        match_found = False
        for face_encoding, face_location in zip(encodings, faces):
            # Compare with stored encoding
            result = face_recognition.compare_faces([stored_encoding], face_encoding, tolerance=0.6)
            
            # Get face location coordinates
            top, right, bottom, left = face_location
            
            if result[0] and movement_detected:
                match_found = True
                # Draw green rectangle for match
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, f"MATCHED - {movement_text}", (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                # Draw red rectangle for non-match or no movement
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, f"NOT VERIFIED - {movement_text}", (left, top - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

                # Draw movement guide arrows
                center_x = (left + right) // 2
                center_y = (top + bottom) // 2
                arrow_length = 50
                cv2.arrowedLine(frame, (center_x, center_y), (center_x + arrow_length, center_y), 
                               (255, 255, 255), 2)
                cv2.arrowedLine(frame, (center_x, center_y), (center_x - arrow_length, center_y), 
                               (255, 255, 255), 2)

        # Convert processed frame back to base64
        _, buffer = cv2.imencode('.jpg', frame)
        processed_image = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'success': True,
            'message': 'Face verified successfully' if match_found else 'Keep moving face slightly',
            'matched': match_found,
            'movement_detected': movement_detected,
            'processedImage': f'data:image/jpeg;base64,{processed_image}',
            'previous_location': str(current_face_location),  # Store current location for next request
            'closeVideo': match_found and movement_detected
        })
            
    except Exception as e:
        print(f"Error in face verification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Face verification error',
            'redirect': url_for('index'),
            'closeVideo': True
        }), 500


# Add this to your app initialization
if __name__ == '__main__':
    try:
        # Create necessary directories
        os.makedirs('data', exist_ok=True)
        os.makedirs('models', exist_ok=True)
        
        # Download shape predictor if needed
        if not download_shape_predictor():
            print("Error: Could not download required shape predictor file")
            sys.exit(1)
        
        # Import and initialize database
        from database import init_db
        init_db()
        
        # Verify database initialization
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
            if not cursor.fetchone():
                print("Warning: Database tables not found. Reinitializing...")
                init_db()
        finally:
            conn.close()
            
        app.run(debug=True)
    except Exception as e:
        print(f"Startup error: {str(e)}")
        raise
    finally:
        if 'cleanup' in globals():
            cleanup()


