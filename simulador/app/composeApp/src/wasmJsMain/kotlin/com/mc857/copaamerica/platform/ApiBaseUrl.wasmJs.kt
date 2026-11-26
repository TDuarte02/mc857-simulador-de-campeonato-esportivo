package com.mc857.copaamerica.platform

import kotlinx.browser.window

// Same machine that serves the page, on the API's port.
actual val apiBaseUrl: String = "http://${window.location.hostname}:5000"
