import sqlite3
import sqlite3 as sql
import os
import pickle
from datetime import datetime, timedelta

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frvs.db')

def get_db_connection():
    """Create a database connection and return the connection object."""
    conn = sql.connect(DATABASE_PATH)
    conn.row_factory = sql.Row
    return conn

def init_db():
    """Initialize the database with all required tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create or update voting_rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voting_rooms (
                room_id TEXT PRIMARY KEY,
                host_id TEXT NOT NULL,
                election_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expired_at DATETIME DEFAULT NULL,
                UNIQUE(host_id, is_active)
            )
        ''')

        # Create or update user_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                room_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES voting_rooms (room_id)
            )
        ''')

        # Create Candidates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES voting_rooms (room_id)
            )
        ''')

        # Create CandidateLogos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS CandidateLogos (
                logo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER NOT NULL,
                logo_data BLOB,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES Candidates(candidate_id)
            )
        ''')

        # Create or update Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                unique_id_number TEXT UNIQUE NOT NULL,
                room_id TEXT NOT NULL,
                registration_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES voting_rooms(room_id)
            )
        ''')

        # Create or update Votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Votes (
                vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                candidate_id INTEGER NOT NULL,
                voter_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES voting_rooms(room_id),
                FOREIGN KEY (candidate_id) REFERENCES Candidates(candidate_id),
                FOREIGN KEY (voter_id) REFERENCES Users(user_id)
            )
        ''')

        # Create or update FaceEncodings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS FaceEncodings (
                encoding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                face_encoding BLOB NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            )
        ''')

        # Add AllowedVoters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS AllowedVoters (
                allowed_voter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                mobile_number TEXT NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(room_id, mobile_number),
                FOREIGN KEY (room_id) REFERENCES voting_rooms(room_id)
            )
        ''')

        conn.commit()
        print("Database initialized successfully")

    except sqlite3.Error as e:
        print(f"Error initializing database: {str(e)}")
        raise
    finally:
        conn.close()

def create_voting_room(room_id, host_id, election_name):
    """Create a new voting room"""
    conn = sqlite3.connect('frvs.db')
    cursor = conn.cursor()
    try:
        current_time = datetime.now()
        
        cursor.execute('''
            INSERT INTO voting_rooms (room_id, host_id, election_name, created_at)
            VALUES (?, ?, ?, ?)
        ''', (room_id, host_id, election_name, current_time))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating voting room: {e}")
        return False
    finally:
        conn.close()

def get_host_rooms(host_id):
    """Get all rooms created by a host"""
    conn = sqlite3.connect('frvs.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM VotingRooms 
            WHERE host_id = ? 
            ORDER BY created_at DESC
        ''', (host_id,))
        return cursor.fetchall()
    finally:
        conn.close()

def get_room_by_id(room_id):
    """Get room details by room_id"""
    conn = sqlite3.connect('frvs.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM VotingRooms 
            WHERE room_id = ? AND is_active = 1
        ''', (room_id,))
        return cursor.fetchone()
    finally:
        conn.close()

def register_user(name, unique_id_number, room_id, face_encoding=None):
    """Register a new user in the system."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Users (name, unique_id_number, room_id)
            VALUES (?, ?, ?)
        ''', (name, unique_id_number, room_id))
        
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except Exception as e:
        print(f"Error registering user: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def save_face_encodings(user_id, face_encodings):
    """Save multiple face encodings for a user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for encoding in face_encodings:
            cursor.execute('''
                INSERT INTO FaceEncodings (user_id, face_encoding)
                VALUES (?, ?)
            ''', (user_id, pickle.dumps(encoding)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving face encodings: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_face_encodings():
    """Retrieve all face encodings with associated names."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.name, f.face_encoding
            FROM FaceEncodings f
            JOIN Users u ON f.user_id = u.user_id
        ''')
        results = cursor.fetchall()
        
        encodings = []
        names = []
        for row in results:
            encodings.append(pickle.loads(row['face_encoding']))
            names.append(row['name'])
        
        return encodings, names
    finally:
        conn.close()

def save_voted_face(face_encoding):
    """Save a face encoding of someone who has voted."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO VotedFaces (face_encoding)
            VALUES (?)
        ''', (pickle.dumps(face_encoding),))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving voted face: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_voted_faces():
    """Retrieve all face encodings of people who have voted."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT face_encoding FROM VotedFaces')
        results = cursor.fetchall()
        return [pickle.loads(row['face_encoding']) for row in results]
    finally:
        conn.close()

def record_vote(user_id, room_id, candidate_id):
    """Record a user's vote."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Votes (user_id, room_id, candidate_id)
            VALUES (?, ?, ?)
        ''', (user_id, room_id, candidate_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error recording vote: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def save_candidate(room_id, candidate_name, candidate_logo=None):
    conn = sqlite3.connect('frvs.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO RoomCandidates (room_id, candidate_name, candidate_logo)
            VALUES (?, ?, ?)
        ''', (room_id, candidate_name, candidate_logo))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving candidate: {e}")
        return False
    finally:
        conn.close()

def get_room_candidates(room_id):
    """Get all candidates for a room with their complete data"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                candidate_id,
                name,
                logo,
                votes,
                creation_time
            FROM Candidates 
            WHERE room_id = ? 
            ORDER BY candidate_id ASC
        ''', (room_id,))
        
        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                'id': row['candidate_id'],
                'name': row['name'],
                'logo': row['logo'],
                'votes': row['votes'],
                'creation_time': row['creation_time']
            })
        return candidates
    finally:
        conn.close()

def verify_room_access(room_id, host_id):
    """Verify if the host_id matches the room_id and room is active"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT room_id, election_name, is_active 
            FROM voting_rooms 
            WHERE room_id = ? AND host_id = ? AND is_active = 1
        ''', (room_id, host_id))
        
        room = cursor.fetchone()
        if not room:
            return None
        
        return dict(room)
    except Exception as e:
        print(f"Error verifying room access: {e}")
        return None
    finally:
        conn.close()

def update_room_settings(room_id, host_id, candidates=None):
    """Update room settings and candidates"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Verify room ownership
        cursor.execute('''
            SELECT room_id FROM voting_rooms 
            WHERE room_id = ? AND host_id = ? AND is_active = 1
        ''', (room_id, host_id))
        
        if not cursor.fetchone():
            return False, "Invalid room access"

        # Begin transaction
        conn.execute('BEGIN')

        # Update candidates if provided
        if candidates:
            # Get existing candidates
            cursor.execute('SELECT candidate_id, name FROM Candidates WHERE room_id = ?', (room_id,))
            existing_candidates = {row['name']: row['candidate_id'] for row in cursor.fetchall()}
            
            for candidate in candidates:
                if candidate['name'] in existing_candidates:
                    # Update existing candidate if logo changed
                    if candidate.get('logo'):
                        cursor.execute('''
                            UPDATE Candidates 
                            SET logo = ? 
                            WHERE candidate_id = ?
                        ''', (candidate['logo'], existing_candidates[candidate['name']]))
                else:
                    # Add new candidate
                    cursor.execute('''
                        INSERT INTO Candidates (room_id, name, logo)
                        VALUES (?, ?, ?)
                    ''', (room_id, candidate['name'], candidate.get('logo')))

        conn.commit()
        return True, "Room updated successfully"
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating room settings: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_room_state(room_id):
    """Get complete room state including candidates and settings"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get room details
        cursor.execute('''
            SELECT 
                r.room_id,
                r.host_id,
                r.election_name,
                r.is_active,
                COUNT(c.candidate_id) as candidate_count
            FROM voting_rooms r
            LEFT JOIN Candidates c ON r.room_id = c.room_id
            WHERE r.room_id = ?
            GROUP BY r.room_id
        ''', (room_id,))
        
        room = cursor.fetchone()
        if not room:
            return None
        
        room_data = dict(room)
        room_data['candidates'] = get_room_candidates(room_id)
        
        return room_data
    finally:
        conn.close()

def expire_room(room_id):
    """Manually terminate a voting room"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Update room status
        cursor.execute('''
            UPDATE voting_rooms 
            SET is_active = 0,
                terminated_at = CURRENT_TIMESTAMP
            WHERE room_id = ? AND is_active = 1
        ''', (room_id,))
        
        if cursor.rowcount == 0:
            return False, "Room not found or already terminated"
            
        conn.commit()
        return True, "Room terminated successfully"
        
    except Exception as e:
        conn.rollback()
        print(f"Error terminating room: {e}")
        return False, str(e)
    finally:
        conn.close()

