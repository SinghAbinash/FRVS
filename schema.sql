-- Create the Users table to store user information
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    unique_id_number TEXT UNIQUE NOT NULL,
    room_id TEXT NOT NULL,
    registration_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES VotingRooms(room_id)
);

-- Create the FaceData table to store facial encodings
CREATE TABLE IF NOT EXISTS FaceData (
    face_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    face_encoding BLOB NOT NULL,
    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Create the UploadedImages table
CREATE TABLE IF NOT EXISTS UploadedImages (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    id_card_image BLOB,
    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Create the VotingRooms table
CREATE TABLE IF NOT EXISTS VotingRooms (
    room_id TEXT PRIMARY KEY,
    election_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create the Candidates table
CREATE TABLE IF NOT EXISTS Candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL,
    candidate_name TEXT NOT NULL,
    candidate_position INTEGER NOT NULL,
    FOREIGN KEY (room_id) REFERENCES VotingRooms(room_id)
);

-- Create the Votes table
CREATE TABLE IF NOT EXISTS Votes (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    room_id TEXT NOT NULL,
    candidate_id INTEGER NOT NULL,
    vote_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, room_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (room_id) REFERENCES VotingRooms(room_id),
    FOREIGN KEY (candidate_id) REFERENCES Candidates(candidate_id)
);