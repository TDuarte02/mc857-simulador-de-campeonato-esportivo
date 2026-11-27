package com.mc857.copaamerica.platform

/** Address of the API (simulador/server) as seen from each platform. */
expect val apiBaseUrl: String

/**
 * Sent as the x-api-key header required by the API Gateway. Empty on the web,
 * where the host that serves the page adds it.
 */
expect val apiKey: String
