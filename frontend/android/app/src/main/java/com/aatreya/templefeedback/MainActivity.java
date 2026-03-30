package com.aatreya.templefeedback;

import android.os.Bundle;
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
	}
}
