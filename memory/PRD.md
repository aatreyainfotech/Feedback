# Temple Feedback Management System - PRD

## Original Problem Statement
Build a comprehensive Temple Feedback Management System with an Admin Dashboard, Officer Dashboard, and a tablet-based Public Feedback application. Key features include tracking feedback via video capture, location mapping, officer assignment, temple management, and generating reports. Additionally, integrate a "Tablet Kiosk Mode" where tablets are locked to specific temples and enforce direct camera recording for feedback.

## System Overview
A fully functional React frontend and FastAPI + MongoDB backend system featuring:
- **Admin Dashboard**: Temple, officer, services, and feedback management
- **Officer Dashboard**: View and manage assigned feedback
- **Tablet Kiosk Flow**: Device registration to temples, public feedback submission with mandatory video recording
- **Native Android APK**: Ready for build using Capacitor

## Tech Stack
- **Frontend**: React, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Mobile**: Capacitor (Android APK)

## Key Features Implemented
- [x] Complete Architecture Setup (React, FastAPI, MongoDB)
- [x] Tablet Kiosk Setup & Flow (`/setup-temple`)
- [x] Public Feedback submission with mandatory camera recording
- [x] Admin & Officer Dashboards
- [x] Temple logo uploading and frontend branding
- [x] Officer Assignment and Video Playback features
- [x] Official UI Branding (Govt Header and Aatreya Footer)
- [x] Services Management
- [x] Success screen with auto-transition (1 second)
- [x] Mobile number validation (10 digits only)
- [x] "Devotee" terminology across all pages
- [x] Android APK build setup with Capacitor
- [x] Documentation files (SYSTEM_GUIDE.md, ALL_URLS.md, DATABASE.md, APK_BUILD_GUIDE.md)
- [x] GitHub repository push completed

## Database Schema
- `temples`: {id, name, location, email, logo_url}
- `services`: {id, name}
- `feedback`: {id, temple_id, devotee_name, mobile_number, service_id, rating, video_url, message, status, officer_id, transaction_id, created_at}
- `officers`: {id, temple_id, username, password, name}
- `users`: {id, username, role, password}

## Key API Endpoints
- `POST /api/auth/login`
- `GET/POST /api/temples`
- `GET/POST /api/services`
- `GET/POST /api/feedback`
- `PUT /api/feedback/{feedback_id}/status`
- `PUT /api/feedback/{feedback_id}/assign`

## GitHub Repository
- **URL**: https://github.com/sriaatreya/temple-feedback-system
- **Status**: Updated with Android APK build (March 26, 2025)

## Android APK Details
- **App Name**: Temple Feedback
- **Package ID**: com.aatreya.templefeedback
- **Build Guide**: See APK_BUILD_GUIDE.md
- **Permissions**: Camera, Audio, Storage, Internet

## Backlog / Future Tasks
### P1 (High Priority)
- Real Meta WhatsApp API / Webhook integration (currently mocked)

### P2 (Medium Priority)
- Multi-language Support (Telugu / English) for the public form
- AI Sentiment Analysis and Auto Escalation (if not resolved in 24 hrs)

## Mocked Features
- WhatsApp Webhook Notifications
- OTP Verification

## Important Notes
- **Tablet Kiosk Flow**: Frontend bypasses "select temple" dropdown. Admins must first go to `/setup-temple` to register a device to a temple via email. This sets `localStorage` items. `/submit-feedback` reads these values.

