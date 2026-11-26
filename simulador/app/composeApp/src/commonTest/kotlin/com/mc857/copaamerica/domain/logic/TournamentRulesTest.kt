package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.Availability
import com.mc857.copaamerica.domain.model.AvailablePlayer
import com.mc857.copaamerica.domain.model.Bracket
import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.Federation
import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.Placement
import com.mc857.copaamerica.domain.model.Position
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.Stage
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TournamentRulesTest {
    private fun squad(id: String) = Squad(id, id, "https://flags.example/$id.png", Federation.CONMEBOL)

    private val user = squad("brazil")

    private fun match(id: String, stage: Stage, round: Int, played: Boolean = false) =
        Match(id, stage, round, home = user, away = squad("peru"), played = played)

    private val draw = Draw(user, emptyList(), (1..3).map { match("G$it", Stage.GROUP, it) })

    private fun history(
        phase: SessionPhase,
        played: List<Match> = emptyList(),
        placement: Placement? = null,
        bracket: Bracket = Bracket(),
    ) = History("s", phase, user, placement, null, emptyList(), bracket, played, played)

    @Test
    fun groupStageOffersTheFirstUnplayedRound() {
        val played = listOf(match("G1", Stage.GROUP, 1, played = true))

        assertEquals(NextStep.Play(draw.matches[1]), nextStep(draw, history(SessionPhase.GROUP_STAGE, played)))
    }

    @Test
    fun afterTheGroupsAQualifiedUserDrawsThePlayoffs() {
        assertEquals(NextStep.DrawPlayoffs, nextStep(draw, history(SessionPhase.PLAYOFFS_PENDING)))
        assertEquals(
            NextStep.Eliminated,
            nextStep(draw, history(SessionPhase.PLAYOFFS_PENDING, placement = Placement.GROUP_STAGE)),
        )
    }

    @Test
    fun aBeatenSemiFinalistStillHasTheThirdPlaceMatch() {
        val semi = match("SF1", Stage.SEMI_FINAL, 5, played = true)
        val third = match("THIRD", Stage.THIRD_PLACE, 6)
        val state = history(SessionPhase.FINALS, listOf(semi), bracket = Bracket(semiFinals = listOf(semi), thirdPlace = third))

        assertEquals(NextStep.Play(third), nextStep(draw, state))
    }

    @Test
    fun withoutAnUpcomingMatchTheUserIsOut() {
        val quarter = match("QF1", Stage.QUARTER_FINAL, 4, played = true)
        val state = history(SessionPhase.SEMI_FINALS, listOf(quarter), bracket = Bracket(quarterFinals = listOf(quarter)))

        assertEquals(NextStep.Eliminated, nextStep(draw, state))
        assertEquals(NextStep.Finished, nextStep(draw, history(SessionPhase.FINISHED)))
    }

    private fun available(id: Int, position: Position) = AvailablePlayer(id, "P$id", 25, position, 70 + id % 10, 0)

    @Test
    fun randomLineupFieldsOneGoalkeeperAndFillsAShortSectorWithOutfielders() {
        // Only 1 of the 2 forwards of a 4-4-2 is fit.
        val players = listOf(available(1, Position.GK), available(2, Position.GK)) +
            (3..9).map { available(it, Position.DEF) } +
            (10..16).map { available(it, Position.MID) } +
            available(17, Position.FW)
        val lineup = randomLineup(FIELD_FORMATIONS.getValue(FormKey.F442), Availability(players, emptyList()))

        assertTrue(lineup.all { it != null })
        assertEquals(11, lineup.mapNotNull { it?.id }.toSet().size)
        assertEquals(1, lineup.count { it?.position == Position.GK })
    }
}
