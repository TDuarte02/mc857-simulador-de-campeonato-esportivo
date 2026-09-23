package com.mc857.copaamerica.platform

/** Opens the platform share sheet with the given text. Mirrors the `navigator.share` fallback in App.tsx (e.g. :2092-2111). */
expect fun shareText(title: String, text: String)
