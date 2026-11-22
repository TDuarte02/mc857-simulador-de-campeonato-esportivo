package com.mc857.copaamerica

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFontFamilyResolver
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.platform.Font
import androidx.compose.ui.window.ComposeViewport
import com.mc857.copaamerica.resources.Res
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.AppFontFamilies
import com.mc857.copaamerica.theme.LocalAppFontFamilies
import kotlinx.browser.document
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import org.jetbrains.compose.resources.ExperimentalResourceApi

@OptIn(ExperimentalComposeUiApi::class, ExperimentalResourceApi::class)
fun main() {
    ComposeViewport(document.body!!) {
        // Compose on the web draws text with its own fonts, not the system's,
        // and resource fonts load asynchronously, so text would show as empty
        // boxes for a while. Load every font up front: the app's families are
        // built from the bytes and handed to the theme (see Type.kt), and the
        // emoji font (a subset of Noto Color Emoji with only the glyphs the app
        // uses, for flags, ⚽, 🏆…) is preloaded as a fallback.
        val fontFamilyResolver = LocalFontFamilyResolver.current
        var fonts by remember { mutableStateOf<AppFontFamilies?>(null) }
        LaunchedEffect(Unit) {
            fonts = coroutineScope {
                val loaded = APP_FONTS.map { (file, weight) -> async { Font(file, Res.readBytes("font/$file.ttf"), weight) } }
                val emoji = Res.readBytes("files/NotoColorEmoji-subset.ttf")
                fontFamilyResolver.preload(FontFamily(Font("NotoColorEmoji", emoji)))
                val byFile = APP_FONTS.map { it.first }.zip(loaded.awaitAll()).toMap()
                fun family(prefix: String) = FontFamily(byFile.filterKeys { it.startsWith(prefix) }.values.toList())
                AppFontFamilies(display = family("barlow_"), mono = family("jetbrains_"), body = family("outfit_"))
            }
        }
        // Until then an empty page in the app's background color.
        Box(Modifier.fillMaxSize().background(AppColors.surface)) {
            fonts?.let { CompositionLocalProvider(LocalAppFontFamilies provides it) { CopaAmericaApp() } }
        }
    }
}

/** Files in commonMain/composeResources/font and their weights, as in theme/Type.kt. */
private val APP_FONTS = listOf(
    "barlow_semibold" to FontWeight.SemiBold, "barlow_bold" to FontWeight.Bold,
    "barlow_extrabold" to FontWeight.ExtraBold, "barlow_black" to FontWeight.Black,
    "jetbrains_medium" to FontWeight.Medium, "jetbrains_bold" to FontWeight.Bold,
    "outfit_medium" to FontWeight.Medium, "outfit_semibold" to FontWeight.SemiBold,
    "outfit_bold" to FontWeight.Bold, "outfit_extrabold" to FontWeight.ExtraBold,
)
