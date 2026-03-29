# Temple Feedback Management System - Complete Guide

## 🎯 System Overview
A comprehensive temple feedback management system with public feedback submission, admin dashboard, officer portal, and live display screen.

## 📱 Access URLs

### Public Access
- **Feedback Submission**: https://temple-feedback-1.preview.emergentagent.com/submit-feedback
- **Display Screen (Temple TV)**: https://temple-feedback-1.preview.emergentagent.com/display

### Admin Access
- **Admin Login**: https://temple-feedback-1.preview.emergentagent.com/login
- **Credentials**: admin@temple.com / admin123

### Officer Access
- **Officer Login**: https://temple-feedback-1.preview.emergentagent.com/officer/login
- **Test Credentials**: officer@temple.com / officer123

---

## 🎨 Key Features

### 1. Public Feedback Submission (/submit-feedback)
**For Devotees - No Login Required**

✅ **Form Fields:**
- Select Temple (dropdown with all temples)
- Your Name (text input)
- Mobile Number (10 digits)
- Select Service (button grid):
  - Annadhanam
  - Darshan
  - Prasadam
  - Pooja
  - Donation
  - Other
  - General
- Select Rating (1-5 stars, clickable)
- Record Video (Max 60 seconds):
  - Live camera capture from mobile/tablet
  - Real-time recording with timer
  - Preview before submit
  - Clear and re-record option
- Additional Message (optional textarea)

✅ **Actions:**
- Clear Button: Resets entire form
- Submit Button: Uploads video and creates feedback
- Success: Shows complaint ID (e.g., TF00001)
- WhatsApp notification sent automatically (MOCKED)

---

### 2. Admin Dashboard (/admin)
**Full System Management**

#### 📊 Dashboard Page
- Total temples count
- Total officers count
- Feedback statistics (Total, Pending, In Progress, Resolved, Rejected)
- Temple-wise feedback chart

#### 🏛️ Temple Management
- View all temples in table
- Add new temple (Name, Location, Email)
- Edit temple details
- Delete temple
- Assign officers to temples

#### 👮 Officer Management
- View all officers
- Create new officer:
  - Name
  - Email
  - Password
  - Assign to temple
- Delete officer

#### 📹 Feedback Monitoring
- View all feedback in table
- Filters:
  - By Status (All, Pending, In Progress, Resolved, Rejected)
  - By Temple
- Table columns:
  - Complaint ID
  - Temple
  - User (name + mobile)
  - Service
  - Rating (stars)
  - Status (color-coded badges)
  - Date
  - Play Video button
- Click video to view:
  - Full video playback
  - All feedback details
  - User information
  - Officer notes (if any)

#### 💬 WhatsApp Logs
- View all WhatsApp messages sent
- Shows:
  - Mobile number
  - Message content
  - Status (Delivered/Failed)
  - Sent timestamp

#### 📊 Reports
- Summary statistics cards
- Filter by temple
- Export options:
  - PDF Report (with tables)
  - CSV Export (with all data)
- Recent feedback preview

---

### 3. Officer Dashboard (/officer)
**Temple-Specific Management**

#### 📊 Officer Stats
- Total feedback for assigned temple
- Pending count
- In Progress count
- Resolved count

#### 📝 My Complaints
- View only assigned temple's feedback
- Table with all feedback details
- "View & Update" button for each complaint

#### ✏️ Update Feedback
Dialog opens with:
- Video playback (if available)
- User details
- Service and rating
- Original message
- Update Status dropdown:
  - Pending
  - In Progress
  - Resolved
  - Rejected
- Officer Notes (textarea)
- Submit button:
  - Updates status
  - Saves notes
  - Sends WhatsApp reply to user (MOCKED)

---

### 4. Display Screen (/display)
**Temple TV Live Feed**

- Full-screen display for temple premises
- Shows recent 20 feedback items
- Bento grid layout
- Each card shows:
  - Complaint ID
  - Temple name
  - Service
  - Rating (stars)
  - Devotee name
  - Status (color-coded)
  - Date & time
  - Video indicator (if available)
- Auto-refresh every 10 seconds
- Live updates indicator

---

## 🎨 Design Theme

### Colors
- **Primary**: Maroon (#721C24)
- **Secondary**: Saffron/Gold (#F4C430)
- **Background**: Cream (#FDFBF7)
- **Surface**: White (#FFFFFF)
- **Accent**: Orange (#FF9933)

### Typography
- **Headings**: Cormorant Garamond (serif)
- **Body**: Outfit (sans-serif)

### UI Elements
- Magic curve sidebar (rounded corner)
- Glass-morphism effects
- Smooth transitions (300ms)
- Shadow elevations on hover
- Color-coded status badges

---

## 🔧 Technical Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **Storage**: Object Storage (Emergent)
- **Authentication**: JWT tokens
- **API Prefix**: /api

### Frontend
- **Framework**: React 18
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **Components**: Shadcn UI
- **Video Player**: React Player
- **Charts**: Recharts
- **PDF Export**: jsPDF
- **Date Formatting**: date-fns

### Integrations
- **Object Storage**: For video/photo uploads
- **WhatsApp**: Mock service (database logging)
- **OTP**: Mock service (always 123456)

---

## 📊 Database Collections

### temples
```json
{
  "id": "uuid",
  "name": "string",
  "location": "string",
  "email": "string (optional)",
  "services": ["array"],
  "officer_id": "string (optional)",
  "created_at": "ISO timestamp"
}
```

### officers
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "password": "hashed",
  "temple_id": "string",
  "temple_name": "string",
  "created_at": "ISO timestamp"
}
```

### feedback
```json
{
  "id": "uuid",
  "complaint_id": "TF00001",
  "temple_id": "uuid",
  "temple_name": "string",
  "user_mobile": "string",
  "user_name": "string",
  "service": "string",
  "video_url": "string (optional)",
  "video_path": "string",
  "photo_url": "string (optional)",
  "rating": "1-5",
  "message": "string (optional)",
  "location": "object (optional)",
  "status": "Pending|In Progress|Resolved|Rejected",
  "created_at": "ISO timestamp",
  "resolved_at": "ISO timestamp (optional)",
  "officer_notes": "string (optional)"
}
```

### whatsapp_logs
```json
{
  "id": "uuid",
  "feedback_id": "uuid",
  "mobile": "string",
  "message": "string",
  "status": "Delivered|Failed",
  "sent_at": "ISO timestamp"
}
```

---

## 🔐 Authentication Flow

### Admin
1. Login with admin@temple.com / admin123
2. Receives JWT token
3. Token stored in localStorage
4. All API calls include Authorization header
5. Token expires after 7 days

### Officer
1. Admin creates officer with credentials
2. Officer logs in with email/password
3. Receives JWT token with temple_id
4. Can only access their temple's data
5. Token expires after 7 days

### Public User (Devotee)
- No authentication required
- Direct access to /submit-feedback
- Can submit feedback without login

---

## 📱 User Flows

### Devotee Submits Feedback
1. Opens /submit-feedback
2. Selects temple from dropdown
3. Enters name and mobile number
4. Selects service (Annadhanam, Darshan, etc.)
5. Clicks rating stars (1-5)
6. Clicks "Start Recording"
7. Records video (max 60 seconds)
8. Stops recording or auto-stops at 60s
9. Previews video
10. Can clear and re-record
11. Adds optional message
12. Clicks Submit
13. Video uploads to object storage
14. Feedback saved to database
15. WhatsApp sent with complaint ID
16. Success message shown with ID

### Admin Manages System
1. Logs in at /login
2. Views dashboard statistics
3. Creates temples (Temples page)
4. Creates officers and assigns temples
5. Monitors all feedback (Feedback page)
6. Watches feedback videos
7. Views WhatsApp logs
8. Generates reports (PDF/CSV)
9. Exports data for analysis

### Officer Handles Complaints
1. Logs in at /officer/login
2. Views dashboard with temple stats
3. Sees only assigned temple's feedback
4. Clicks "View & Update" on complaint
5. Watches feedback video
6. Reviews user details
7. Selects new status
8. Adds officer notes
9. Clicks Update
10. Status updated in database
11. WhatsApp reply sent to user
12. Dashboard refreshes

### Temple TV Shows Live Feed
1. Display screen opens /display
2. Shows recent 20 feedback items
3. Auto-refreshes every 10 seconds
4. Shows real-time updates
5. Color-coded status badges
6. Large text for visibility

---

## 🚀 API Endpoints

### Authentication
- `POST /api/auth/admin/login` - Admin login
- `POST /api/auth/officer/login` - Officer login
- `POST /api/auth/send-otp` - Send OTP (mock)
- `POST /api/auth/verify-otp` - Verify OTP (mock)

### Temples
- `GET /api/temples` - Get all temples
- `POST /api/temples` - Create temple (admin)
- `PUT /api/temples/{id}` - Update temple (admin)
- `DELETE /api/temples/{id}` - Delete temple (admin)

### Officers
- `GET /api/officers` - Get all officers (admin)
- `POST /api/officers` - Create officer (admin)
- `DELETE /api/officers/{id}` - Delete officer (admin)

### Feedback
- `POST /api/feedback` - Submit feedback (public)
- `GET /api/feedback` - Get all feedback (with filters)
- `GET /api/feedback/officer` - Get officer's temple feedback
- `GET /api/feedback/{id}` - Get feedback by ID
- `PUT /api/feedback/{id}/status` - Update feedback status (officer)

### Uploads
- `POST /api/upload/video` - Upload video file
- `POST /api/upload/photo` - Upload photo file
- `GET /api/files/{path}` - Download/view file

### Dashboard
- `GET /api/dashboard/stats` - Admin dashboard stats
- `GET /api/dashboard/officer-stats` - Officer dashboard stats

### WhatsApp
- `GET /api/whatsapp/logs` - Get WhatsApp logs (admin)

### Display
- `GET /api/display/live-feed` - Get recent feedback for TV

---

## 🎯 Default Data

### Temples
1. **Bhadrachalam Devasthanam** - Bhadrachalam, Telangana
2. **Vemulawada Devasthanam** - Vemulawada, Telangana
3. **Yadagirigutta** - Yadagirigutta, Telangana

### Services
- Annadhanam
- Darshan
- Prasadam
- Pooja
- Donation
- Other
- General

### Admin
- Email: admin@temple.com
- Password: admin123

### Test Officer
- Name: Test Officer
- Email: officer@temple.com
- Password: officer123
- Temple: Bhadrachalam Devasthanam

---

## ⚠️ Mock Services

### Mock OTP
- **Code**: Always 123456
- **Usage**: Any mobile number can use this OTP
- **Expiry**: 10 minutes
- **Purpose**: Development/testing only

### Mock WhatsApp
- **Behavior**: Messages logged to database
- **Status**: Always "Delivered"
- **Actual Sending**: Not implemented
- **Purpose**: For testing workflow
- **Replacement**: Use webhook https://aatreyaomnicloud.com/webhook

---

## 📈 Next Steps / Enhancements

### High Priority
1. **Real WhatsApp Integration**
   - Replace mock with actual WhatsApp API
   - Use webhook: https://aatreyaomnicloud.com/webhook
   - Add delivery status tracking

2. **Real OTP Service**
   - Integrate Twilio or MSG91
   - Add proper SMS sending
   - Rate limiting

3. **Mobile App Development**
   - Build React Native or Flutter app
   - Compile to APK for Android
   - Compile to IPA for iOS
   - Add push notifications

### Medium Priority
4. **Photo Upload**
   - Add optional photo upload alongside video
   - Multiple photo support
   - Image compression

5. **Geo-Location**
   - Capture user location on submit
   - Show on map in admin dashboard
   - Location-based analytics

6. **Analytics Dashboard**
   - Advanced charts and graphs
   - Trend analysis
   - Service-wise breakdown
   - Time-series analysis

### Low Priority
7. **Multi-language Support**
   - Telugu, Hindi, English
   - Language switcher
   - Localized messages

8. **Email Notifications**
   - Send email along with WhatsApp
   - Email reports to temple admin
   - Weekly summaries

9. **Advanced Search**
   - Search by complaint ID
   - Search by mobile number
   - Date range filters
   - Service-specific search

---

## 🔒 Security Features

- Password hashing with bcrypt
- JWT token authentication
- Role-based access control (Admin/Officer)
- Temple-specific data isolation for officers
- MongoDB _id exclusion (no ObjectId serialization errors)
- Input validation on all forms
- CORS configuration
- File upload size limits

---

## 🎬 Demo Scenarios

### Scenario 1: New Devotee Feedback
1. Devotee visits temple
2. Scans QR code or opens link
3. Fills form and records video
4. Submits feedback
5. Gets complaint ID: TF00001
6. Receives WhatsApp confirmation

### Scenario 2: Officer Resolves Complaint
1. Officer logs in
2. Sees new feedback notification
3. Watches video
4. Marks as "In Progress"
5. Takes action at temple
6. Updates status to "Resolved"
7. Adds notes: "Issue fixed"
8. User gets WhatsApp update

### Scenario 3: Admin Reviews Reports
1. Admin logs in
2. Views dashboard
3. Sees 100 feedback this month
4. 80 resolved, 15 in progress, 5 pending
5. Exports PDF report
6. Shares with temple committee
7. Identifies improvement areas

---

## 📞 Support

For technical issues or feature requests, contact the development team.

**System Status**: ✅ Fully Operational
**Last Updated**: March 26, 2026
**Version**: 1.0.0

---

## 🌟 Success Metrics

- ✅ Public feedback submission working
- ✅ Video recording with MediaRecorder API
- ✅ Object storage integration
- ✅ Admin dashboard fully functional
- ✅ Officer portal operational
- ✅ Display screen with auto-refresh
- ✅ WhatsApp mock service
- ✅ Traditional temple theme implemented
- ✅ Responsive design
- ✅ All CRUD operations working

**Ready for production with real WhatsApp/OTP integration!**
