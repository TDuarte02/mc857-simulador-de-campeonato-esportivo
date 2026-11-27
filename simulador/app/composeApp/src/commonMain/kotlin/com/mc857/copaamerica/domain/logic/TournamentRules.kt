package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.domain.model.Stage

/*
 * Read-only questions about the state the API reported. Nothing here decides a
 * result: matches, standings and the bracket all come from the server.
 */

/** What the user can do next. */
sealed interface NextStep {
    /** There is a match to play. */
    data class Play(val match: Match) : NextStep

    /** Group stage over and the user qualified: the quarter-finals can be drawn. */
    data object DrawPlayoffs : NextStep

    /** The user is out; the rest of the cup can be simulated. */
    data object Eliminated : NextStep

    data object Finished : NextStep
}

/**
 * Derived from the history instead of the `next` of POST /simulate, so it stays
 * right after a lost response or a repeated request.
 */
fun nextStep(draw: Draw, history: History): NextStep {
    val user = draw.userSquad.id
    return when (history.phase) {
        SessionPhase.FINISHED -> NextStep.Finished
        SessionPhase.PLAYOFFS_PENDING ->
            if (history.placement == null) NextStep.DrawPlayoffs else NextStep.Eliminated
        else -> {
            val playedIds = history.matches.map { it.id }.toSet()
            val bracket = history.bracket
            val fixtures = if (history.phase == SessionPhase.GROUP_STAGE) {
                draw.matches.sortedBy { it.round }
            } else {
                bracket.quarterFinals + bracket.semiFinals + listOfNotNull(bracket.thirdPlace, bracket.final)
            }
            fixtures.firstOrNull { it.involves(user) && it.id !in playedIds }
                ?.let { NextStep.Play(it) }
                ?: NextStep.Eliminated
        }
    }
}

/** The user's three group fixtures, with results where already played. */
fun userGroupMatches(draw: Draw, history: History): List<Match> {
    val played = history.matches.associateBy { it.id }
    return draw.matches
        .filter { it.involves(draw.userSquad.id) }
        .sortedBy { it.round }
        .map { played[it.id] ?: it }
}

/** Goals scored by [squadId] and by its opponent; (0, 0) while unplayed. */
fun Match.scoreFor(squadId: String): Pair<Int, Int> {
    val result = result ?: return 0 to 0
    return if (home.id == squadId) result.homeGoals to result.awayGoals else result.awayGoals to result.homeGoals
}

/** Won, drawn or lost from [squadId]'s side; a shootout decides knockout draws. */
enum class Outcome { WIN, DRAW, LOSS }

fun Match.outcomeFor(squadId: String): Outcome = when (result?.winner) {
    null -> Outcome.DRAW
    squadId -> Outcome.WIN
    else -> Outcome.LOSS
}

/** "2–1", or "1–1 (4–3 pên.)" when penalties decided it, from [squadId]'s side. */
fun Match.scoreLabel(squadId: String = home.id): String {
    val result = result ?: return "–"
    val (own, other) = scoreFor(squadId)
    val penalties = result.penalties ?: return "$own–$other"
    val (ownPens, otherPens) =
        if (home.id == squadId) penalties.home to penalties.away else penalties.away to penalties.home
    return "$own–$other ($ownPens–$otherPens pên.)"
}

/** Name of the last stage the user's squad reached, for the final recap. */
fun stageReached(history: History): String =
    history.placement?.label ?: history.userPath.lastOrNull()?.stage?.label ?: Stage.GROUP.label
