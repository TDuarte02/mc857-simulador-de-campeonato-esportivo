package com.mc857.copaamerica.state

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.mc857.copaamerica.platform.KeyValueStore
import com.mc857.copaamerica.platform.MemoryStore

/** The tournament in progress, as Home offers it: its session and the user's squad. */
data class TournamentInProgress(val sessionId: String, val squadName: String)

/**
 * Remembers the session of the tournament in progress on the device, so it can
 * be reopened after the app is closed. The server keeps the tournament itself.
 */
class SavedTournament(private val store: KeyValueStore = MemoryStore()) {
    var current by mutableStateOf(load())
        private set

    fun save(sessionId: String, squadName: String) {
        store.putString(SESSION_ID, sessionId)
        store.putString(SQUAD_NAME, squadName)
        current = TournamentInProgress(sessionId, squadName)
    }

    fun clear() {
        store.remove(SESSION_ID)
        store.remove(SQUAD_NAME)
        current = null
    }

    private fun load(): TournamentInProgress? {
        val sessionId = store.getString(SESSION_ID) ?: return null
        return TournamentInProgress(sessionId, store.getString(SQUAD_NAME).orEmpty())
    }

    private companion object {
        const val SESSION_ID = "tournament.sessionId"
        const val SQUAD_NAME = "tournament.squadName"
    }
}
