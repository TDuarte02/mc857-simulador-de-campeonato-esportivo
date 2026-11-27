package com.mc857.copaamerica.theme

import androidx.compose.ui.graphics.Color

/**
 * Mirrors the CSS custom properties and one-off hex values used throughout
 * design/src/index.css and design/src/App.tsx — same names, same values.
 */
object AppColors {
    // Theme tokens (index.css @theme block)
    val gold = Color(0xFFF59E0B)
    val goldDark = Color(0xFFD97706)
    val crimson = Color(0xFFEF4444)
    val emerald = Color(0xFF10B981)
    val surface = Color(0xFFF5F7FA)
    val card = Color(0xFFFFFFFF)
    val card2 = Color(0xFFEEF2F7)
    val border = Color(0xFFDCE3EC)

    // Vintage matchday paper palette (used across every screen)
    val paper = Color(0xFFF6F1E5)
    val ink = Color(0xFF172033)
    val antiqueGold = Color(0xFFB8860B)
    val paperBorder = Color(0xFFC9BFA6)
    val kicker = Color(0xFF8A6D1F)
    val bodyText = Color(0xFF6B5B3E)
    val mutedText = Color(0xFF8A7B5E)
    val cream = Color(0xFFFFFDF5)
    val ticketOrange = Color(0xFFD97706)
    val ticketOrangeBg = Color(0xFFFFF7E6)
    val ticketOrangeText = Color(0xFFB45309)
    val ticketGreen = Color(0xFF059669)
    val ticketGreenBg = Color(0xFFEAF8EF)
    val ticketGreenText = Color(0xFF047857)
    val ticketBlue = Color(0xFF2563EB)
    val ticketBlueBg = Color(0xFFEAF3FF)
    val ticketBlueText = Color(0xFF1D4ED8)
    val winGreenBg = Color(0xFFEAF3EC)
    val lossRedBg = Color(0xFFF7EBEB)
    val lossRed = Color(0xFFB91C1C)
    val rowBorder = Color(0xFFE4DCC6)
    val fieldGreenTop = Color(0xFF1D7A42)
    val fieldGreenMid = Color(0xFF176B39)
    val fieldGreenBottom = Color(0xFF145B32)

    /** Rating chip color, mirrors the `rc()` helper in App.tsx. */
    fun forRating(rating: Int): Color = when {
        rating >= 95 -> Color(0xFFB8860B)
        rating >= 90 -> Color(0xFFB45309)
        rating >= 85 -> Color(0xFF6B7A2E)
        else -> Color(0xFF8A7B5E)
    }
}
