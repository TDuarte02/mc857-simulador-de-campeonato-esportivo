package com.mc857.copaamerica.state

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.mc857.copaamerica.data.ApiException
import com.mc857.copaamerica.data.CopaApi
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.logic.nextStep
import com.mc857.copaamerica.domain.model.Availability
import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.Preset
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.nav.Screen
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Job
import kotlinx.coroutines.job
import kotlinx.coroutines.launch

/** A failed request, in words for the user. */
data class UiError(
    val message: String,
    val retry: (() -> Unit)? = null,
    /** The session is unusable: the only way forward is a new tournament. */
    val mustRestart: Boolean = false,
)

/**
 * Navigation and tournament state. The server is the source of truth: every
 * action calls the API and then shows what it answered. One request runs at a
 * time; [busy] blocks the UI meanwhile.
 */
class TournamentController(
    private val api: CopaApi,
    private val scope: CoroutineScope,
    private val serverAddress: String,
) {
    var stack by mutableStateOf(listOf(Screen.HOME))
        private set
    var busy by mutableStateOf(false)
        private set
    var error by mutableStateOf<UiError?>(null)
        private set

    var squads by mutableStateOf<List<Squad>>(emptyList())
        private set
    var squad by mutableStateOf<Squad?>(null)
        private set
    var players by mutableStateOf<List<Player>>(emptyList())
        private set
    var presets by mutableStateOf<List<Preset>>(emptyList())
        private set
    var callUp by mutableStateOf<Set<Int>>(emptySet())
        private set
    var draw by mutableStateOf<Draw?>(null)
        private set
    var history by mutableStateOf<History?>(null)
        private set
    var availability by mutableStateOf<Availability?>(null)
        private set
    var lineup by mutableStateOf<List<Player?>>(emptyList())
    var formKey by mutableStateOf(FormKey.F442)
    private var lastMatchId by mutableStateOf<String?>(null)

    private var sessionId: String? = null
    private var job: Job? = null

    val screen get() = stack.last()

    val next: NextStep?
        get() {
            val currentDraw = draw ?: return null
            val currentHistory = history ?: return null
            return nextStep(currentDraw, currentHistory)
        }

    /** The user's most recently played match, shown on the result screen. */
    val lastMatch: Match?
        get() = history?.matches?.firstOrNull { it.id == lastMatchId }

    fun openTeamSelection() {
        navigate(Screen.TEAM_SELECTION)
        if (squads.isEmpty()) loadSquads()
    }

    fun loadSquads() = request { squads = api.squads() }

    fun selectSquad(selected: Squad) = request {
        val loadedPlayers = api.players(selected.id)
        presets = api.presets(selected.id)
        players = loadedPlayers
        if (squad?.id != selected.id) callUp = emptySet()
        squad = selected
        navigate(Screen.SQUAD_BUILDER)
    }

    /** Asks the server for the preset again, so "random" draws a new squad each time. */
    fun applyPreset(presetId: String, apply: (List<Player>) -> Unit) {
        val squadId = squad?.id ?: return
        request {
            presets = api.presets(squadId)
            presets.firstOrNull { it.id == presetId }?.let { apply(it.players) }
        }
    }

    fun confirmCallUp(playerIds: Set<Int>) {
        val squadId = squad?.id ?: return
        request {
            val session = sessionId ?: api.createSession().also { sessionId = it }
            api.callUp(session, squadId, playerIds.toList())
            callUp = playerIds
            lineup = emptyList()
            navigate(Screen.DRAW_SETUP)
        }
    }

    fun runDraw() = withSession { session ->
        val drawn = api.draw(session)
        history = api.history(session)
        draw = drawn
    }

    /** Loads who is fit and goes to the lineup of the next match. */
    fun openLineup() = withSession { session ->
        val current = api.availability(session)
        val fit = current.available.associate { it.id to it.player }
        lineup = lineup.map { player -> player?.let { fit[it.id] } }
        availability = current
        stack = listOf(Screen.HOME, hubScreen(), Screen.PRE_MATCH)
    }

    fun playMatch() {
        val match = (next as? NextStep.Play)?.match ?: return
        val ids = lineup.filterNotNull().map { it.id }
        val formation = formKey.label
        withSession { session ->
            var latest = api.history(session)
            // A retry after a lost response must not play the following round.
            if (latest.matches.none { it.id == match.id }) {
                api.simulate(session, ids, formation)
                latest = api.history(session)
            }
            history = latest
            lastMatchId = match.id
            stack = listOf(Screen.HOME, Screen.MATCH_RESULT)
        }
    }

    fun continueAfterMatch() {
        stack = listOf(Screen.HOME, hubScreen())
    }

    fun drawPlayoffs() = withSession { session ->
        api.playoffsDraw(session)
        history = api.history(session)
        stack = listOf(Screen.HOME, Screen.BRACKET)
    }

    fun simulateRest() = withSession { session ->
        api.simulateAll(session)
        history = api.history(session)
        stack = listOf(Screen.HOME, Screen.PHASE_OVERVIEW)
    }

    fun back() {
        if (stack.size > 1) stack = stack.dropLast(1)
    }

    fun dismissError() {
        error = null
    }

    /** New tournament: forgets the session; an in-flight request is cancelled. */
    fun reset() {
        job?.cancel()
        job = null
        busy = false
        error = null
        stack = listOf(Screen.HOME)
        sessionId = null
        squad = null
        players = emptyList()
        presets = emptyList()
        callUp = emptySet()
        draw = null
        history = null
        availability = null
        lineup = emptyList()
        formKey = FormKey.F442
        lastMatchId = null
    }

    /** The screen the tournament rests on between matches. */
    private fun hubScreen(): Screen {
        val phase = history?.phase
        return when (val step = next) {
            is NextStep.Play -> when (step.match.stage) {
                Stage.GROUP -> Screen.GROUP_STAGE
                Stage.THIRD_PLACE -> Screen.ELIMINATION
                else -> Screen.BRACKET
            }
            NextStep.DrawPlayoffs -> Screen.GROUP_STAGE
            NextStep.Eliminated ->
                if (phase == SessionPhase.PLAYOFFS_PENDING) Screen.GROUP_STAGE else Screen.ELIMINATION
            NextStep.Finished -> Screen.PHASE_OVERVIEW
            null -> Screen.HOME
        }
    }

    private fun navigate(target: Screen) {
        stack = stack + target
    }

    private fun withSession(block: suspend (String) -> Unit) {
        val session = sessionId ?: return
        request { block(session) }
    }

    private fun request(block: suspend () -> Unit) {
        if (busy) return
        busy = true
        error = null
        val launched = scope.launch(start = CoroutineStart.LAZY) {
            val self = coroutineContext.job
            try {
                block()
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (failure: Throwable) {
                // Throwable: on the web, Ktor reports a failed fetch as an Error.
                error = describe(failure) { request(block) }
            } finally {
                if (job === self) busy = false
            }
        }
        job = launched
        launched.start()
    }

    private fun describe(failure: Throwable, retry: () -> Unit): UiError {
        if (failure !is ApiException) {
            return UiError("Não foi possível falar com o servidor em $serverAddress.", retry)
        }
        if (failure.code == "SESSION_NOT_FOUND") {
            return UiError("Este torneio não existe mais no servidor. Comece um novo.", mustRestart = true)
        }
        val message = when (failure.code) {
            "INVALID_CALL_UP" -> "O servidor recusou a convocação."
            "INVALID_LINEUP" -> "O servidor recusou a escalação."
            "PLAYER_UNAVAILABLE" -> "Há um jogador suspenso ou lesionado na escalação."
            else -> "O servidor recusou a ação (${failure.code})."
        }
        return UiError(message, retry = retry.takeIf { failure.status >= 500 })
    }
}
