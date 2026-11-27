package com.mc857.copaamerica.platform

import kotlinx.browser.localStorage

// localStorage can throw (private windows, blocked site data): then the values
// just are not kept, and the app goes on.
private object LocalStorageStore : KeyValueStore {
    override fun getString(key: String): String? =
        try {
            localStorage.getItem(key)
        } catch (_: Throwable) {
            null
        }

    override fun putString(key: String, value: String) {
        try {
            localStorage.setItem(key, value)
        } catch (_: Throwable) {
        }
    }

    override fun remove(key: String) {
        try {
            localStorage.removeItem(key)
        } catch (_: Throwable) {
        }
    }
}

actual fun deviceStore(): KeyValueStore = LocalStorageStore
