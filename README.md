# 🎯 Handwritten Digit Recognition System

A comprehensive Flask-based web application for recognizing handwritten digits using deep learning. Users can predict digits through multiple input methods: image upload, canvas drawing, and voice input.

## ✨ Features

### 🖼️ Multiple Prediction Methods
- **📤 Image Upload**: Upload handwritten digit images for instant prediction
- **✍️ Canvas Drawing**: Draw digits directly on the canvas and get real-time predictions
- **🎤 Voice Input**: Speak the digit with start/stop recording controls

### 👤 User Management
- User registration and authentication
- Secure login/logout functionality
- User password management and account deletion
- Profile page with prediction statistics

### 📊 Analytics & Reports
- **Analytics Dashboard**: View prediction statistics with interactive charts
- **Filterable Analytics**: Filter by prediction type (image, draw, voice) and date range
- **Top Predictions**: See most frequent digits and highest confidence predictions
- **Report Generation**: Download predictions as CSV or PDF reports

### 🛠️ Admin Dashboard
- User management (view, delete)
- System-wide analytics and statistics
- Admin settings and password management
- Predictions monitoring
- Comprehensive reports

### 🎨 User Experience
- **Dark/Light Theme Switcher**: Toggle between dark and light modes across all pages
- **Responsive Design**: Works seamlessly on desktop and mobile
- **Glass-morphism UI**: Modern, sleek interface with backdrop blur effects
- **Real-time Feedback**: Instant prediction results with confidence scores

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLite
- **ML Model**: TensorFlow/Keras (Digit Model)
- **Speech Recognition**: SpeechRecognition + librosa + soundfile
- **Audio Processing**: librosa, soundfile
- **Data Engineering**: NumPy, Pillow
- **Report Generation**: ReportLab

### Frontend
- **HTML5** with Jinja2 templating
- **CSS3** with glass-morphism design
- **JavaScript** (vanilla)
- **Canvas API** for drawing
- **Web Audio API** for voice recording
- **Chart.js** for data visualization

### Tools
- **Package Manager**: uv
- **Version Control**: Git

## 📋 Prerequisites

- Python 3.11+
- uv package manager
- Modern web browser with microphone support
- 500MB+ free disk space

## 🚀 Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd Handwritten-Digit-Recognition
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
uv sync
```

Or install individually:
```bash
uv add flask flask-cors
uv add tensorflow keras
uv add pillow numpy scipy
uv add SpeechRecognition librosa soundfile
uv add reportlab
```

### 4. Run Application
```bash
uv run app.py
```

The app will start on `http://127.0.0.1:5000`

## 📁 Project Structure

```
Handwritten-Digit-Recognition/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
├── pyproject.toml
│
├── backend/
│   ├── auth.py                     # User authentication
│   ├── db.py                       # Database management
│   └── predict.py                  # ML prediction models
│
├── model/
│   ├── digit_model.h5              # Pre-trained digit recognition model
│   ├── train_model.py              # Model training script
── dataset/                    # Training dataset (0-9 digits)
│
├── templates/
│                     
│   ├── home.html                   # Landing page
│   ├── user/
│   │   ├── login.html              # User login
│   │   ├── register.html           # User registration with password confirmation
│   │   ├── dashboard.html          # User dashboard
│   │   ├── predict.html            # Multi-method prediction interface
│   │   ├── profile.html            # User profile management
│   │   ├── history.html            # Prediction history
│   │   ├── analytics.html          # Analytics with filtering
│   │   ├── top_predictions.html    # Top predictions view
│   │   ├── reports.html            # Report generation
│   │   ├── download.html           # Download predictions
│   │   └── forgot_password.html
        └── reset_password.html  
│   │
│   └── admin/
│       ├── base_admin.html         # Admin base template
│       ├── admin_login.html        # Admin login
│       ├── admin_dashboard.html    # Admin dashboard
│       ├── users.html              # User management with delete button
│       ├── admin_analytics.html    # System analytics
│       ├── admin_reports.html      # System reports
│       ├── admin_settings.html     # Admin settings (password change)
│       └── admin_predictions.html
│       └── view_user.html
├── static/
│   ├── css/
│   │   ├── style.css               # Main styles
│   │   ├── home.css               
│   │   ├── dashboard.css           # Dashboard styles
│   │   ├── admin.css               # Admin styles
│   │   └── admin_dashboard.css
│   │
│   ├── js/
│   │   ├── script.js               # Main JavaScript
│   │   
│   │
│   └── uploads/                    # User uploaded files & recordings
│   └── profile_pics/

├── instance/                       # Flask instance folder
└── database/ 
    ├── digit.db                      
```

## 🎓 Usage Guide

### For Users

#### 1. **Registration & Login**
```
Home → Register → Create Account
      → Login → Enter Credentials
```

#### 2. **Make Predictions**
- **Upload Image**: Dashboard → Predict → Upload Image
- **Draw Digit**: Dashboard → Predict → Draw on Canvas
- **Voice Input**: Dashboard → Predict → Start Recording → Say Digit → Stop Recording

#### 3. **View Analytics**
- Analytics Dashboard with filterable charts
- Filter by prediction type and date range
- View statistics and accuracy metrics

#### 4. **Download Data**
- Export predictions as CSV
- Generate PDF reports
- Download images as ZIP

#### 5. **Manage Account**
- Profile page to view user information
- Change password (with confirmation)
- Delete account (requires password verification)

### For Admins

#### Admin Panel Access
```
Admin Page → /admin
Username: admin (default)
Password: (configured at setup)
```

#### Admin Features
1. **User Management**
   - View all users
   - View user details and prediction history
   - Delete users (removes all their predictions)

2. **Analytics**
   - System-wide statistics
   - Most predicted digits
   - Prediction distribution charts

3. **Settings**
   - Change admin password

## 🎤 Voice Input Guide

### For Best Results:
1. Speak clearly in English
2. Supported words: "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"
3. Also supports numeric digits: "1", "2", "3", etc.
4. Ensure microphone is working and browser has permission

### Recording Process:
1. Click **"Start Recording"** (green button)
2. Recordingimer will show elapsed seconds
3. Speak the digit clearly
4. Click **"Stop Recording"** (red button)
5. System processes audio and returns result

## 🔧 Configuration

### Edit `config.py`
```python
class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    UPLOAD_FOLDER = 'instance/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
```

### Environment Variables
Create `.env` file:
```
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=True
```

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Predictions Table
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    prediction_type TEXT,  -- 'upload', 'draw', 'voice'
    image_path TEXT,
    predicted_digit INTEGER,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```
## Dataset

The dataset is too large to be hosted on GitHub.

Download Dataset:
[https://drive.google.com/file/d/1i8jOTYF1VYW1J-uidIkGwPVUT5eujms6/view?usp=drivesdk]

After downloading, extract the dataset folder and place it in the project root directory.


## 📈 API Endpoints

### User Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | User login |
| GET | `/logout` | User logout |
| GET | `/dashboard` | User dashboard |
| POST | `/predict` | Upload and predict image |
| POST | `/predict_canvas` | Predict from canvas drawing |
| POST | `/predict_voice` | Predict from voice recording |
| GET | `/history` | View prediction history |
| GET | `/analytics` | View analytics with filters |
| GET | `/top_predictions` | View top predictions |
| GET | `/profile` | View user profile |
| POST | `/change_password` | Change password |
| POST | `/delete_account` | Delete account |

### Admin Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin_login` | Admin authentication |
| GET | `/admin_dashboard` | Admin dashboard |
| GET | `/admin/users` | Manage users |
| POST | `/admin/delete_user/<id>` | Delete user |
| GET | `/admin/analytics` | System analytics |
| GET | `/admin/settings` | Admin settings |
| POST | `/admin/change_password` | Change admin password |

## 🐛 Troubleshooting

### Voice Recognition Not Working
- Ensure microphone is connected and allowed in browser
- Grant microphone permission when prompted
- Check browser console (F12) for detailed error messages
- Speak clearly and at normal volume
- Check network connection (Google Speech API requires internet)

### Predictions Showing Low Confidence
- Ensure uploaded images are clear and well-lit
- Draw digits larger on canvas
- Ensure digits are dark on light background (MNIST format)

### Database Errors
- Delete `database.db` to reset database
- Ensure `instance/` folder has write permissions

### Port Already in Use
```bash
# Change port in app.py
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Use different port
```

## 📝 Recent Updates (v2.0)

✅ **Voice Recognition Improvements**
- Implemented proper audio format conversion (16kHz WAV)
- Better error handling and logging
- Real-time recording timer

✅ **UI/UX Enhancements**
- Updated voice input with Start/Stop buttons
- Improved recording status display
- Better visual feedback

✅ **Security Updates**
- Password verification required for account deletion
- Confirm password field in registration
- Admin password management

✅ **Admin Features**
- User deletion with confirmation
- Admin settings page with password change
- Enhanced user management

## 🚀 Deployment

### Production Deployment
```bash
# Install production server
uv add gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👥 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For issues and feature requests, please open an issue on GitHub.

## 🎓 Model Information

**Digit Prediction Model**
- Architecture: CNN (Convolutional Neural Network)
- Training Data: MNIST Dataset (0-9 digits)
- Input Size: 28×28 grayscale images
- Accuracy: 98%+
- Framework: TensorFlow/Keras

## 📚 References

- [MNIST Dataset](http://yann.lecun.com/exdb/mnist/)
- [TensorFlow Documentation](https://www.tensorflow.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SpeechRecognition Library](https://github.com/Uberi/speech_recognition)

---


