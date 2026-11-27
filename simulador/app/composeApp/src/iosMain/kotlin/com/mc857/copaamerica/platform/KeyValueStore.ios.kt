package com.mc857.copaamerica.platform

import platform.Foundation.NSUserDefaults

private object UserDefaultsStore : KeyValueStore {
    private val defaults = NSUserDefaults.standardUserDefaults
    override fun getString(key: String): String? = defaults.stringForKey(key)
    override fun putString(key: String, value: String) {
        defaults.setObject(value, forKey = key)
    }
    override fun remove(key: String) {
        defaults.removeObjectForKey(key)
    }
}

actual fun deviceStore(): KeyValueStore = UserDefaultsStore
