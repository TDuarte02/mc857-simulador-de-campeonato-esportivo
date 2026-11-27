package com.mc857.copaamerica.state

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Placement
import com.mc857.copaamerica.platform.KeyValueStore
import com.mc857.copaamerica.platform.MemoryStore

/**
 * The user's record, kept on the device: the API has no users, so it cannot
 * tell that two tournaments belong to the same person.
 */
class PlayerStats(private val store: KeyValueStore = MemoryStore()) {
    /** Single-player cups won (Modo Clássico), shown on Home. */
    var cupsWon by mutableStateOf(store.getString(CUPS_WON)?.toIntOrNull() ?: 0)
        private set

    /**
     * Counts the cup when [history] says the user is champion. The history of a
     * session is fetched more than once, so each session counts at most once.
     */
    fun record(history: History) {
        if (history.placement != Placement.CHAMPION) return
        if (store.getString(LAST_COUNTED_SESSION) == history.sessionId) return
        cupsWon += 1
        store.putString(CUPS_WON, cupsWon.toString())
        store.putString(LAST_COUNTED_SESSION, history.sessionId)
    }

    private companion object {
        const val CUPS_WON = "stats.singlePlayer.cupsWon"
        const val LAST_COUNTED_SESSION = "stats.singlePlayer.lastCountedSession"
    }
}
