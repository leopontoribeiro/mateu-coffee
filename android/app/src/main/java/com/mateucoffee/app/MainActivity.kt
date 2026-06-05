package com.mateucoffee.app

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.*
import android.widget.ProgressBar
import android.widget.RelativeLayout

class MainActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar

    // ← COLOQUE AQUI A URL DO APP APÓS DEPLOY
    private val APP_URL = "https://SEU-APP.streamlit.app"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Layout dinâmico: WebView + barra de progresso
        val layout = RelativeLayout(this)
        layout.setBackgroundColor(0xFF0A0A0A.toInt())

        progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal)
        progressBar.id = View.generateViewId()
        progressBar.max = 100
        progressBar.progressTintList = android.content.res.ColorStateList.valueOf(0xFFE8722E.toInt())
        val pbParams = RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.MATCH_PARENT, 8
        )
        pbParams.addRule(RelativeLayout.ALIGN_PARENT_TOP)
        layout.addView(progressBar, pbParams)

        webView = WebView(this)
        val wvParams = RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.MATCH_PARENT,
            RelativeLayout.LayoutParams.MATCH_PARENT
        )
        wvParams.addRule(RelativeLayout.BELOW, progressBar.id)
        layout.addView(webView, wvParams)

        setContentView(layout)

        // Configurações do WebView
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            useWideViewPort = true
            loadWithOverviewMode = true
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            cacheMode = WebSettings.LOAD_DEFAULT
            userAgentString = userAgentString + " MateuCoffeeApp/1.0"
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                // Links externos abrem no browser nativo
                if (!url.startsWith(APP_URL) && (url.startsWith("http://") || url.startsWith("https://"))) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    return true
                }
                return false
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                progressBar.visibility = View.GONE
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progressBar.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
                progressBar.progress = newProgress
            }
        }

        webView.loadUrl(APP_URL)
    }

    // Botão voltar navega dentro do WebView
    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }
}
