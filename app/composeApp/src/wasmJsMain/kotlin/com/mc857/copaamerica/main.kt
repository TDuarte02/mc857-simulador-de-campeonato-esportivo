package com.mc857.copaamerica

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.widthIn
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFontFamilyResolver
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.platform.Font
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.ComposeViewport
import com.mc857.copaamerica.resources.Res
import com.mc857.copaamerica.theme.AppColors
import kotlinx.browser.document
import org.jetbrains.compose.resources.ExperimentalResourceApi

@OptIn(ExperimentalComposeUiApi::class, ExperimentalResourceApi::class)
fun main() {
    ComposeViewport(document.body!!) {
        // Compose on the web draws text with its own fonts, not the system's,
        // so emoji (team flags, ⚽, 🏆…) need an emoji font preloaded as a
        // fallback. The file is a subset of Noto Color Emoji with only the
        // glyphs the app uses.
        val fontFamilyResolver = LocalFontFamilyResolver.current
        var emojiLoaded by remember { mutableStateOf(false) }
        LaunchedEffect(Unit) {
            val bytes = Res.readBytes("files/NotoColorEmoji-subset.ttf")
            fontFamilyResolver.preload(FontFamily(Font("NotoColorEmoji", bytes)))
            emojiLoaded = true
        }
        // The app is designed for a phone frame (design/: 390x844); on wide
        // browser windows keep it in a centered phone-width column.
        Box(Modifier.fillMaxSize().background(AppColors.surface), contentAlignment = Alignment.TopCenter) {
            Box(Modifier.fillMaxHeight().widthIn(max = 480.dp)) {
                if (emojiLoaded) CopaAmericaApp()
            }
        }
    }
}
