package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.GroupMatch
import com.mc857.copaamerica.domain.model.GroupStanding
import com.mc857.copaamerica.domain.model.MatchStatus
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TournamentFormat
import com.mc857.copaamerica.domain.model.TournamentGroup

/** Number of groups for a format: 4 groups of 4 for CLASSIC, 3 for TRADITIONAL, 0 (no groups) for QUICK. Mirrors App.tsx:428-430. */
fun groupCount(format: TournamentFormat): Int = when (format) {
    TournamentFormat.TRADITIONAL -> 3
    TournamentFormat.CLASSIC -> 4
    TournamentFormat.QUICK -> 0
}

fun makeGroups(participants: List<PoolTeam>, format: TournamentFormat): List<TournamentGroup> =
    List(groupCount(format)) { i ->
        val teams = participants.drop(i * 4).take(4)
        val standings = teams.map { GroupStanding(team = it) }
        val matches = mutableListOf<GroupMatch>()
        for (a in teams.indices) {
            for (b in a + 1 until teams.size) {
                matches += GroupMatch(
                    id = "G${i + 1}-${a + 1}-${b + 1}",
                    home = teams[a],
                    away = teams[b],
                )
            }
        }
        TournamentGroup(name = ('A' + i).toString(), teams = teams, standings = standings, matches = matches)
    }

/** Mirrors App.tsx:453-475. */
fun applyGroupResult(group: TournamentGroup, match: GroupMatch, homeGoals: Int, awayGoals: Int): TournamentGroup {
    val standings = group.standings.map { row ->
        when (row.team.name) {
            match.home.name -> row.copy(
                played = row.played + 1,
                goalsFor = row.goalsFor + homeGoals, goalsAgainst = row.goalsAgainst + awayGoals,
                yellow = row.yellow + match.homeYellow, red = row.red + match.homeRed,
                won = row.won + if (homeGoals > awayGoals) 1 else 0,
                lost = row.lost + if (homeGoals < awayGoals) 1 else 0,
                drawn = row.drawn + if (homeGoals == awayGoals) 1 else 0,
                points = row.points + if (homeGoals > awayGoals) 3 else if (homeGoals == awayGoals) 1 else 0,
            )
            match.away.name -> row.copy(
                played = row.played + 1,
                goalsFor = row.goalsFor + awayGoals, goalsAgainst = row.goalsAgainst + homeGoals,
                yellow = row.yellow + match.awayYellow, red = row.red + match.awayRed,
                won = row.won + if (awayGoals > homeGoals) 1 else 0,
                lost = row.lost + if (awayGoals < homeGoals) 1 else 0,
                drawn = row.drawn + if (homeGoals == awayGoals) 1 else 0,
                points = row.points + if (awayGoals > homeGoals) 3 else if (homeGoals == awayGoals) 1 else 0,
            )
            else -> row
        }
    }
    val matches = group.matches.map {
        if (it.id == match.id) match.copy(status = MatchStatus.PLAYED, homeGoals = homeGoals, awayGoals = awayGoals) else it
    }
    return group.copy(standings = standings, matches = matches)
}

private fun seedOf(id: String): Int = id.sumOf { it.code }

/** Deterministic placeholder score/cards for a match, keyed by its id — same match always resolves the same way. Mirrors App.tsx:490-504. */
fun groupMatchScore(match: GroupMatch): Pair<Int, Int> {
    val seed = seedOf(match.id)
    return (seed % 3) to ((seed / 3) % 3)
}

fun groupMatchCards(match: GroupMatch): GroupMatch {
    val seed = seedOf(match.id)
    return match.copy(
        homeYellow = if (seed % 4 == 0) 1 else 0,
        awayYellow = if (seed % 5 == 0) 1 else 0,
        homeRed = if (seed % 11 == 0) 1 else 0,
        awayRed = if (seed % 13 == 0) 1 else 0,
    )
}

/** Auto-resolves every match still pending in each group (used to fast-forward games that don't involve the user). Mirrors App.tsx:477-484. */
fun simulateGroupMatches(groups: List<TournamentGroup>): List<TournamentGroup> = groups.map { group ->
    group.matches.fold(group) { current, match ->
        if (match.status == MatchStatus.PLAYED) return@fold current
        val homeGoals = (group.matches.indexOf(match) + group.name[0].code) % 3
        val awayGoals = (group.matches.indexOf(match) * 2 + group.name[0].code) % 2
        applyGroupResult(current, groupMatchCards(match), homeGoals, awayGoals)
    }
}

fun groupMatchLabel(match: GroupMatch): String = "${match.home.flag} ${match.home.name} × ${match.away.name} ${match.away.flag}"

fun groupTieBreakers(): List<String> = listOf(
    "Saldo de gols",
    "Gols marcados",
    "Confronto direto: pontos, saldo e gols",
    "Menos cartões vermelhos",
    "Menos cartões amarelos",
    "Sorteio",
)

/** Mirrors App.tsx:517-524. */
val standingComparator: Comparator<GroupStanding> = compareByDescending<GroupStanding> { it.points }
    .thenByDescending { it.goalsFor - it.goalsAgainst }
    .thenByDescending { it.goalsFor }
    .thenBy { it.red }
    .thenBy { it.yellow }
    .thenBy { it.team.name }

fun rankGroups(groups: List<TournamentGroup>): List<TournamentGroup> =
    groups.map { it.copy(standings = it.standings.sortedWith(standingComparator)) }
