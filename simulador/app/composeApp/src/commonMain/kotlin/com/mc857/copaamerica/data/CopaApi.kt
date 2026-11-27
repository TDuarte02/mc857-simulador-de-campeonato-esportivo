package com.mc857.copaamerica.data

import com.mc857.copaamerica.domain.model.Availability
import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.Preset
import com.mc857.copaamerica.domain.model.SessionState
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.TournamentMode
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.request.HttpRequestBuilder
import io.ktor.client.request.header
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.encodeURLPathPart
import io.ktor.http.isSuccess
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** An error the API answered with: `{"error": {"code", "message"}}`. */
class ApiException(val status: Int, val code: String, message: String) : Exception(message)

@Serializable
private data class CreateSessionRequest(val mode: TournamentMode)

@Serializable
private data class SessionResponse(val sessionId: String)

@Serializable
private data class SessionStateResponse(val session: SessionState)

@Serializable
private data class SquadsResponse(val squads: List<Squad>)

@Serializable
private data class PlayersResponse(val players: List<Player>)

@Serializable
private data class PresetsResponse(val presets: List<Preset>)

@Serializable
private data class CallUpRequest(val squad: String, val players: List<Int>)

@Serializable
private data class SimulateRequest(val players: List<Int>, val formation: String)

@Serializable
private data class ErrorBody(val code: String, val message: String)

@Serializable
private data class ErrorResponse(val error: ErrorBody)

private val apiJson = Json { ignoreUnknownKeys = true }

/**
 * HTTP client for simulador/server. Failures are an [ApiException] when the
 * server answered with an error, or the engine's own exception when it could
 * not be reached.
 */
class CopaApi(private val baseUrl: String, private val apiKey: String = "") {
    private val client = HttpClient {
        install(ContentNegotiation) { json(apiJson) }
        install(HttpTimeout) { requestTimeoutMillis = 15_000 }
        defaultRequest {
            url("$baseUrl/")
            if (apiKey.isNotEmpty()) header("x-api-key", apiKey)
        }
    }

    suspend fun createSession(mode: TournamentMode): String =
        post("session") { jsonBody(CreateSessionRequest(mode)) }.body<SessionResponse>().sessionId

    suspend fun session(sessionId: String): SessionState =
        get("session/${sessionId.encodeURLPathPart()}").body<SessionStateResponse>().session

    suspend fun squads(): List<Squad> = get("squads").body<SquadsResponse>().squads

    suspend fun players(squadId: String): List<Player> =
        get("${squadId.encodeURLPathPart()}/players").body<PlayersResponse>().players

    suspend fun presets(squadId: String): List<Preset> =
        get("${squadId.encodeURLPathPart()}/presets").body<PresetsResponse>().presets

    suspend fun callUp(sessionId: String, squadId: String, playerIds: List<Int>) {
        post("$sessionId/call-up") { jsonBody(CallUpRequest(squadId, playerIds)) }
    }

    suspend fun draw(sessionId: String): Draw = get("$sessionId/draw").body()

    suspend fun availability(sessionId: String): Availability = get("$sessionId/available-players").body()

    /** Plays the user's match of the current round. The result shows up in [history]. */
    suspend fun simulate(sessionId: String, playerIds: List<Int>, formation: String) {
        post("$sessionId/simulate") { jsonBody(SimulateRequest(playerIds, formation)) }
    }

    suspend fun playoffsDraw(sessionId: String) {
        get("$sessionId/playoffs-draw")
    }

    suspend fun simulateAll(sessionId: String) {
        post("$sessionId/simulate-all")
    }

    suspend fun history(sessionId: String): History = get("$sessionId/history").body()

    private suspend fun get(path: String): HttpResponse = client.get(path).orThrow()

    private suspend fun post(path: String, block: HttpRequestBuilder.() -> Unit = {}): HttpResponse =
        client.post(path, block).orThrow()

    private inline fun <reified T> HttpRequestBuilder.jsonBody(body: T) {
        contentType(ContentType.Application.Json)
        setBody(body)
    }

    private suspend fun HttpResponse.orThrow(): HttpResponse {
        if (status.isSuccess()) return this
        val error = try {
            body<ErrorResponse>().error
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            ErrorBody("HTTP_${status.value}", "O servidor respondeu ${status.value}.")
        }
        throw ApiException(status.value, error.code, error.message)
    }
}
