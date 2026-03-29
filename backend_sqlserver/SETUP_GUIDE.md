# Temple Feedback System - SQL Server Setup Guide

## Complete Setup Instructions for SQL Server Backend

---

## Step 1: SQL Server Setup

### 1.1 Run the Database Script
1. Open SQL Server Management Studio (SSMS)
2. Connect to your server (e.g., `DESKTOP-JGCUNUE\SQLEXPRESS`)
3. Open `SQL_SERVER_SETUP.sql`
4. Execute the entire script (F5)

### 1.2 Verify Setup
```sql
USE ts_feedbackdb;
SELECT * FROM users;
SELECT * FROM temples;
SELECT * FROM services;
```

---

## Step 2: Backend Setup

### 2.1 Copy Backend Files
Copy the entire `backend_sqlserver` folder to your project location.

### 2.2 Configure Environment Variables
Edit `backend_sqlserver/.env`:

```env
# SQL Server Configuration
DB_TYPE=sqlserver
DB_SERVER=DESKTOP-JGCUNUE\SQLEXPRESS
DB_NAME=ts_feedbackdb
DB_USER=ts_feedback_user
DB_PASSWORD=TsFeedback@2026!

# CORS Settings (add your frontend URL)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# JWT Secret (change in production!)
JWT_SECRET=temple_feedback_secret_key_2026

# File Upload Settings
UPLOAD_DIR=uploads
MAX_FILE_SIZE=52428800
```

### 2.3 Install Python Dependencies
```bash
cd backend_sqlserver

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2.4 Install ODBC Driver
Download and install "ODBC Driver 17 for SQL Server":
- Windows: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 2.5 Run Backend Server
```bash
cd backend_sqlserver
python server.py
```
Or:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Backend will run at: http://localhost:8000

---

## Step 3: Frontend Setup

### 3.1 Configure Frontend Environment
Edit `frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

### 3.2 Install Dependencies
```bash
cd frontend
yarn install
```

### 3.3 Run Frontend
```bash
yarn start
```

Frontend will run at: http://localhost:3000

---

## Step 4: Verify Installation

### Test API
```bash
# Test health endpoint
curl http://localhost:8000/api/health

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@temple.com","password":"admin123"}'
```

### Access Application
- Admin Login: http://localhost:3000/admin/login
- Officer Login: http://localhost:3000/officer/login

---

## File Structure

```
temple-feedback-system/
├── backend_sqlserver/
│   ├── server.py           # SQL Server backend
│   ├── requirements.txt    # Python dependencies
│   ├── .env               # Environment variables
│   └── uploads/           # Uploaded files
│
├── frontend/
│   ├── src/               # React source code
│   ├── package.json
│   └── .env               # Frontend config
│
└── SQL_SERVER_SETUP.sql   # Database setup script
```

---

## Environment Variables Reference

### Backend (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| DB_TYPE | Database type | sqlserver |
| DB_SERVER | SQL Server instance | DESKTOP-JGCUNUE\SQLEXPRESS |
| DB_NAME | Database name | ts_feedbackdb |
| DB_USER | Database user | ts_feedback_user |
| DB_PASSWORD | Database password | TsFeedback@2026! |
| CORS_ORIGINS | Allowed origins | http://localhost:3000 |
| JWT_SECRET | JWT signing key | your_secret_key |
| UPLOAD_DIR | Upload directory | uploads |

### Frontend (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| REACT_APP_BACKEND_URL | Backend API URL | http://localhost:8000 |

---

## Default Credentials

### Admin
- Email: `admin@temple.com`
- Password: `admin123`

### Officer
- Email: `officer@temple.com`
- Password: `officer123`

---

## Troubleshooting

### Connection Error: "ODBC Driver 17 not found"
Install ODBC Driver 17 for SQL Server from Microsoft.

### Connection Error: "Login failed"
1. Ensure SQL Server Authentication is enabled
2. Verify username and password
3. Check if user has access to database

### CORS Error
Add your frontend URL to `CORS_ORIGINS` in backend `.env`

### Port Already in Use
```bash
# Windows - Find process
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Admin login |
| POST | /api/auth/officer/login | Officer login |
| GET | /api/temples | Get all temples |
| POST | /api/temples | Create temple |
| GET | /api/officers | Get all officers |
| POST | /api/officers | Create officer |
| GET | /api/services | Get all services |
| POST | /api/services | Create service |
| GET | /api/feedback | Get all feedback |
| POST | /api/feedback | Submit feedback |
| POST | /api/feedback/with-video | Submit feedback with video |
| PUT | /api/feedback/{id}/status | Update status |
| PUT | /api/feedback/{id}/assign | Assign officer |
| GET | /api/stats | Get dashboard stats |
| GET | /api/whatsapp-logs | Get WhatsApp logs |

---

## Production Deployment

1. Use a production SQL Server instance
2. Change JWT_SECRET to a strong random key
3. Set CORS_ORIGINS to your production domain
4. Use HTTPS for all connections
5. Set up proper firewall rules
6. Enable SQL Server SSL/TLS

---

**Developed by Aatreya Infotech**
**Sponsored by Central Bank of India**
