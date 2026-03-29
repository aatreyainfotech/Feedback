# 🏛️ Temple Feedback System - All URLs

## 📱 Public Access (For Devotees)

### Tablet Setup (First Time)
**URL:** https://temple-feedback-1.preview.emergentagent.com/setup-temple

**Purpose:** Register tablet with temple email
**Credentials:**
- Bhadrachalam: `bhadrachalam@temple.com`
- Vemulawada: `vemulawada@temple.com`
- Yadagirigutta: `yadagirigutta@temple.com`

---

### Feedback Submission (After Setup)
**URL:** https://temple-feedback-1.preview.emergentagent.com/submit-feedback

**Purpose:** Devotees submit feedback with video recording
**Flow:**
1. Fill name, mobile, service, rating
2. Record video (60 seconds max)
3. Submit
4. See success screen with Transaction ID
5. Choose: "Back to Display" or "Create New Feedback"

---

### Display Screen (Temple TV)
**URL:** https://temple-feedback-1.preview.emergentagent.com/display

**Purpose:** Live feedback display on temple TV
**Features:**
- Shows recent 20 feedback items
- Auto-refresh every 10 seconds
- Full screen display
- Color-coded status

---

## 👨‍💼 Super Admin Access

### Admin Login
**URL:** https://temple-feedback-1.preview.emergentagent.com/login

**Credentials:**
- Email: `admin@temple.com`
- Password: `admin123`

**After Login, Access:**

#### Dashboard
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/dashboard
- View statistics
- Temple-wise feedback chart
- Total counts

#### Temples Management
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/temples
- Add new temple
- Edit temple (name, location, email)
- Delete temple
- Assign officers

#### Officers Management
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/officers
- Create new officer
- Assign temple
- Delete officer

#### Feedback Monitoring
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/feedback
- View all feedback
- Filter by status/temple
- Watch videos
- View details

#### WhatsApp Logs
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/whatsapp-logs
- View all messages sent
- Delivery status
- Message history

#### Reports
**URL:** https://temple-feedback-1.preview.emergentagent.com/admin/reports
- Generate PDF reports
- Export CSV data
- Filter by temple
- View statistics

---

## 👮 Officer Access

### Officer Login
**URL:** https://temple-feedback-1.preview.emergentagent.com/officer/login

**Test Credentials:**
- Email: `officer@temple.com`
- Password: `officer123`
- Temple: Bhadrachalam Devasthanam

**After Login:**

#### Officer Dashboard
**URL:** https://temple-feedback-1.preview.emergentagent.com/officer/dashboard
- View assigned temple's feedback only
- Update feedback status
- Add officer notes
- Send WhatsApp replies

---

## 🔄 User Flow Summary

### Devotee Experience
1. **First Time:** /setup-temple → Enter temple email → Tablet registered
2. **Submit Feedback:** /submit-feedback → Fill form → Record video → Submit
3. **Success Screen:** 
   - "Successfully submitted your feedback, thank you for visiting"
   - Shows temple name
   - Shows Transaction ID (e.g., TF00001)
   - Two buttons:
     - **Back to Display** → Goes to /display
     - **Create New Feedback** → Clear form, submit again
4. **Display Screen:** /display → See all recent feedback

### Admin Experience
1. Login → /admin/dashboard
2. Manage temples → /admin/temples
3. Create officers → /admin/officers
4. Monitor feedback → /admin/feedback
5. View WhatsApp logs → /admin/whatsapp-logs
6. Generate reports → /admin/reports

### Officer Experience
1. Login → /officer/dashboard
2. View temple-specific complaints
3. Watch videos
4. Update status (Pending/In Progress/Resolved/Rejected)
5. Add notes
6. WhatsApp auto-sent to devotee

---

## 📊 Quick Access Summary

| Role | Main URL | Login Credentials |
|------|----------|------------------|
| **Devotee** | /submit-feedback | No login required |
| **Temple Setup** | /setup-temple | Temple email |
| **Super Admin** | /login | admin@temple.com / admin123 |
| **Officer** | /officer/login | officer@temple.com / officer123 |
| **Display** | /display | No login required |

---

## 🎯 Most Important URLs

**For Daily Use:**
1. **Feedback Form:** https://temple-feedback-1.preview.emergentagent.com/submit-feedback
2. **Admin Dashboard:** https://temple-feedback-1.preview.emergentagent.com/admin/dashboard
3. **Display Screen:** https://temple-feedback-1.preview.emergentagent.com/display

**For Setup:**
1. **Tablet Setup:** https://temple-feedback-1.preview.emergentagent.com/setup-temple
2. **Admin Login:** https://temple-feedback-1.preview.emergentagent.com/login

---

## 🔐 Security Notes

- Admin credentials should be changed in production
- Temple emails are used for tablet registration
- Officers can only see their temple's data
- JWTs expire after 7 days
- Tablets store registration in localStorage

---

## 📱 Tablet QR Codes (Recommended)

Create QR codes for each temple:
1. **Bhadrachalam Tablet:** /submit-feedback (after setup with bhadrachalam@temple.com)
2. **Vemulawada Tablet:** /submit-feedback (after setup with vemulawada@temple.com)
3. **Yadagirigutta Tablet:** /submit-feedback (after setup with yadagirigutta@temple.com)

Print and place near temple counters for easy access!

---

**System Status:** ✅ Fully Operational
**Last Updated:** March 26, 2026
