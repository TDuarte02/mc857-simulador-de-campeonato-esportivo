package com.mc857.copaamerica.state

import com.mc857.copaamerica.platform.MemoryStore
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class SavedTournamentTest {
    @Test
    fun startsEmpty() {
        assertNull(SavedTournament(MemoryStore()).current)
    }

    @Test
    fun survivesRestarts() {
        val store = MemoryStore()
        SavedTournament(store).save("s1", "Brasil")

        // A new SavedTournament over the same store is the app opening again.
        assertEquals(TournamentInProgress("s1", "Brasil"), SavedTournament(store).current)
    }

    @Test
    fun aNewCallUpReplacesTheSavedTournament() {
        val saved = SavedTournament(MemoryStore())
        saved.save("s1", "Brasil")
        saved.save("s2", "Peru")
        assertEquals(TournamentInProgress("s2", "Peru"), saved.current)
    }

    @Test
    fun clearForgetsItForGood() {
        val store = MemoryStore()
        val saved = SavedTournament(store)
        saved.save("s1", "Brasil")
        saved.clear()

        assertNull(saved.current)
        assertNull(SavedTournament(store).current)
    }
}
