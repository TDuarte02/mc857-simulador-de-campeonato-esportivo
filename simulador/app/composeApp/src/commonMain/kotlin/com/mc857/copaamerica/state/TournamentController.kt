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
import com.mc857.copaamerica.domain.model.TournamentMode
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

/** The server created a full cup when asked for a fast one: it predates fast mode. */
private class FastModeUnavailable : Exception("The server does not support fast mode.")

/**
 * Navigation and tournament state. The server is the source of truth: every
 * action calls the API and then shows what it answered. One request runs at a
 * time; [busy] blocks the UI meanwhile.
 */
class TournamentController(
    private val api: CopaApi,
    private val scope: CoroutineScope,
    private val serverAddress: String,
    private val stats: PlayerStats = PlayerStats(),
    private val saved: SavedTournament = SavedTournament(),
) {
    var stack by mutableStateOf(listOf(Screen.HOME))
        private set
    var busy by mutableStateOf(false)
        private set
    var error by mutableStateOf<UiError?>(null)
        private set

    /** The mode of the tournament being set up or played. */
    var mode by mutableStateOf(TournamentMode.FULL)
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
    private var historyState by mutableStateOf<History?>(null)

    /**
     * Every history the server sends goes through [stats], which counts cups won.
     * A finished cup is no longer offered for reopening.
     */
    var history: History?
        get() = historyState
        private set(value) {
            historyState = value
            if (value == null) return
            stats.record(value)
            if (value.phase == SessionPhase.FINISHED && saved.current?.sessionId == value.sessionId) saved.clear()
        }
    var availability by mutableStateOf<Availability?>(null)
        private set
    var lineup by mutableStateOf<List<Player?>>(emptyList())
    var formKey by mutableStateOf(FormKey.F442)
    private var lastMatchId by mutableStateOf<String?>(null)

    private var sessionId: String? = null
    private var job: Job? = null

    val screen get() = stack.last()

    /** Single-player cups won on this device. */
    val cupsWon get() = stats.cupsWon

    /** The unfinished tournament saved on this device, which Home offers to reopen. */
    val inProgress get() = saved.current

    val next: NextStep?
        get() {
            val currentDraw = draw ?: return null
            val currentHistory = history ?: return null
            return nextStep(currentDraw, currentHistory)
        }

    /** The user's most recently played match, shown on the result screen. */
    val lastMatch: Match?
        get() = history?.matches?.firstOrNull { it.id == lastMatchId }

    fun openTeamSelection(mode: TournamentMode = TournamentMode.FULL) {
        // Starting over from Home: a drawn session can no longer take a call-up, and a
        // session keeps the mode it was created with. The saved one stays reopenable
        // until the new call-up replaces it.
        if (draw != null || (sessionId != null && mode != this.mode)) clearTournament()
        this.mode = mode
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
            val session = sessionId ?: createSession()
            api.callUp(session, squadId, playerIds.toList())
            squad?.let { saved.save(session, it.name) }
            callUp = playerIds
            lineup = emptyList()
            navigate(Screen.DRAW_SETUP)
        }
    }

    /** A server without fast mode ignores the mode and creates a full cup: that is checked here. */
    private suspend fun createSession(): String {
        val created = api.createSession(mode)
        if (mode != TournamentMode.FULL && api.session(created).mode != mode) throw FastModeUnavailable()
        sessionId = created
        return created
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

    /**
     * Reopens the saved tournament where it stopped. The server keeps the whole
     * tournament: this only reloads what the screens show.
     */
    fun resumeTournament() {
        val target = saved.current ?: return
        if (target.sessionId == sessionId && callUp.isNotEmpty()) {
            stack = resumedStack()
            return
        }
        request {
            val state = api.session(target.sessionId)
            val squadId = state.squadId
            if (squadId == null || state.phase == SessionPhase.CREATED || state.phase == SessionPhase.FINISHED) {
                saved.clear()
                return@request
            }
            if (state.phase == SessionPhase.CALLED_UP) {
                // Called up but not drawn yet: back to the draw, with the squad screens behind it.
                val loadedSquads = api.squads()
                val loadedPlayers = api.players(squadId)
                val loadedPresets = api.presets(squadId)
                clearTournament()
                squads = loadedSquads
                squad = loadedSquads.firstOrNull { it.id == squadId }
                players = loadedPlayers
                presets = loadedPresets
            } else {
                // GET /draw returns the existing draw once there is one.
                val drawn = api.draw(target.sessionId)
                val latest = api.history(target.sessionId)
                clearTournament()
                squad = drawn.userSquad
                draw = drawn
                history = latest
            }
            sessionId = target.sessionId
            mode = state.mode ?: TournamentMode.FULL
            callUp = state.callUp.toSet()
            stack = resumedStack()
        }
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
        clearTournament()
        saved.clear()
    }

    /** Forgets the tournament in memory; the saved one on the device stays. */
    private fun clearTournament() {
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

    private fun resumedStack(): List<Screen> =
        if (draw == null) {
            listOf(Screen.HOME, Screen.TEAM_SELECTION, Screen.SQUAD_BUILDER, Screen.DRAW_SETUP)
        } else {
            listOf(Screen.HOME, hubScreen())
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
        if (failure is FastModeUnavailable) {
            return UiError("O servidor ainda não tem o modo rápido. Jogue o modo clássico por enquanto.")
        }
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
