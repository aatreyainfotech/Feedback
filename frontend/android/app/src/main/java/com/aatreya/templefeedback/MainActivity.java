package com.aatreya.templefeedback;

import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebSettings;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		// Samsung and newer Android devices have stricter WebView policies.
		// Explicitly allow mixed content so HTTP backend calls succeed.
		WebSettings settings = getBridge().getWebView().getSettings();
		settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
		settings.setJavaScriptEnabled(true);
		settings.setDomStorageEnabled(true);

		// Disable Safe Browsing — it can block LAN HTTP URLs on Samsung One UI
		if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
			settings.setSafeBrowsingEnabled(false);
		}

		// Kiosk tablets stay on 24x7 and autoplay the screensaver without a tap.
		getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
		settings.setMediaPlaybackRequiresUserGesture(false);
	}

	@Override
	public void onWindowFocusChanged(boolean hasFocus) {
		super.onWindowFocusChanged(hasFocus);
		if (hasFocus) {
			// Hide the status and navigation bars; they return briefly on an edge swipe.
			getWindow().getDecorView().setSystemUiVisibility(
				View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
					| View.SYSTEM_UI_FLAG_LAYOUT_STABLE
					| View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
					| View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
					| View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
					| View.SYSTEM_UI_FLAG_FULLSCREEN
			);
		}
	}
}
