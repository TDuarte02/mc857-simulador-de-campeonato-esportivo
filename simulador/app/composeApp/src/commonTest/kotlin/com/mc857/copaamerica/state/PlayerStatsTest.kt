package com.mc857.copaamerica.state

import com.mc857.copaamerica.domain.model.Bracket
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Placement
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.platform.MemoryStore
import kotlin.test.Test
import kotlin.test.assertEquals

class PlayerStatsTest {
    private fun history(sessionId: String, placement: Placement?, phase: SessionPhase = SessionPhase.FINISHED) =
        History(
            sessionId = sessionId,
            phase = phase,
            placement = placement,
            groups = emptyList(),
            bracket = Bracket(),
            userPath = emptyList(),
            matches = emptyList(),
        )

    @Test
    fun startsAtZero() {
        assertEquals(0, PlayerStats(MemoryStore()).cupsWon)
    }

    @Test
    fun countsOnlyCupsWon() {
        val stats = PlayerStats(MemoryStore())
        stats.record(history("s1", placement = null, phase = SessionPhase.GROUP_STAGE))
        stats.record(history("s2", Placement.RUNNER_UP))
        stats.record(history("s3", Placement.GROUP_STAGE))
        assertEquals(0, stats.cupsWon)

        stats.record(history("s4", Placement.CHAMPION))
        assertEquals(1, stats.cupsWon)
    }

    @Test
    fun countsEachSessionOnce() {
        val stats = PlayerStats(MemoryStore())
        // The history of a finished session is fetched again (retries, screens).
        repeat(3) { stats.record(history("s1", Placement.CHAMPION)) }
        assertEquals(1, stats.cupsWon)

        stats.record(history("s2", Placement.CHAMPION))
        assertEquals(2, stats.cupsWon)
    }

    @Test
    fun survivesRestarts() {
        val store = MemoryStore()
        PlayerStats(store).record(history("s1", Placement.CHAMPION))

        // A new PlayerStats over the same store is the app opening again.
        val reopened = PlayerStats(store)
        assertEquals(1, reopened.cupsWon)
        reopened.record(history("s1", Placement.CHAMPION))
        assertEquals(1, reopened.cupsWon)
    }
}
