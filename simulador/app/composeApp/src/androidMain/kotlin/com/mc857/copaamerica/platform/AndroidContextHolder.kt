package com.mc857.copaamerica.platform

import android.content.Context

/** Set once from MainActivity so platform actuals (share, etc.) have a Context to work with. */
object AndroidContextHolder {
    lateinit var appContext: Context
}
