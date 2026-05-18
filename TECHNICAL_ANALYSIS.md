# Technical Deep Dive: MIME Type Issue Fix

## Problem Analysis

### Error Message
```
Refused to execute script from 'https://fb.aatreya.org/static/js/main.791f328f.js' 
because its MIME type ('text/html') is not executable, and strict MIME type checking is enabled.
```

### Root Cause
Azure Static Web Apps was serving JavaScript files with `Content-Type: text/html` header instead of `application/javascript`.

### Why This Happened
The routing configuration in `staticwebapp.config.json` had an incomplete exclude pattern that failed to properly exclude `/static/*` files from the navigation fallback rewrite rule.

#### Before (BROKEN):
```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": ["/static/*", "/*.{css,js,ico,png,jpg,jpeg,svg,webmanifest,txt}"]
  },
  "responseOverrides": {
    "404": {
      "rewrite": "/index.html",
      "statusCode": 200
    }
  },
  "globalHeaders": {
    "Cache-Control": "no-cache"
  }
}
```

**Problem**: The pattern `/*.{css,js,...}` only matches files in the ROOT directory (`/main.js`) but NOT files in subdirectories (`/static/js/main.xxx.js`). When a request came in for `/static/js/main.791f328f.js`, Azure incorrectly rewrote it to `/index.html` and served HTML content.

## Solution Implementation

### After (FIXED):
```json
{
  "navigationFallback": {
    "rewrite": "/index.html",
    "exclude": [
      "/static/*",
      "/favicon.ico",
      "/manifest.webmanifest",
      "/*.{css,js,ico,png,jpg,jpeg,svg,webmanifest,txt}"
    ]
  },
  "responseOverrides": {
    "404": {
      "rewrite": "/index.html",
      "statusCode": 200
    }
  },
  "mimeTypes": {
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".json": "application/json",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2"
  },
  "routes": [
    {
      "route": "/static/*",
      "headers": {
        "cache-control": "public, max-age=31536000, immutable"
      }
    }
  ],
  "globalHeaders": {
    "Cache-Control": "no-cache"
  }
}
```

### Key Improvements

#### 1. **Explicit MIME Types Section**
```json
"mimeTypes": {
  ".js": "application/javascript",
  ".css": "text/css",
  ...
}
```
Ensures Azure explicitly serves files with correct `Content-Type` headers, overriding any default behavior.

#### 2. **Improved Exclude Patterns**
```json
"exclude": [
  "/static/*",              // Exclude all static files
  "/favicon.ico",           // Favicon
  "/manifest.webmanifest",  // PWA manifest
  "/*.{...}"                // Root-level resources
]
```
More explicit and comprehensive exclude list.

#### 3. **Cache Optimization**
```json
"routes": [
  {
    "route": "/static/*",
    "headers": {
      "cache-control": "public, max-age=31536000, immutable"
    }
  }
]
```
Sets 1-year cache for immutable assets (files with content hash in name like `main.791f328f.js`).

## Request Flow Analysis

### Before Fix (BROKEN)
```
Browser: GET /static/js/main.791f328f.js
   ↓
Azure Static Web Apps:
  - Check navigationFallback.exclude pattern
  - Pattern "/*.{js,...}" doesn't match /static/js/main.791f328f.js ❌
  - Apply navigationFallback.rewrite → /index.html
   ↓
Azure Static Web Apps: 
  - Serve /index.html (HTML content)
  - Default Content-Type: text/html
   ↓
Browser: 
  - Receives HTML with text/html MIME type
  - Tries to execute as JavaScript
  - ❌ BLOCKED by strict MIME type checking
   ↓
Console Error: "Refused to execute script..."
Result: ❌ JavaScript doesn't load, React app doesn't initialize, blank page
```

### After Fix (WORKING)
```
Browser: GET /static/js/main.791f328f.js
   ↓
Azure Static Web Apps:
  - Check navigationFallback.exclude pattern
  - Pattern "/static/*" matches /static/js/main.791f328f.js ✅
  - Check mimeTypes section
  - ".js" → application/javascript ✅
   ↓
Azure Static Web Apps:
  - Serve /static/js/main.791f328f.js (actual JS file)
  - Content-Type: application/javascript ✅
   ↓
Browser:
  - Receives JavaScript with correct MIME type
  - ✅ Loads and executes script
   ↓
Result: ✅ React app initializes, page displays login screen
```

## Deployment

### Changes to Deploy
1. **frontend/public/staticwebapp.config.json**
   - This is the source file (committed to git)
   
2. **frontend/build/staticwebapp.config.json**
   - This is deployed to Azure (generated during build)
   - Must be updated to match source

### Deployment Trigger
- Push to `main` branch with changes to frontend files
- GitHub Actions workflow: `azure-static-web-apps-yellow-ocean-07bef8000.yml`
- Automatically triggers Azure Static Web Apps deployment

### Expected Timeline
1. **Commit & Push**: Immediate
2. **GitHub Actions**: 2-3 minutes
   - Checkout code
   - Detect frontend changes
   - Run `yarn build` (generates build/ directory)
   - Deploy to Azure
3. **Live**: 1-2 minutes after GitHub Actions completes
   - DNS/CDN may cache for up to 5 minutes

## Verification

### Check MIME Types in Browser
1. Open: https://fb.aatreya.org/
2. Press F12 (Developer Tools)
3. Go to Network tab
4. Look for `main.xxx.js` file
5. Click on it
6. Check "Response Headers"
7. Should see:
   ```
   Content-Type: application/javascript
   ```
   NOT `text/html`

### Check Azure Configuration
1. Azure Portal: Static Web Apps > yellow-ocean (or your resource name)
2. Check deployment history
3. Verify latest deployment status: ✅ Succeeded
4. Confirm date/time matches your git push

## Prevention for Future

### Best Practices
1. **Always include `mimeTypes` section** in staticwebapp.config.json
2. **Be explicit with exclude patterns** - don't rely on glob patterns alone
3. **Test locally with Azure Static Web Apps CLI** before deploying
4. **Monitor deployment pipeline** - check GitHub Actions for failures

### Azure Static Web Apps CLI Testing
```bash
# Install Azure Static Web Apps CLI
npm install -g @azure/static-web-apps-cli

# Test locally (simulates Azure routing)
swa start ./build
```

This simulates Azure Static Web Apps locally, allowing you to test static file serving before deployment.

---

## Technical References

- [Azure Static Web Apps Route Config](https://learn.microsoft.com/en-us/azure/static-web-apps/configuration#define-routes)
- [MIME Types Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types)
- [Azure Static Web Apps Best Practices](https://learn.microsoft.com/en-us/azure/static-web-apps/configuration-overview)

---

**Issue Fixed**: 2026-05-18
**Status**: Ready for Deployment
