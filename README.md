# Temple Feedback Management System

A comprehensive feedback management system for temples with Admin Dashboard, Officer Dashboard, and Tablet Kiosk mode for public feedback collection.

![Telangana Endowment Department](https://upload.wikimedia.org/wikipedia/en/thumb/7/77/Emblem_of_Telangana.svg/150px-Emblem_of_Telangana.svg.png)

**Sponsored by**: Central Bank of India  
**Developed by**: Aatreya Infotech

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Environment Setup](#-environment-setup)
- [Running the Application](#-running-the-application)
- [Default Credentials](#-default-credentials)
- [Application URLs](#-application-urls)
- [API Endpoints](#-api-endpoints)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Tablet Kiosk Setup](#-tablet-kiosk-setup)
- [Building APK](#-building-apk)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### Admin Dashboard
- 📊 Dashboard with statistics and charts
- 🛕 Temple management (add, edit, delete, logo upload)
- 👥 Officer management with role & permissions
- 📝 Service category management
- 📋 Feedback monitoring with video playback
- 📱 WhatsApp notification logs
- 📈 Reports generation and export
- ⚙️ Administration panel for role management

### Officer Dashboard
- 📋 View assigned feedback
- ✅ Update feedback status
- 📹 Watch feedback videos
- 📊 Personal statistics

### Public Feedback (Tablet Kiosk)
- 🎥 Mandatory video recording for feedback
- 📝 Simple form with service selection
- ⭐ Rating system (1-5 stars)
- 🔒 Locked to specific temple after setup

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 19, Tailwind CSS, shadcn/ui |
| Backend | FastAPI (Python 3.11+) |
| Database | SQLDB |
| Charts | Recharts |
| Video | MediaRecorder API |
| Mobile | Capacitor (for APK build) |

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Yarn** (v1.22+) - `npm install -g yarn`
- **Python** (v3.11+) - [Download](https://python.org/)
- **MongoDB** (v6+) - [Download](https://mongodb.com/try/download/community)
- **Git** - [Download](https://git-scm.com/)

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/sriaatreya/temple-feedback-system.git
cd temple-feedback-system
```

### Step 2: Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend folder
cd ../frontend

# Install dependencies
yarn install
```

---

## ⚙️ Environment Setup

### Backend Environment (.env)

Create `/backend/.env` file:

```env
# MongoDB Connection
MONGO_URL=mongodb://localhost:27017
DB_NAME=temple_feedback

# CORS Settings
CORS_ORIGINS=http://localhost:3000,http://localhost:8001

# JWT Secret (change in production!)
JWT_SECRET=your_super_secret_jwt_key_change_this_in_production

# File Upload Settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=52428800

# Optional: Object Storage (for video uploads)
STORAGE_ACCESS_KEY=your_storage_key
STORAGE_SECRET_KEY=your_storage_secret
```

### Frontend Environment (.env)

Create `/frontend/.env` file:

```env
# Backend API URL
REACT_APP_BACKEND_URL=http://localhost:8001

# WebSocket Port (for development)
WDS_SOCKET_PORT=443
```

---

## ▶️ Running the Application

### Option 1: Run Separately (Development)

**Terminal 1 - Start MongoDB:**
```bash
# Windows
mongod

# macOS/Linux
sudo systemctl start mongod
```

**Terminal 2 - Start Backend:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 3 - Start Frontend:**
```bash
cd frontend
yarn start
```

### Option 2: Using Docker (Recommended for Production)

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Verify Installation

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001/api/docs
- MongoDB: mongodb://localhost:27017

---

## 🔐 Default Credentials

### Admin Login
| Field | Value |
|-------|-------|
| Email | admin@temple.com |
| Password | admin123 |

### Officer Login
| Field | Value |
|-------|-------|
| Email | officer@temple.com |
| Password | officer123 |

---

## 🌐 Application URLs

| Page | URL | Description |
|------|-----|-------------|
| Admin Login | `/admin/login` | Admin authentication |
| Admin Dashboard | `/admin/dashboard` | Statistics overview |
| Temples | `/admin/temples` | Manage temples |
| Officers | `/admin/officers` | Manage officers |
| Services | `/admin/services` | Manage service categories |
| Feedback | `/admin/feedback` | Monitor all feedback |
| WhatsApp Logs | `/admin/whatsapp-logs` | View notification logs |
| Reports | `/admin/reports` | Generate reports |
| Administration | `/admin/administration` | Role & permissions |
| Officer Login | `/officer/login` | Officer authentication |
| Officer Dashboard | `/officer/dashboard` | Officer workspace |
| Temple Setup | `/setup-temple` | Kiosk registration |
| Submit Feedback | `/submit-feedback` | Public feedback form |
| Display Screen | `/display` | Temple display screen |

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Admin/Officer login |
| POST | `/api/auth/officer/login` | Officer login |

### Temples
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/temples` | Get all temples |
| POST | `/api/temples` | Create temple |
| GET | `/api/temples/{id}` | Get temple by ID |
| PUT | `/api/temples/{id}` | Update temple |
| DELETE | `/api/temples/{id}` | Delete temple |
| GET | `/api/temples/by-email/{email}` | Get temple by email |

### Officers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/officers` | Get all officers |
| POST | `/api/officers` | Create officer |
| DELETE | `/api/officers/{id}` | Delete officer |
| PUT | `/api/officers/{id}/role` | Update role/permissions |

### Services
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/services` | Get all services |
| POST | `/api/services` | Create service |
| DELETE | `/api/services/{id}` | Delete service |

### Feedback
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/feedback` | Get all feedback |
| POST | `/api/feedback` | Submit feedback |
| PUT | `/api/feedback/{id}/status` | Update status |
| PUT | `/api/feedback/{id}/assign` | Assign officer |

### Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Get dashboard stats |
| GET | `/api/officer/stats` | Get officer stats |

---

## 📁 Project Structure

```
temple-feedback-system/
├── backend/
│   ├── server.py           # Main FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── .env               # Environment variables
│   └── uploads/           # Uploaded files
│
├── frontend/
│   ├── public/
│   │   └── ts-logo.png    # Telangana State logo
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/        # shadcn/ui components
│   │   │   ├── Header.js
│   │   │   ├── Footer.js
│   │   │   ├── AdminLayout.js
│   │   │   └── OfficerLayout.js
│   │   ├── pages/
│   │   │   ├── AdminDashboard.js
│   │   │   ├── AdminLogin.js
│   │   │   ├── Temples.js
│   │   │   ├── Officers.js
│   │   │   ├── Services.js
│   │   │   ├── FeedbackMonitoring.js
│   │   │   ├── WhatsAppLogs.js
│   │   │   ├── Reports.js
│   │   │   ├── Administration.js
│   │   │   ├── OfficerLogin.js
│   │   │   ├── OfficerDashboard.js
│   │   │   ├── TempleSetup.js
│   │   │   ├── PublicFeedbackSubmit.js
│   │   │   └── DisplayScreen.js
│   │   ├── utils/
│   │   │   └── api.js     # Axios configuration
│   │   ├── App.js         # Routes
│   │   └── index.css      # Global styles
│   ├── package.json
│   └── .env
│
├── android/               # Capacitor Android project
├── SQL_SERVER_SETUP.sql   # SQL Server setup script
├── SQL_SERVER_README.md   # SQL Server documentation
├── SYSTEM_GUIDE.md        # System guide
├── ALL_URLS.md           # All application URLs
├── DATABASE.md           # Database documentation
└── README.md             # This file
```

---

## 🗄 Database Schema

### Collections (MongoDB)

**users**
```javascript
{
  id: String,
  username: String,
  email: String,
  password: String (hashed),
  role: "admin",
  created_at: DateTime
}
```

**temples**
```javascript
{
  id: String,
  name: String,
  location: String,
  email: String,
  logo_path: String,
  officer_id: String,
  created_at: DateTime
}
```

**officers**
```javascript
{
  id: String,
  name: String,
  email: String,
  password: String (hashed),
  temple_id: String,
  temple_name: String,
  role: "officer" | "supervisor" | "eo",
  permissions: Array,
  created_at: DateTime
}
```

**feedback**
```javascript
{
  id: String,
  complaint_id: String (TF00001),
  temple_id: String,
  temple_name: String,
  user_name: String,
  user_mobile: String,
  service: String,
  rating: Number (1-5),
  message: String,
  video_url: String,
  status: "Pending" | "In Progress" | "Resolved" | "Rejected",
  officer_id: String,
  officer_name: String,
  created_at: DateTime
}
```

**services**
```javascript
{
  id: String,
  name: String,
  order: Number,
  created_at: DateTime
}
```

---

## 📱 Tablet Kiosk Setup

### Step 1: Register Tablet to Temple

1. Open `/setup-temple` on the tablet
2. Enter the temple's registered email
3. Click "Register Device"
4. Device is now locked to that temple

### Step 2: Configure Kiosk Mode

**Option A: Using Fully Kiosk Browser (Recommended)**
1. Install "Fully Kiosk Browser" from Play Store
2. Set the start URL to your deployed app
3. Enable kiosk mode in settings
4. Lock device to app

**Option B: Android Device Owner Mode**
1. Build the APK (see Building APK section)
2. Install as device owner
3. Use Android's pinned app mode

---

## 📲 Building APK

### Prerequisites
- Android Studio installed
- Java JDK 17+

### Build Steps

```bash
# Navigate to frontend
cd frontend

# Build the web app
yarn build

# Sync with Capacitor
npx cap sync android

# Open in Android Studio
npx cap open android
```

### In Android Studio:
1. Wait for Gradle sync
2. Go to **Build → Generate Signed Bundle / APK**
3. Select **APK**
4. Create keystore or use existing
5. Choose **release** build
6. Click **Finish**

APK location: `frontend/android/app/build/outputs/apk/release/app-release.apk`

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check if port 8001 is in use
netstat -an | grep 8001

# Kill process if needed
kill -9 <PID>
```

### MongoDB connection failed
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod
```

### Frontend build errors
```bash
# Clear cache and reinstall
rm -rf node_modules
rm yarn.lock
yarn install
```

### Camera not working on tablet
- Ensure HTTPS is used (required for camera)
- Check camera permissions in browser/app settings
- Verify MediaRecorder API support

### CORS errors
- Verify `CORS_ORIGINS` in backend `.env` includes frontend URL
- Restart backend after changing `.env`

---

## 📞 Support

For issues or feature requests, contact:

**Aatreya Infotech**  
Email: support@aatreyainfotech.com

---

## 📄 License

This project is proprietary software developed for Telangana Endowment Department.

© 2026 Telangana Endowment Department. All rights reserved.

---

**Sponsored by Central Bank of India | Developed by Aatreya Infotech**
