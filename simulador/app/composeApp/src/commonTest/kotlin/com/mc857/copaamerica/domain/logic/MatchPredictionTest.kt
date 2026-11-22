package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.data.MOCK_TEAMS
import com.mc857.copaamerica.domain.data.NATIONAL_TEAM_ATTRIBUTES
import com.mc857.copaamerica.domain.data.teamAttributesFor
import com.mc857.copaamerica.domain.model.TeamAttributes
import kotlin.random.Random
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class MatchPredictionTest {
    @Test
    fun strongerAttackRaisesExpectedGoals() {
        val average = TeamAttributes(65.0, 65.0, 65.0, 70.0)
        val strongerAttack = average.copy(attack = 80.0, midfield = 75.0)

        assertTrue(expectedGoals(strongerAttack, average) > expectedGoals(average, strongerAttack))
    }

    @Test
    fun scoreIsRepeatableForSameFixtureAndSeed() {
        val first = predictMatchScore("Argentina", "Brasil", 1234)

        assertEquals(first, predictMatchScore("Argentina", "Brasil", 1234))
        assertTrue(first.first >= 0 && first.second >= 0)
    }

    @Test
    fun poissonSamplerHasExpectedAverage() {
        val mean = (0 until 5000).map { seed -> sampleGoals(2.0, Random(seed)) }.average()

        assertTrue(mean in 1.9..2.1, "Observed mean was $mean")
    }

    @Test
    fun everyTournamentTeamHasAnAggregatedProfile() {
        assertEquals(MOCK_TEAMS.map { it.name }.toSet(), NATIONAL_TEAM_ATTRIBUTES.keys)
        assertTrue(teamAttributesFor("Haiti").attack < teamAttributesFor("Argentina").attack)
    }
}