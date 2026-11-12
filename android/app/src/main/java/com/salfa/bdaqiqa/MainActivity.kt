package com.salfa.bdaqiqa

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.*
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging

class MainActivity : AppCompatActivity() {

    private lateinit var web: WebView
    private lateinit var swipe: SwipeRefreshLayout
    private lateinit var progress: ProgressBar
    private lateinit var offline: LinearLayout

    private val siteHost: String by lazy { Uri.parse(BuildConfig.SITE_URL).host ?: "" }

    private val askNotif = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        web = findViewById(R.id.web)
        swipe = findViewById(R.id.swipe)
        progress = findViewById(R.id.progress)
        offline = findViewById(R.id.offline)

        swipe.setColorSchemeColors(ContextCompat.getColor(this, R.color.brand_orange))
        swipe.setProgressBackgroundColorSchemeColor(ContextCompat.getColor(this, R.color.brand_black))
        swipe.setOnRefreshListener { web.reload() }
        // Only allow pull-to-refresh when the page is scrolled to the top
        swipe.setOnChildScrollUpCallback { _, _ -> web.scrollY > 0 }

        findViewById<Button>(R.id.retry).setOnClickListener {
            offline.visibility = View.GONE
            web.reload()
        }

        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            loadWithOverviewMode = true
            useWideViewPort = true
            userAgentString = "$userAgentString SalfaApp/${BuildConfig.VERSION_NAME}"
        }

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                val inside = (uri.scheme == "https" || uri.scheme == "http") &&
                        (uri.host == siteHost || uri.host?.endsWith(".$siteHost") == true)
                if (inside) return false
                // Instagram, TikTok, WhatsApp... open in their own apps
                return try {
                    startActivity(Intent(Intent.ACTION_VIEW, uri)); true
                } catch (e: Exception) { true }
            }

            override fun onPageFinished(view: WebView, url: String) {
                swipe.isRefreshing = false
            }

            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (request.isForMainFrame) {
                    swipe.isRefreshing = false
                    offline.visibility = View.VISIBLE
                }
            }
        }

        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
            }
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) web.goBack() else finish()
            }
        })

        if (savedInstanceState != null) web.restoreState(savedInstanceState)
        else web.loadUrl(urlFromIntent(intent) ?: BuildConfig.SITE_URL)

        setupNotifications()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        urlFromIntent(intent)?.let { web.loadUrl(it) }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    /** A notification can carry a "url" (e.g. the new post) to open inside the app. */
    private fun urlFromIntent(intent: Intent?): String? {
        val url = intent?.getStringExtra("url") ?: return null
        val host = Uri.parse(url).host ?: return null
        return if (host == siteHost) url else null
    }

    private fun setupNotifications() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                PushService.CHANNEL_ID, getString(R.string.channel_name),
                NotificationManager.IMPORTANCE_HIGH
            ).apply { description = getString(R.string.channel_desc) }
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            askNotif.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        // Firebase is only present when google-services.json was added at build time
        if (FirebaseApp.getApps(this).isNotEmpty()) {
            try {
                FirebaseMessaging.getInstance().subscribeToTopic(PushService.TOPIC)
            } catch (_: Exception) { }
        }
    }
}
