package com.mc857.copaamerica.domain.model

/**
 * Core data model, mirroring the TypeScript types in design/src/App.tsx:4-69.
 * Names match the original 1:1 so the two implementations stay easy to
 * cross-reference.
 */

enum class Confederation { CONMEBOL, CONCACAF }

data class TeamData(
    val id: String,
    val name: String,
    val flag: String,
    val conf: Confederation,
)

enum class SlotCat { GK, DEF, MID, FW }

enum class SlotRole(val sector: SlotCat) {
    GOL(SlotCat.GK),
    ZAG(SlotCat.DEF), LD(SlotCat.DEF), LE(SlotCat.DEF),
    VOL(SlotCat.MID), MC(SlotCat.MID), MEI(SlotCat.MID),
    PD(SlotCat.FW), PE(SlotCat.FW), CA(SlotCat.FW),
}

data class Player(
    val id: Int,
    val name: String,
    val rating: Int,
    val era: String,
    val pos: SlotCat,
    val role: SlotRole,
)

enum class PosFilter { ALL, GK, DEF, MID, FW }

enum class FormKey(val label: String) {
    F442("4-4-2"), F433("4-3-3"), F352("3-5-2"), F4231("4-2-3-1"),
}

enum class Phase { GROUP, QF, SF, THIRD, FINAL }

enum class TournamentFormat(val teamCount: Int) { QUICK(8), TRADITIONAL(12), CLASSIC(16) }

data class SlotCfg(val label: String, val cat: SlotCat, val x: Float, val y: Float)
data class FSlot(val slot: SlotCfg, val player: Player)

data class PoolTeam(val name: String, val flag: String)

data class Stadium(val name: String, val city: String, val country: String, val capacity: String)

data class GroupStanding(
    val team: PoolTeam,
    val played: Int = 0,
    val won: Int = 0,
    val drawn: Int = 0,
    val lost: Int = 0,
    val goalsFor: Int = 0,
    val goalsAgainst: Int = 0,
    val points: Int = 0,
    val yellow: Int = 0,
    val red: Int = 0,
)

enum class MatchStatus { PENDING, PLAYED }

data class GroupMatch(
    val id: String,
    val home: PoolTeam,
    val away: PoolTeam,
    val status: MatchStatus = MatchStatus.PENDING,
    val homeGoals: Int? = null,
    val awayGoals: Int? = null,
    val homeYellow: Int = 0,
    val awayYellow: Int = 0,
    val homeRed: Int = 0,
    val awayRed: Int = 0,
)

data class TournamentGroup(
    val name: String,
    val teams: List<PoolTeam>,
    val standings: List<GroupStanding>,
    val matches: List<GroupMatch>,
)

data class KnockoutTie(
    val home: PoolTeam? = null,
    val away: PoolTeam? = null,
    val homeGoals: Int? = null,
    val awayGoals: Int? = null,
    val winner: PoolTeam? = null,
)

data class Knockout(
    val qf: List<KnockoutTie>,
    val sf: List<KnockoutTie>,
    val third: KnockoutTie,
    val final: KnockoutTie,
)

data class DrawnBracket(
    val format: TournamentFormat,
    val participants: List<PoolTeam>,
    val groups: List<TournamentGroup>,
    val qf: List<Pair<PoolTeam, PoolTeam>>,
    val ko: Knockout,
)

enum class CardStatus { YELLOW, RED }

enum class MatchEventType { GOAL, YELLOW }
enum class MatchSide { TEAM, RIVAL }

data class MatchEvent(
    val minute: Int,
    val type: MatchEventType,
    val side: MatchSide,
    val player: String,
    val score: String,
)
