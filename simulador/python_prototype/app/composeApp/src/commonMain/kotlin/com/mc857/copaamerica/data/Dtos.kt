package com.mc857.copaamerica.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable data class ApiErrorBody(val code: String, val message: String)

@Serializable
data class NationDto(
    val id: String, val name: String,
    @SerialName("display_name") val displayName: String,
    val flag: String, val confederation: String,
)

@Serializable
data class ApiPlayerDto(
    val name: String, val positions: List<String>, val sectors: List<String>, val overall: Int,
    @SerialName("is_goalkeeper") val isGoalkeeper: Boolean,
    val attributes: Map<String, Double>,
)

@Serializable
data class SquadRulesDto(
    val size: Int, val goalkeepers: Int, val outfield: Int,
    @SerialName("min_defenders") val minDefenders: Int,
    @SerialName("min_midfielders") val minMidfielders: Int,
    @SerialName("min_forwards") val minForwards: Int,
)

@Serializable data class PoolDto(val nation: String, val rules: SquadRulesDto, val players: List<ApiPlayerDto>)

@Serializable
data class CreateGameRequest(
    @SerialName("user_team") val userTeam: String, val squad: List<String>, val seed: Int? = null,
)

@Serializable data class PickDto(val player: String, val slot: String)
@Serializable data class StartMatchRequest(val picks: List<PickDto>? = null)
@Serializable data class LineupRequest(val picks: List<PickDto>, val formation: List<String>? = null)
@Serializable data class PlayRequest(val until: String) // "halftime" | "end"

@Serializable
data class PenaltiesSummaryDto(
    @SerialName("first_team") val firstTeam: String? = null,
    @SerialName("goals_a") val goalsA: Int, @SerialName("goals_b") val goalsB: Int,
    val winner: String? = null, @SerialName("sudden_death") val suddenDeath: Boolean,
)

@Serializable
data class MatchSummaryDto(
    val id: String, val phase: String, val group: String? = null, val round: Int? = null,
    @SerialName("slot_a") val slotA: String? = null, @SerialName("slot_b") val slotB: String? = null,
    @SerialName("team_a") val teamA: String? = null, @SerialName("team_b") val teamB: String? = null,
    val status: String,
    @SerialName("goals_a") val goalsA: Int? = null, @SerialName("goals_b") val goalsB: Int? = null,
    val penalties: PenaltiesSummaryDto? = null, val winner: String? = null,
)

@Serializable
data class StandingRowDto(
    val team: String, val played: Int, val wins: Int, val draws: Int, val losses: Int,
    @SerialName("goals_for") val goalsFor: Int, @SerialName("goals_against") val goalsAgainst: Int,
    @SerialName("goal_diff") val goalDiff: Int, val points: Int,
)

@Serializable
data class GroupDto(
    val name: String, val teams: List<String>, val standings: List<StandingRowDto>,
    @SerialName("is_final") val isFinal: Boolean, val matches: List<MatchSummaryDto>,
)

@Serializable data class LineupSlotDto(val player: String, val slot: String)

@Serializable
data class ActiveMatchDto(
    @SerialName("match_id") val matchId: String,
    @SerialName("team_a") val teamA: String, @SerialName("team_b") val teamB: String,
    @SerialName("user_side") val userSide: String, val phase: String, val minute: Int,
    val score: Map<String, Int>,
    @SerialName("can_change_lineup") val canChangeLineup: Boolean,
    @SerialName("cycles_played") val cyclesPlayed: Int,
    val lineup: List<LineupSlotDto>, val formation: List<String>,
)

@Serializable
data class GameStateDto(
    @SerialName("game_id") val gameId: String, val seed: Int,
    @SerialName("user_team") val userTeam: String? = null,
    val phase: String,
    @SerialName("is_finished") val isFinished: Boolean,
    @SerialName("user_eliminated") val userEliminated: Boolean,
    val groups: List<GroupDto>, val knockout: List<MatchSummaryDto>,
    @SerialName("next_match") val nextMatch: MatchSummaryDto? = null,
    @SerialName("pending_user_match") val pendingUserMatch: MatchSummaryDto? = null,
    @SerialName("active_match") val activeMatch: ActiveMatchDto? = null,
    val suspended: List<String>,
)

@Serializable
data class CreateGameDto(
    @SerialName("game_id") val gameId: String, val seed: Int, val state: GameStateDto,
)

@Serializable
data class AdvanceDto(
    @SerialName("pending_match") val pendingMatch: MatchSummaryDto? = null,
    val phase: String,
    @SerialName("user_eliminated") val userEliminated: Boolean,
    @SerialName("is_finished") val isFinished: Boolean,
    val suspended: List<String>,
)

@Serializable
data class TimelineEntryDto(
    val minute: Int, val type: String, val team: String? = null, val player: String? = null,
    val score: Map<String, Int>? = null, val data: JsonObject? = null,
)

@Serializable
data class TeamStatsDto(
    val goals: Int, val possession: Double, val attacks: Int, val attempts: Int,
    @SerialName("possession_lost") val possessionLost: Int, val fouls: Int,
    @SerialName("yellow_cards") val yellowCards: Int, @SerialName("red_cards") val redCards: Int,
)

@Serializable data class KickDto(val team: String, val player: String, val scored: Boolean)

@Serializable
data class PenaltiesViewDto(
    @SerialName("first_team") val firstTeam: String,
    @SerialName("goals_a") val goalsA: Int, @SerialName("goals_b") val goalsB: Int,
    val winner: String, @SerialName("sudden_death") val suddenDeath: Boolean,
    val kicks: List<KickDto>,
)

@Serializable
data class MatchViewDto(
    @SerialName("match_id") val matchId: String,
    @SerialName("team_a") val teamA: String, @SerialName("team_b") val teamB: String,
    val score: Map<String, Int>, val penalties: PenaltiesViewDto? = null,
    val stats: Map<String, TeamStatsDto>, val timeline: List<TimelineEntryDto>,
)

@Serializable
data class PlayDto(
    @SerialName("match_id") val matchId: String, val phase: String, val minute: Int,
    val score: Map<String, Int>, val finished: Boolean,
    val view: MatchViewDto? = null, val suspended: List<String>,
)

/** `final_result()` completo fica como JSON; os campos principais estão tipados. */
@Serializable
data class FinalResultDto(
    val seed: Int,
    @SerialName("user_team") val userTeam: String? = null,
    val champion: String,
    @SerialName("runner_up") val runnerUp: String,
    val third: String, val fourth: String,
    val groups: JsonObject? = null,
)
