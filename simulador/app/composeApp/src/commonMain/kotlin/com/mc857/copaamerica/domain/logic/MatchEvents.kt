package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.MatchEvent
import com.mc857.copaamerica.domain.model.MatchEventType
import com.mc857.copaamerica.domain.model.MatchSide
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.SlotCat

/**
 * Builds a plausible event timeline from the final score so the running
 * score always matches: one event per goal in chronological order, plus one
 * yellow card per side. Scorers come from whoever actually took the pitch;
 * the opponent, with no detailed squad, is credited by generic position.
 * Mirrors App.tsx:1817-1846.
 */
fun buildMatchEvents(teamGoals: Int, opponentGoals: Int, squad: List<Player>): List<MatchEvent> {
    val outfield = squad.filter { it.pos != SlotCat.GK }
    fun teamScorer(i: Int) = if (outfield.isNotEmpty()) outfield[(i * 3) % outfield.size].name else "Atacante"
    val rivalRoles = listOf("Atacante", "Meia", "Volante")
    fun rivalScorer(i: Int) = rivalRoles[i % 3]

    data class Goal(val side: MatchSide, val minute: Int)

    val goals = mutableListOf<Goal>()
    val maxGoals = maxOf(teamGoals, opponentGoals)
    for (i in 0 until maxGoals) {
        if (i < teamGoals) goals += Goal(MatchSide.TEAM, 12 + i * 15 + (i % 2) * 4)
        if (i < opponentGoals) goals += Goal(MatchSide.RIVAL, 22 + i * 18 + (i % 2) * 5)
    }
    goals.sortBy { it.minute }

    val events = mutableListOf<MatchEvent>()
    var t = 0
    var o = 0
    goals.forEach { g ->
        if (g.side == MatchSide.TEAM) t++ else o++
        events += MatchEvent(
            minute = g.minute,
            type = MatchEventType.GOAL,
            side = g.side,
            player = if (g.side == MatchSide.TEAM) teamScorer(t - 1) else rivalScorer(o - 1),
            score = "$t – $o",
        )
    }
    val final = "$t – $o"
    events += MatchEvent(62, MatchEventType.YELLOW, MatchSide.TEAM, teamScorer(2), final)
    events += MatchEvent(68, MatchEventType.YELLOW, MatchSide.RIVAL, rivalScorer(2), final)
    return events.sortedBy { it.minute }
}
