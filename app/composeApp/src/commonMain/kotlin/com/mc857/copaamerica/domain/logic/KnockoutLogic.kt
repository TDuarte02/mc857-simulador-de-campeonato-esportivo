package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.Knockout
import com.mc857.copaamerica.domain.model.KnockoutTie
import com.mc857.copaamerica.domain.model.MatchStatus
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TournamentFormat
import com.mc857.copaamerica.domain.model.TournamentGroup

/** Mirrors App.tsx:537-549: top 2 of each group, plus the 2 best 3rd-placed when there are 3 groups. */
fun qualifiedForQuarterfinals(groups: List<TournamentGroup>): List<PoolTeam> {
    val ranked = rankGroups(groups)
    if (ranked.size == 4) {
        return ranked.flatMap { it.standings.take(2).map { s -> s.team } }
    }
    val direct = ranked.flatMap { it.standings.take(2).map { s -> s.team } }
    val bestThirds = ranked.mapNotNull { it.standings.getOrNull(2) }
        .sortedWith(standingComparator)
        .take(2)
        .map { it.team }
    return direct + bestThirds
}

/** Mirrors App.tsx:551-567. */
fun makeQuarterfinals(groups: List<TournamentGroup>): List<Pair<PoolTeam, PoolTeam>> {
    val q = qualifiedForQuarterfinals(groups)
    return if (groups.size == 4) {
        listOf(q[0] to q[7], q[1] to q[6], q[2] to q[5], q[3] to q[4])
    } else {
        listOf(q[0] to q[3], q[1] to q[4], q[2] to q[5], q[6] to q[7])
    }
}

fun emptyTie(home: PoolTeam? = null, away: PoolTeam? = null): KnockoutTie =
    KnockoutTie(home = home, away = away)

fun makeKnockout(qf: List<Pair<PoolTeam, PoolTeam>>): Knockout = Knockout(
    qf = qf.map { (home, away) -> emptyTie(home, away) },
    sf = listOf(emptyTie(), emptyTie()),
    third = emptyTie(),
    final = emptyTie(),
)

/** Same two names always produce the same seed, so a tie's placeholder result never changes across recompositions. Mirrors App.tsx:584-586. */
fun tieSeed(a: PoolTeam, b: PoolTeam): Int = "${a.name}×${b.name}".sumOf { it.code }

/** Resolves a tie the user doesn't play. Mirrors App.tsx:591-600. */
fun simulateTie(tie: KnockoutTie): KnockoutTie {
    if (tie.home == null || tie.away == null || tie.winner != null) return tie
    val seed = tieSeed(tie.home, tie.away)
    val homeGoals = seed % 3
    val awayGoals = (seed / 3) % 3
    val winner = when {
        homeGoals == awayGoals -> if (seed % 2 == 0) tie.home else tie.away
        homeGoals > awayGoals -> tie.home
        else -> tie.away
    }
    return tie.copy(homeGoals = homeGoals, awayGoals = awayGoals, winner = winner)
}

fun tieLoser(tie: KnockoutTie): PoolTeam? {
    val winner = tie.winner ?: return null
    return if (winner.name == tie.home?.name) tie.away else tie.home
}

/** Keeps the tie if both sides are unchanged; otherwise reopens it. Mirrors App.tsx:609-612. */
fun carryOver(tie: KnockoutTie, home: PoolTeam?, away: PoolTeam?): KnockoutTie =
    if (home?.name == tie.home?.name && away?.name == tie.away?.name) tie else emptyTie(home, away)

/** Propagates winners qf→sf→final and losers sf→3rd place. Mirrors App.tsx:616-625. */
fun propagateKnockout(ko: Knockout): Knockout {
    val sf = ko.sf.mapIndexed { index, tie ->
        carryOver(tie, ko.qf.getOrNull(index * 2)?.winner, ko.qf.getOrNull(index * 2 + 1)?.winner)
    }
    return ko.copy(
        sf = sf,
        final = carryOver(ko.final, sf[0].winner, sf[1].winner),
        third = carryOver(ko.third, tieLoser(sf[0]), tieLoser(sf[1])),
    )
}

/** Settles a tie the user just played, respecting which side of the bracket she landed on. Mirrors App.tsx:629-637. */
fun decideTie(tie: KnockoutTie, winner: PoolTeam, winnerGoals: Int, loserGoals: Int): KnockoutTie {
    val winnerIsHome = tie.home?.name == winner.name
    return tie.copy(
        homeGoals = if (winnerIsHome) winnerGoals else loserGoals,
        awayGoals = if (winnerIsHome) loserGoals else winnerGoals,
        winner = winner,
    )
}

/** Resolves a whole round: the user's tie is taken as given, every other tie is simulated, then winners propagate. Mirrors App.tsx:641-644. */
fun settleRound(ko: Knockout, round: KnockoutRound, userIndex: Int, userTie: KnockoutTie): Knockout {
    val updated = when (round) {
        KnockoutRound.QF -> ko.copy(qf = ko.qf.mapIndexed { i, tie -> if (i == userIndex) userTie else simulateTie(tie) })
        KnockoutRound.SF -> ko.copy(sf = ko.sf.mapIndexed { i, tie -> if (i == userIndex) userTie else simulateTie(tie) })
    }
    return propagateKnockout(updated)
}

enum class KnockoutRound { QF, SF }

/** User eliminated: resolves final and 3rd place together so the bracket closes out. Mirrors App.tsx:648-651. */
fun finishKnockout(ko: Knockout): Knockout {
    val filled = propagateKnockout(ko)
    return filled.copy(final = simulateTie(filled.final), third = simulateTie(filled.third))
}

fun makeDrawnBracket(team: PoolTeam, shuffledRivals: List<PoolTeam>, format: TournamentFormat): DrawnBracket {
    val participants = listOf(team) + shuffledRivals
    val groups = if (format == TournamentFormat.TRADITIONAL || format == TournamentFormat.CLASSIC) {
        makeGroups(participants, format)
    } else emptyList()
    val qf = if (format == TournamentFormat.QUICK) {
        listOf(
            team to shuffledRivals[0], shuffledRivals[1] to shuffledRivals[2],
            shuffledRivals[3] to shuffledRivals[4], shuffledRivals[5] to shuffledRivals[6],
        )
    } else emptyList()
    return DrawnBracket(format = format, participants = participants, groups = groups, qf = qf, ko = makeKnockout(qf))
}

fun completeGroupStage(bracket: DrawnBracket): DrawnBracket {
    val groups = simulateGroupMatches(bracket.groups)
    val qf = makeQuarterfinals(groups)
    return bracket.copy(groups = groups, qf = qf, ko = makeKnockout(qf))
}

fun koIndexOf(ties: List<KnockoutTie>, teamName: String): Int =
    ties.indexOfFirst { it.home?.name == teamName || it.away?.name == teamName }

/** Where the bracket stands from the user's point of view. Mirrors App.tsx:1159-1163. */
fun koStageLabel(ko: Knockout, teamName: String): String = when {
    ko.final.winner != null -> "Torneio encerrado"
    koIndexOf(ko.sf, teamName) >= 0 -> "Semifinal"
    else -> "Quartas de final"
}

fun tieLine(tie: KnockoutTie): String =
    "${tie.home?.name} ${tie.home?.flag}  ${tie.homeGoals} – ${tie.awayGoals}  ${tie.away?.name} ${tie.away?.flag}"

data class TieForTeam(val rival: PoolTeam?, val goals: Int, val rivalGoals: Int, val won: Boolean, val drew: Boolean)

fun tieForTeam(tie: KnockoutTie, teamName: String): TieForTeam? {
    if (tie.home?.name != teamName && tie.away?.name != teamName) return null
    val isHome = tie.home?.name == teamName
    val goals = (if (isHome) tie.homeGoals else tie.awayGoals) ?: 0
    val rivalGoals = (if (isHome) tie.awayGoals else tie.homeGoals) ?: 0
    return TieForTeam(
        rival = if (isHome) tie.away else tie.home,
        goals = goals, rivalGoals = rivalGoals,
        won = tie.winner?.name == teamName, drew = false,
    )
}

data class CampaignGame(val label: String, val rival: PoolTeam?, val goals: Int, val rivalGoals: Int, val won: Boolean, val drew: Boolean)

/** The user's games in order played: group stage, then each knockout round reached. Mirrors App.tsx:2016-2045. */
fun userCampaign(bracket: DrawnBracket, teamName: String): List<CampaignGame> {
    val ko = bracket.ko
    val fromGroup = bracket.groups.flatMap { it.matches }
        .filter { it.status == MatchStatus.PLAYED && (it.home.name == teamName || it.away.name == teamName) }
        .map { match ->
            val isHome = match.home.name == teamName
            val goals = (if (isHome) match.homeGoals else match.awayGoals) ?: 0
            val rivalGoals = (if (isHome) match.awayGoals else match.homeGoals) ?: 0
            CampaignGame("Grupos", if (isHome) match.away else match.home, goals, rivalGoals, goals > rivalGoals, goals == rivalGoals)
        }
    val fromKnockout = listOf(
        "Quartas" to ko.qf.getOrNull(koIndexOf(ko.qf, teamName)),
        "Semifinal" to ko.sf.getOrNull(koIndexOf(ko.sf, teamName)),
        "3º lugar" to ko.third,
        "Final" to ko.final,
    ).mapNotNull { (label, tie) ->
        tie?.let { tieForTeam(it, teamName) }?.let { result ->
            CampaignGame(label, result.rival, result.goals, result.rivalGoals, result.won, result.drew)
        }
    }
    return fromGroup + fromKnockout
}
