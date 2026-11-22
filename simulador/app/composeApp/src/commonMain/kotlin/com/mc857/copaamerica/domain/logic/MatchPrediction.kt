package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.data.teamAttributesFor
import com.mc857.copaamerica.domain.model.TeamAttributes
import kotlin.math.exp
import kotlin.random.Random

fun expectedGoals(attacking: TeamAttributes, defending: TeamAttributes): Double =
    (1.35 * exp(
        0.8 * (attacking.attack - defending.defense) / 100.0 +
            0.35 * (attacking.midfield - defending.midfield) / 100.0 +
            0.25 * (75.0 - defending.goalkeeper) / 100.0,
    )).coerceIn(0.15, 4.0)

fun sampleGoals(expectedGoals: Double, random: Random): Int {
    require(expectedGoals.isFinite() && expectedGoals > 0.0)
    val limit = exp(-expectedGoals)
    var product = 1.0
    var goals = 0
    do {
        goals += 1
        product *= random.nextDouble()
    } while (product > limit)
    return goals - 1
}

fun predictScore(
    home: TeamAttributes,
    away: TeamAttributes,
    seed: Int,
): Pair<Int, Int> {
    val random = Random(seed)
    return sampleGoals(expectedGoals(home, away), random) to
        sampleGoals(expectedGoals(away, home), random)
}

fun predictMatchScore(homeTeam: String, awayTeam: String, seed: Int): Pair<Int, Int> =
    predictScore(teamAttributesFor(homeTeam), teamAttributesFor(awayTeam), seed)