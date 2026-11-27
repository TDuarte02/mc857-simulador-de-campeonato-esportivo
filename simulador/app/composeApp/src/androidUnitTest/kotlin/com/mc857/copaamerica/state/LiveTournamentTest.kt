package com.mc857.copaamerica.state

import com.mc857.copaamerica.data.CopaApi
import com.mc857.copaamerica.domain.logic.FIELD_FORMATIONS
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.logic.SQUAD_SIZE
import com.mc857.copaamerica.domain.logic.randomLineup
import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.domain.model.TournamentMode
import com.mc857.copaamerica.nav.Screen
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * Plays whole cups through the real [TournamentController] against a running
 * API. Skipped unless API_BASE_URL is set (API_KEY too, for the API Gateway):
 *
 *     API_BASE_URL=http://127.0.0.1:5000 ./gradlew :composeApp:testDebugUnitTest
 *
 * The Modo Rápido cups run only with API_FAST_MODE=1, against a server that has it.
 * API_CUPS sets how many cups of each mode are played (40 by default).
 */
class LiveTournamentTest {
    private val baseUrl: String? = System.getenv("API_BASE_URL")
    private val apiKey: String = System.getenv("API_KEY").orEmpty()
    private val fastMode: Boolean = System.getenv("API_FAST_MODE") == "1"
    private val cups: Int = System.getenv("API_CUPS")?.toIntOrNull() ?: 40

    private suspend fun TournamentController.act(action: TournamentController.() -> Unit) {
        action()
        withTimeout(20_000) { while (busy) delay(5) }
        assertNull(error, error?.message)
    }

    @Test
    fun playsWholeCupsAgainstTheApi() = playCups(TournamentMode.FULL)

    @Test
    fun playsWholeFastCupsAgainstTheApi() {
        if (fastMode) playCups(TournamentMode.FAST)
    }

    private fun playCups(mode: TournamentMode) = runBlocking {
        val url = baseUrl ?: return@runBlocking
        val controller = TournamentController(CopaApi(url, apiKey), CoroutineScope(Dispatchers.Default), url)
        val placements = mutableMapOf<String, Int>()

        // Enough cups for the random server model to reach every branch of the flow.
        repeat(cups) { cup ->
            controller.reset()
            controller.act { openTeamSelection(mode) }
            assertEquals(16, controller.squads.size)
            controller.act { selectSquad(squads[cup % squads.size]) }
            assertEquals(listOf("current", "legends", "random"), controller.presets.map { it.id })

            var picked = emptySet<Int>()
            controller.act { applyPreset("random") { players -> picked = players.map { it.id }.toSet() } }
            assertEquals(SQUAD_SIZE, picked.size)
            controller.act { confirmCallUp(picked) }
            assertEquals(Screen.DRAW_SETUP, controller.screen)
            controller.act { runDraw() }
            val draw = assertNotNull(controller.draw)
            if (mode == TournamentMode.FAST) {
                assertTrue(draw.groups.isEmpty())
                assertEquals(8, draw.squads.size)
                assertTrue(draw.matches.all { it.stage == Stage.QUARTER_FINAL })
            } else {
                assertEquals(4, draw.groups.size)
            }
            controller.act { openLineup() }

            var steps = 0
            while (controller.screen != Screen.PHASE_OVERVIEW) {
                assertTrue(steps++ < 40, "stuck on ${controller.screen} with ${controller.next}")
                when (controller.screen) {
                    Screen.PRE_MATCH -> {
                        val slots = FIELD_FORMATIONS.getValue(FormKey.F442)
                        controller.lineup = randomLineup(slots, assertNotNull(controller.availability))
                        controller.act { playMatch() }
                        assertEquals(Screen.MATCH_RESULT, controller.screen)
                        assertNotNull(controller.lastMatch?.result)
                    }
                    Screen.MATCH_RESULT -> controller.act { continueAfterMatch() }
                    Screen.GROUP_STAGE, Screen.ELIMINATION -> when (controller.next) {
                        is NextStep.Play -> controller.act { openLineup() }
                        NextStep.DrawPlayoffs -> controller.act { drawPlayoffs() }
                        NextStep.Eliminated -> controller.act { simulateRest() }
                        else -> error("unexpected ${controller.next} on ${controller.screen}")
                    }
                    Screen.BRACKET -> controller.act { openLineup() }
                    else -> error("unexpected screen ${controller.screen}")
                }
            }

            val history = assertNotNull(controller.history)
            assertEquals(SessionPhase.FINISHED, history.phase)
            assertNotNull(history.podium)
            val placement = assertNotNull(history.placement).name
            placements[placement] = (placements[placement] ?: 0) + 1
            val played = if (mode == TournamentMode.FAST) 8 else 32
            assertEquals(played, history.matches.size)
        }
        println("$mode placements reached: $placements")
    }
}
