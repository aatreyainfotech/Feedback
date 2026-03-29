# Temple Feedback System - Android APK Build Guide

## Prerequisites
1. **Android Studio** installed on your computer
2. **Java JDK 17** or higher
3. **Node.js 18+** and **Yarn**

## Quick Build Steps

### Option 1: Build on Your Computer

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sriaatreya/temple-feedback-system.git
   cd temple-feedback-system/frontend
   ```

2. **Install dependencies:**
   ```bash
   yarn install
   ```

3. **Update the API URL for production:**
   Edit `frontend/.env` and set your production backend URL:
   ```
   REACT_APP_BACKEND_URL=https://your-production-server.com
   ```

4. **Build the web app:**
   ```bash
   yarn build
   ```

5. **Sync with Android:**
   ```bash
   npx cap sync android
   ```

6. **Open in Android Studio:**
   ```bash
   npx cap open android
   ```

7. **In Android Studio:**
   - Wait for Gradle sync to complete
   - Go to **Build → Generate Signed Bundle / APK**
   - Select **APK**
   - Create or use existing keystore
   - Choose **release** build variant
   - Click **Finish**

8. **APK Location:**
   The APK will be generated at:
   ```
   frontend/android/app/build/outputs/apk/release/app-release.apk
   ```

### Option 2: Build Debug APK (Quick Test)

1. After step 6 above, in Android Studio:
   - Go to **Build → Build Bundle(s) / APK(s) → Build APK(s)**
   - Debug APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

## App Configuration

- **App Name:** Temple Feedback
- **Package ID:** com.aatreya.templefeedback
- **Min SDK:** 22 (Android 5.1)
- **Target SDK:** 34 (Android 14)

## Permissions (Configured)

The app has the following permissions:
- `INTERNET` - For API communication
- `CAMERA` - For video recording
- `RECORD_AUDIO` - For video audio
- `READ_EXTERNAL_STORAGE` - For file access
- `WRITE_EXTERNAL_STORAGE` - For saving files

## Kiosk Mode Setup (For Tablets)

After installing the APK on a tablet:

1. **Set as Default Launcher:**
   - Go to Settings → Apps → Default apps → Home app
   - Select "Temple Feedback"

2. **Pin the App:**
   - Open Temple Feedback app
   - Go to Recent Apps
   - Tap the app icon → Select "Pin"

3. **Use Fully Kiosk Browser (Recommended):**
   - Download "Fully Kiosk Browser" from Play Store
   - Set the URL to your deployed web app
   - Enable kiosk mode in settings

## Troubleshooting

### Camera not working
- Ensure camera permissions are granted in device settings
- Check that HTTPS is being used (required for camera access)

### Build fails
- Run `npx cap sync android` before opening in Android Studio
- Clear Gradle cache: `./gradlew clean` in android folder

### App crashes on launch
- Check `frontend/.env` has correct API URL
- Rebuild: `yarn build && npx cap sync android`

## Release Checklist

- [ ] Update version in `android/app/build.gradle`
- [ ] Test on multiple Android devices
- [ ] Verify camera recording works
- [ ] Test feedback submission flow
- [ ] Verify temple registration persists

## Support

Developed by **Aatreya Infotech**
For Telangana Endowment Department
