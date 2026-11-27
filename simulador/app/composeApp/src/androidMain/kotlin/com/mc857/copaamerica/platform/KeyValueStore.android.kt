package com.mc857.copaamerica.platform

import android.content.Context

private class SharedPreferencesStore(context: Context) : KeyValueStore {
    private val preferences = context.getSharedPreferences("copa_america", Context.MODE_PRIVATE)
    override fun getString(key: String): String? = preferences.getString(key, null)
    override fun putString(key: String, value: String) {
        preferences.edit().putString(key, value).apply()
    }
    override fun remove(key: String) {
        preferences.edit().remove(key).apply()
    }
}

actual fun deviceStore(): KeyValueStore = SharedPreferencesStore(AndroidContextHolder.appContext)
