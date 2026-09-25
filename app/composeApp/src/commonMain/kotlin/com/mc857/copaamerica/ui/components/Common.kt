package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily

/** The rotated-square "◆" bullet used before every kicker label. */
@Composable
fun DiamondBullet(color: Color = AppColors.antiqueGold, size: androidx.compose.ui.unit.Dp = 6.dp) {
    Box(
        Modifier
            .size(size)
            .rotate(45f)
            .background(color),
    )
}

/** Small uppercase mono label with a diamond bullet, e.g. "◆ Copa América". */
@Composable
fun KickerLabel(text: String, color: Color = AppColors.kicker, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        DiamondBullet(color = AppColors.antiqueGold)
        Text(
            text = text.uppercase(),
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = 12.sp,
            letterSpacing = 1.5.sp,
            color = color,
        )
    }
}

/** The big gold CTA button used at the bottom of almost every screen. */
@Composable
fun RetroPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    val bg = if (enabled) AppColors.ticketOrange else Color(0xFFEFE7D2)
    val fg = if (enabled) AppColors.cream else AppColors.mutedText
    val border = if (enabled) AppColors.ink else AppColors.paperBorder
    Box(
        modifier = modifier
            .then(if (enabled) Modifier.hardShadow(color = AppColors.ink.copy(alpha = 0.22f), cornerRadius = 16.dp) else Modifier)
            .background(bg, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, border), RoundedCornerShape(16.dp))
            .then(if (enabled) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(vertical = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text.uppercase(),
            fontFamily = displayFontFamily(),
            fontWeight = FontWeight.Black,
            fontSize = 17.sp,
            letterSpacing = 1.sp,
            color = fg,
            textAlign = TextAlign.Center,
        )
    }
}

/** Secondary (outline) button, used for "Novo torneio" and similar lower-priority actions. */
@Composable
fun RetroSecondaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .background(AppColors.cream, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 13.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = text.uppercase(),
            fontFamily = displayFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = 14.sp,
            letterSpacing = 1.sp,
            color = AppColors.bodyText,
            textAlign = TextAlign.Center,
        )
    }
}

/** Small filled chip used for role tags ("ZAG", "MEI", …). */
@Composable
fun RoleChip(text: String, background: Color) {
    Box(
        Modifier
            .background(background, RoundedCornerShape(6.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Text(
            text = text,
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = 11.sp,
            letterSpacing = 0.5.sp,
            color = AppColors.cream,
        )
    }
}

/** Round icon button (used for back arrow, reset, FABs). */
@Composable
fun RetroIconButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    background: Color = AppColors.cream,
    border: Color = AppColors.ink,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .size(36.dp)
            .hardShadow(color = AppColors.ink.copy(alpha = 0.16f), offsetX = 2.dp, offsetY = 2.dp, cornerRadius = 12.dp)
            .background(background, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, border), RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { content() }
}

@Composable
fun CircleFab(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    background: Color = AppColors.ticketOrange,
    content: @Composable () -> Unit,
) {
    Box(
        modifier = modifier
            .size(48.dp)
            .hardShadow(color = AppColors.ink.copy(alpha = 0.24f), cornerRadius = 100.dp)
            .background(background, CircleShape)
            .border(BorderStroke(2.dp, AppColors.ink), CircleShape)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { content() }
}

val ScreenPadding = PaddingValues(horizontal = 20.dp)
