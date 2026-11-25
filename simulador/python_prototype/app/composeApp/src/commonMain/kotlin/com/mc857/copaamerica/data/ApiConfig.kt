package com.mc857.copaamerica.data

/**
 * URL base da API. Defina no ponto de entrada de cada plataforma, antes de abrir o app:
 * Android emulador `http://10.0.2.2:8000`, iOS/web local `http://localhost:8000`,
 * produção `https://…` (URL a definir).
 */
object ApiConfig {
    var baseUrl: String = "http://localhost:8000"
}
