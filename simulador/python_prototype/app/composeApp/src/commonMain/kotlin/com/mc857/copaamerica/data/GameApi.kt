package com.mc857.copaamerica.data

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

/** Erro da API (`{code, message}`) ou de rede (`status = 0`, `code = "network"`). */
class ApiException(val status: Int, val code: String, override val message: String) : Exception(message) {
    val isGameExpired get() = status == 404 && code == "game_not_found"
}

/** Cliente HTTP da API `/v1`. O app não implementa regra de domínio. */
class GameApi(
    private val baseUrl: () -> String = { ApiConfig.baseUrl },
    private val client: HttpClient = HttpClient {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true; encodeDefaults = true }) }
    },
) {
    private fun url(path: String) = baseUrl().trimEnd('/') + "/v1" + path

    private suspend inline fun <reified T> call(block: () -> HttpResponse): T {
        val response = try {
            block()
        } catch (e: Exception) {
            throw ApiException(0, "network", e.message ?: "Falha de rede.")
        }
        if (response.status.isSuccess()) return response.body()
        val err = runCatching { response.body<ApiErrorBody>() }.getOrNull()
        throw ApiException(response.status.value, err?.code ?: "http_${response.status.value}", err?.message ?: response.status.description)
    }

    suspend fun nations(): List<NationDto> = call { client.get(url("/nations")) }
    suspend fun players(nation: String): PoolDto = call { client.get(url("/nations/$nation/players")) }

    suspend fun createGame(userTeam: String, squad: List<String>, seed: Int? = null): CreateGameDto = call {
        client.post(url("/games")) { contentType(ContentType.Application.Json); setBody(CreateGameRequest(userTeam, squad, seed)) }
    }

    suspend fun game(id: String): GameStateDto = call { client.get(url("/games/$id")) }
    suspend fun advance(id: String): AdvanceDto = call { client.post(url("/games/$id/advance")) }

    suspend fun startMatch(id: String, picks: List<PickDto>? = null): ActiveMatchDto = call {
        client.post(url("/games/$id/match/start")) { contentType(ContentType.Application.Json); setBody(StartMatchRequest(picks)) }
    }

    suspend fun changeLineup(id: String, picks: List<PickDto>, formation: List<String>? = null): ActiveMatchDto = call {
        client.post(url("/games/$id/match/lineup")) { contentType(ContentType.Application.Json); setBody(LineupRequest(picks, formation)) }
    }

    suspend fun play(id: String, until: String): PlayDto = call {
        client.post(url("/games/$id/match/play")) { contentType(ContentType.Application.Json); setBody(PlayRequest(until)) }
    }

    suspend fun secondHalf(id: String): ActiveMatchDto = call { client.post(url("/games/$id/match/second-half")) }
    suspend fun cancelMatch(id: String): GameStateDto = call { client.delete(url("/games/$id/match")) }
    suspend fun simulate(id: String): GameStateDto = call { client.post(url("/games/$id/simulate")) }
    suspend fun result(id: String): FinalResultDto = call { client.get(url("/games/$id/result")) }
    suspend fun matchView(id: String, matchId: String): MatchViewDto = call { client.get(url("/games/$id/matches/$matchId")) }
}
