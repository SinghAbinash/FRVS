# Face Recognition Voting System (FRVS)

A secure digital voting system using facial recognition technology for voter authentication.

## Features

- **Secure Authentication**: Face recognition with liveness detection
- **Real-time Face Verification**: Movement detection to prevent photo spoofing
- **Dynamic Voting Rooms**: Create and manage voting sessions
- **Result Analytics**: Real-time vote counting and result visualization
- **Desktop Optimized**: Enhanced security through desktop-only access
- **User Management**: Separate interfaces for voters and hosts
- **Data Protection**: Secure storage of voter data and face encodings

## Prerequisites

- Python 3.8 or higher
- Webcam access
- Desktop/Laptop device (Mobile devices not supported)
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/FRVS.git
cd FRVS
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python init_db.py
```

## Usage

1. Start the application:
```bash
python app7.py
```

2. Access the application at `http://localhost:5000`

3. Choose your role:
   - Host: Create and manage voting rooms
   - Voter: Join rooms and cast votes

## Project Structure

```
FRVS/
├── app7.py              # Main application file
├── templates/           # HTML templates
├── static/             # Static files (CSS, JS)
├── models/             # Face recognition models
├── uploads/           # Temporary file storage
├── database/          # Database files
└── requirements.txt   # Project dependencies
```

## Security Features

- Face movement detection for liveness verification
- Secure session management
- SQL injection prevention
- XSS protection
- CSRF protection
- Desktop-only access

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Face recognition powered by dlib and face_recognition
- Frontend framework: Bootstrap
- Backend framework: Flask

## Contact

Your Name - yourmail@example.com
Project Link: [https://github.com/yourusername/FRVS](https://github.com/SinghAbinash/FRVS)
