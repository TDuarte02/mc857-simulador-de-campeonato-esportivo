package com.mc857.copaamerica.platform

import kotlinx.browser.window

// The page calls /api on its own host, which forwards to the API Gateway with
// the key: the webpack dev server locally (webpack.config.d/apiProxy.js) and a
// Netlify edge function in production (netlify/edge-functions/api.ts). Same
// origin, so the browser needs no CORS, and the key never reaches the browser.
actual val apiBaseUrl: String = "${window.location.origin}/api"

actual val apiKey: String = ""
