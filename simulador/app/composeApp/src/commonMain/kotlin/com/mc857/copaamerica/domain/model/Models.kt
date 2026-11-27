package com.mc857.copaamerica.domain.model

import kotlinx.serialization.Serializable

/**
 * The app's data model is the API's JSON (see simulador/server and its
 * /openapi.json): the server owns the tournament, the app only displays it.
 */

enum class Position(val label: String) {
    GK("GOL"), DEF("DEF"), MID("MEI"), FW("ATA"),
}

enum class Federation { CONMEBOL, CONCACAF }

@Serializable
data class Squad(
    val id: String,
    val name: String,
    /** Image URL. */
    val flag: String,
    val federation: Federation,
)

@Serializable
data class Player(
    val id: Int,
    val name: String,
    val age: Int,
    val position: Position,
    val overall: Int,
)

@Serializable
data class Preset(
    val id: String,
    val name: String,
    val description: String,
    val players: List<Player>,
)

enum class Stage(val label: String) {
    GROUP("Fase de grupos"),
    QUARTER_FINAL("Quartas de final"),
    SEMI_FINAL("Semifinal"),
    THIRD_PLACE("Disputa de 3º lugar"),
    FINAL("Final"),
}

enum class CardType { YELLOW, RED }

@Serializable
data class EventPlayer(val id: Int, val name: String? = null)

@Serializable
data class GoalEvent(val minute: Int, val squad: String, val player: EventPlayer)

@Serializable
data class CardEvent(val minute: Int, val squad: String, val player: EventPlayer, val type: CardType)

@Serializable
data class InjuryEvent(val minute: Int, val squad: String, val player: EventPlayer, val matchesOut: Int)

@Serializable
data class Penalties(val home: Int, val away: Int)

@Serializable
data class MatchResult(
    val homeGoals: Int,
    val awayGoals: Int,
    val penalties: Penalties? = null,
    /** Squad id of the winner; null on a draw. */
    val winner: String? = null,
    val goals: List<GoalEvent> = emptyList(),
    val cards: List<CardEvent> = emptyList(),
    val injuries: List<InjuryEvent> = emptyList(),
)

@Serializable
data class Match(
    val id: String,
    val stage: Stage,
    val round: Int,
    val group: String? = null,
    val home: Squad,
    val away: Squad,
    val played: Boolean,
    /** Null until the match is played. */
    val result: MatchResult? = null,
) {
    fun involves(squadId: String) = home.id == squadId || away.id == squadId

    fun opponentOf(squadId: String) = if (home.id == squadId) away else home
}

@Serializable
data class DrawGroup(val name: String, val squads: List<Squad>)

@Serializable
data class Draw(
    val userSquad: Squad,
    val groups: List<DrawGroup>,
    /** Every group-stage fixture; results are hidden until their round is played. */
    val matches: List<Match>,
)

enum class UnavailableReason { SUSPENDED_RED, SUSPENDED_YELLOWS, INJURED }

@Serializable
data class AvailablePlayer(
    val id: Int,
    val name: String,
    val age: Int,
    val position: Position,
    val overall: Int,
    val yellowCards: Int,
) {
    val player get() = Player(id, name, age, position, overall)
}

@Serializable
data class UnavailablePlayer(
    val id: Int,
    val name: String,
    val age: Int,
    val position: Position,
    val overall: Int,
    val reason: UnavailableReason,
    val matchesRemaining: Int,
) {
    val player get() = Player(id, name, age, position, overall)
}

@Serializable
data class Availability(
    val available: List<AvailablePlayer>,
    val unavailable: List<UnavailablePlayer>,
)

@Serializable
data class Standing(
    val squad: Squad,
    val played: Int,
    val won: Int,
    val drawn: Int,
    val lost: Int,
    val goalsFor: Int,
    val goalsAgainst: Int,
    val goalDifference: Int,
    val points: Int,
    val yellowCards: Int,
    val redCards: Int,
)

@Serializable
data class GroupTable(val name: String, val standings: List<Standing>)

@Serializable
data class Podium(val champion: Squad, val runnerUp: Squad, val third: Squad, val fourth: Squad)

@Serializable
data class Bracket(
    val quarterFinals: List<Match> = emptyList(),
    val semiFinals: List<Match> = emptyList(),
    val thirdPlace: Match? = null,
    val final: Match? = null,
)

enum class SessionPhase {
    CREATED, CALLED_UP, GROUP_STAGE, PLAYOFFS_PENDING, QUARTER_FINALS, SEMI_FINALS, FINALS, FINISHED,
}

enum class Placement(val label: String) {
    CHAMPION("Campeã"),
    RUNNER_UP("Vice"),
    THIRD_PLACE("3º lugar"),
    FOURTH_PLACE("4º lugar"),
    QUARTER_FINALS("Quartas"),
    GROUP_STAGE("Grupos"),
}

/** Where a session stands (GET /session/{sessionId}): enough to reopen it. */
@Serializable
data class SessionState(
    val id: String,
    val phase: SessionPhase,
    val squadId: String? = null,
    /** The called-up player ids; empty before the call-up. */
    val callUp: List<Int> = emptyList(),
)

/** Snapshot of everything that happened in a session so far (GET /{sessionId}/history). */
@Serializable
data class History(
    val sessionId: String,
    val phase: SessionPhase,
    val userSquad: Squad? = null,
    /** Where the user's squad finished; null while it is still in the cup. */
    val placement: Placement? = null,
    val podium: Podium? = null,
    val groups: List<GroupTable>,
    val bracket: Bracket,
    /** The user's played matches, in order. */
    val userPath: List<Match>,
    /** Every played match. */
    val matches: List<Match>,
)

// --- Local to the app: how the lineup is arranged on the pitch ----------------

enum class PosFilter { ALL, GK, DEF, MID, FW }

enum class FormKey(val label: String) {
    F442("4-4-2"), F433("4-3-3"), F352("3-5-2"), F4231("4-2-3-1"),
}

data class SlotCfg(val label: String, val cat: Position, val x: Float, val y: Float)
