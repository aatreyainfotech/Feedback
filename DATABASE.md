# Temple Feedback System - Database Schema Documentation

## MongoDB Collections

This document describes all MongoDB collections used in the Temple Feedback Management System.

---

## Collections Overview

1. **temples** - Temple information and configuration
2. **officers** - Officer accounts and assignments
3. **feedback** - Feedback submissions from devotees
4. **services** - Service categories for feedback
5. **whatsapp_logs** - WhatsApp notification logs
6. **files** - File storage metadata
7. **users** - User OTP data (optional)

---

## Detailed Schema

### 1. temples

Stores temple information including name, location, logo, and services.

```javascript
{
  _id: ObjectId,  // MongoDB internal ID
  id: "uuid-string",  // Application UUID
  name: "Bhadrachalam Devasthanam",
  location: "Bhadrachalam, Telangana",
  email: "bhadrachalam@temple.com",  // Optional, for tablet registration
  logo_path: "temple-feedback/logos/uuid.png",  // Optional, object storage path
  services: [
    "Annadhanam",
    "Darshan",
    "Prasadam",
    "Pooja",
    "Donation",
    "Other",
    "General"
  ],
  officer_id: "uuid-string",  // Optional, assigned officer
  created_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `id` (unique)
- `email` (unique, sparse)

---

### 2. officers

Stores officer account information and temple assignments.

```javascript
{
  _id: ObjectId,
  id: "uuid-string",
  name: "Officer Name",
  email: "officer@temple.com",  // Unique
  password: "$2b$12$hashed_password",  // Bcrypt hashed
  temple_id: "uuid-string",  // Assigned temple
  temple_name: "Bhadrachalam Devasthanam",
  created_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `id` (unique)
- `email` (unique)
- `temple_id`

---

### 3. feedback

Stores all feedback submissions from devotees.

```javascript
{
  _id: ObjectId,
  id: "uuid-string",
  complaint_id: "TF00001",  // Sequential ID for display
  temple_id: "uuid-string",
  temple_name: "Bhadrachalam Devasthanam",
  user_mobile: "9876543210",
  user_name: "Devotee Name",
  service: "Darshan",
  video_path: "temple-feedback/videos/uuid.webm",  // Object storage path
  photo_path: "temple-feedback/photos/uuid.jpg",  // Optional
  rating: 5,  // 1-5 stars
  message: "Optional feedback message",
  location: {  // Optional geolocation
    latitude: 17.385044,
    longitude: 78.486671
  },
  status: "Pending",  // Pending|In Progress|Resolved|Rejected
  assigned_officer_id: "uuid-string",  // Optional
  assigned_officer_name: "Officer Name",  // Optional
  officer_notes: "Action taken...",  // Optional
  created_at: "2026-03-26T10:00:00.000000+00:00",
  resolved_at: "2026-03-26T12:00:00.000000+00:00"  // Optional
}
```

**Indexes:**
- `id` (unique)
- `complaint_id` (unique)
- `temple_id`
- `status`
- `assigned_officer_id`
- `created_at` (descending)

---

### 4. services

Stores service categories for feedback selection.

```javascript
{
  _id: ObjectId,
  id: "uuid-string",
  name: "Annadhanam",
  order: 1,  // Display order
  created_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `id` (unique)
- `order`

---

### 5. whatsapp_logs

Stores WhatsApp notification logs.

```javascript
{
  _id: ObjectId,
  id: "uuid-string",
  feedback_id: "uuid-string",
  mobile: "9876543210",
  message: "Dear Devotee, Your feedback (ID: #TF00001)...",
  status: "Delivered",  // Delivered|Failed
  sent_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `id` (unique)
- `feedback_id`
- `sent_at` (descending)

---

### 6. files

Stores metadata for uploaded files (videos, photos, logos).

```javascript
{
  _id: ObjectId,
  id: "uuid-string",
  storage_path: "temple-feedback/videos/uuid.webm",
  original_filename: "feedback-video.webm",
  content_type: "video/webm",
  size: 5242880,  // Bytes
  type: "video",  // video|photo|logo
  is_deleted: false,
  created_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `id` (unique)
- `storage_path` (unique)
- `type`
- `is_deleted`

---

### 7. users (Optional)

Stores OTP data for mobile verification (if using real OTP).

```javascript
{
  _id: ObjectId,
  mobile: "9876543210",
  name: "Devotee Name",  // Optional
  otp: "123456",
  otp_expires: "2026-03-26T10:10:00.000000+00:00",
  created_at: "2026-03-26T10:00:00.000000+00:00"
}
```

**Indexes:**
- `mobile` (unique)

---

## Sample Queries

### Get all pending feedback for a temple
```javascript
db.feedback.find({
  temple_id: "temple-uuid",
  status: "Pending"
}).sort({ created_at: -1 })
```

### Get officer's assigned feedback
```javascript
db.feedback.find({
  assigned_officer_id: "officer-uuid"
}).sort({ created_at: -1 })
```

### Get temple-wise feedback count
```javascript
db.feedback.aggregate([
  { $group: { 
    _id: "$temple_name", 
    count: { $sum: 1 } 
  }},
  { $sort: { count: -1 } }
])
```

### Get feedback with video
```javascript
db.feedback.find({
  video_path: { $exists: true, $ne: null }
})
```

---

## Default Data

### Default Temples
```javascript
[
  {
    "name": "Bhadrachalam Devasthanam",
    "location": "Bhadrachalam, Telangana",
    "email": "bhadrachalam@temple.com"
  },
  {
    "name": "Vemulawada Devasthanam",
    "location": "Vemulawada, Telangana",
    "email": "vemulawada@temple.com"
  },
  {
    "name": "Yadagirigutta",
    "location": "Yadagirigutta, Telangana",
    "email": "yadagirigutta@temple.com"
  }
]
```

### Default Services
```javascript
[
  { "name": "Annadhanam", "order": 1 },
  { "name": "Darshan", "order": 2 },
  { "name": "Prasadam", "order": 3 },
  { "name": "Pooja", "order": 4 },
  { "name": "Donation", "order": 5 },
  { "name": "Other", "order": 6 },
  { "name": "General", "order": 7 }
]
```

---

## Backup & Restore

### Backup All Collections
```bash
mongodump --db temple_feedback_db --out /backup/temple-feedback-$(date +%Y%m%d)
```

### Restore Database
```bash
mongorestore --db temple_feedback_db /backup/temple-feedback-20260326
```

### Backup Specific Collection
```bash
mongodump --db temple_feedback_db --collection feedback --out /backup/
```

---

**Note:** Always exclude `_id` field when querying through the API to avoid JSON serialization errors with MongoDB ObjectId.
