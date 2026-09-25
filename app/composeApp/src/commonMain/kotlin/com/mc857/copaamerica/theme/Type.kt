package com.mc857.copaamerica.theme

import androidx.compose.runtime.Composable
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

/** font-display — Barlow Condensed, used for every headline/label in the design. */
@Composable
fun displayFontFamily(): FontFamily = FontFamily(
    Font(Res.font.barlow_semibold, FontWeight.SemiBold),
    Font(Res.font.barlow_bold, FontWeight.Bold),
    Font(Res.font.barlow_extrabold, FontWeight.ExtraBold),
    Font(Res.font.barlow_black, FontWeight.Black),
)

/** font-mono — JetBrains Mono, used for kickers, stats and tags. */
@Composable
fun monoFontFamily(): FontFamily = FontFamily(
    Font(Res.font.jetbrains_medium, FontWeight.Medium),
    Font(Res.font.jetbrains_bold, FontWeight.Bold),
)

/** font-body — Outfit, the default running text font. */
@Composable
fun bodyFontFamily(): FontFamily = FontFamily(
    Font(Res.font.outfit_medium, FontWeight.Medium),
    Font(Res.font.outfit_semibold, FontWeight.SemiBold),
    Font(Res.font.outfit_bold, FontWeight.Bold),
    Font(Res.font.outfit_extrabold, FontWeight.ExtraBold),
)
