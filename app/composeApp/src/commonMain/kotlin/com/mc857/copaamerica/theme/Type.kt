package com.mc857.copaamerica.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import org.jetbrains.compose.resources.Font
import com.mc857.copaamerica.resources.Res
import com.mc857.copaamerica.resources.barlow_black
import com.mc857.copaamerica.resources.barlow_bold
import com.mc857.copaamerica.resources.barlow_extrabold
import com.mc857.copaamerica.resources.barlow_semibold
import com.mc857.copaamerica.resources.jetbrains_bold
import com.mc857.copaamerica.resources.jetbrains_medium
import com.mc857.copaamerica.resources.outfit_bold
import com.mc857.copaamerica.resources.outfit_extrabold
import com.mc857.copaamerica.resources.outfit_medium
import com.mc857.copaamerica.resources.outfit_semibold

/**
 * Font families already loaded by the platform. The web provides these (built
 * from preloaded bytes) because resource fonts load asynchronously there and
 * text would render as empty boxes until they arrive; elsewhere it is null and
 * the families below come from compose resources.
 */
class AppFontFamilies(val display: FontFamily, val mono: FontFamily, val body: FontFamily)

val LocalAppFontFamilies = staticCompositionLocalOf<AppFontFamilies?> { null }

/** font-display — Barlow Condensed, used for every headline/label in the design. */
@Composable
fun displayFontFamily(): FontFamily = LocalAppFontFamilies.current?.display ?: FontFamily(
    Font(Res.font.barlow_semibold, FontWeight.SemiBold),
    Font(Res.font.barlow_bold, FontWeight.Bold),
    Font(Res.font.barlow_extrabold, FontWeight.ExtraBold),
    Font(Res.font.barlow_black, FontWeight.Black),
)

/** font-mono — JetBrains Mono, used for kickers, stats and tags. */
@Composable
fun monoFontFamily(): FontFamily = LocalAppFontFamilies.current?.mono ?: FontFamily(
    Font(Res.font.jetbrains_medium, FontWeight.Medium),
    Font(Res.font.jetbrains_bold, FontWeight.Bold),
)

/** font-body — Outfit, the default running text font. */
@Composable
fun bodyFontFamily(): FontFamily = LocalAppFontFamilies.current?.body ?: FontFamily(
    Font(Res.font.outfit_medium, FontWeight.Medium),
    Font(Res.font.outfit_semibold, FontWeight.SemiBold),
    Font(Res.font.outfit_bold, FontWeight.Bold),
    Font(Res.font.outfit_extrabold, FontWeight.ExtraBold),
)
