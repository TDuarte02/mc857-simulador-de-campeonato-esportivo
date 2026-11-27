package com.mc857.copaamerica.platform

/** Small string values that survive restarts, kept on the device. */
interface KeyValueStore {
    fun getString(key: String): String?
    fun putString(key: String, value: String)
    fun remove(key: String)
}

/** The device's own store: SharedPreferences, NSUserDefaults or localStorage. */
expect fun deviceStore(): KeyValueStore

/** Lives only as long as the process; for tests and as a fallback. */
class MemoryStore : KeyValueStore {
    private val values = mutableMapOf<String, String>()
    override fun getString(key: String): String? = values[key]
    override fun putString(key: String, value: String) {
        values[key] = value
    }
    override fun remove(key: String) {
        values.remove(key)
    }
}
