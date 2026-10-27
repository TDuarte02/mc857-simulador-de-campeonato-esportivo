package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
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

/**
 * The "▶" play glyph, drawn instead of typed: iOS renders U+25B6 as a color
 * emoji, so a text glyph looks different on each platform.
 */
@Composable
fun PlayTriangle(color: Color, size: androidx.compose.ui.unit.Dp = 9.dp, modifier: Modifier = Modifier) {
    Canvas(modifier.size(size)) {
        val path = Path().apply {
            moveTo(this@Canvas.size.width * 0.08f, 0f)
            lineTo(this@Canvas.size.width, this@Canvas.size.height / 2f)
            lineTo(this@Canvas.size.width * 0.08f, this@Canvas.size.height)
            close()
        }
        drawPath(path, color)
    }
}

/*
 * The icons below stand in for the "↺", "⌄" and "⚄" glyphs the design types
 * as text: none of the app's fonts have them, so on the web (which only has
 * the app's own fonts) they rendered as empty boxes.
 */

/** "↺" restart arrow: an open circle with the arrowhead pointing anticlockwise into the gap. */
@Composable
fun RestartIcon(color: Color, size: androidx.compose.ui.unit.Dp = 13.dp) {
    Canvas(Modifier.size(size)) {
        val strokeWidth = this.size.width * 0.14f
        val radius = this.size.width / 2f - strokeWidth
        val center = Offset(this.size.width / 2f, this.size.height / 2f)
        drawArc(
            color = color,
            startAngle = -60f,
            sweepAngle = 300f,
            useCenter = false,
            topLeft = Offset(center.x - radius, center.y - radius),
            size = Size(radius * 2, radius * 2),
            style = Stroke(width = strokeWidth, cap = StrokeCap.Round),
        )
        val angle = (-60.0).toRadians()
        val tip = Offset(center.x + radius * cos(angle).toFloat(), center.y + radius * sin(angle).toFloat())
        val tangent = Offset(sin(angle).toFloat(), -cos(angle).toFloat())
        val normal = Offset(cos(angle).toFloat(), sin(angle).toFloat())
        val head = strokeWidth * 2.2f
        val arrow = Path().apply {
            moveTo(tip.x + tangent.x * head, tip.y + tangent.y * head)
            lineTo(tip.x + normal.x * head, tip.y + normal.y * head)
            lineTo(tip.x - normal.x * head, tip.y - normal.y * head)
            close()
        }
        drawPath(arrow, color)
    }
}

/** "⌄" chevron used on dropdown triggers. */
@Composable
fun ChevronDownIcon(color: Color, size: androidx.compose.ui.unit.Dp = 10.dp) {
    Canvas(Modifier.size(size)) {
        val w = this.size.width
        val h = this.size.height
        val chevron = Path().apply {
            moveTo(w * 0.12f, h * 0.32f)
            lineTo(w * 0.5f, h * 0.7f)
            lineTo(w * 0.88f, h * 0.32f)
        }
        drawPath(chevron, color, style = Stroke(width = w * 0.2f, cap = StrokeCap.Round, join = StrokeJoin.Round))
    }
}

/** "⚄" die face showing five, on the "random lineup" button. */
@Composable
fun DieFiveIcon(color: Color, size: androidx.compose.ui.unit.Dp = 18.dp) {
    Canvas(Modifier.size(size)) {
        val w = this.size.width
        val strokeWidth = w * 0.1f
        drawRoundRect(
            color = color,
            topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
            size = Size(w - strokeWidth, w - strokeWidth),
            cornerRadius = CornerRadius(w * 0.18f),
            style = Stroke(width = strokeWidth),
        )
        val pip = w * 0.085f
        listOf(0.3f to 0.3f, 0.7f to 0.3f, 0.5f to 0.5f, 0.3f to 0.7f, 0.7f to 0.7f).forEach { (x, y) ->
            drawCircle(color, radius = pip, center = Offset(w * x, w * y))
        }
    }
}

private fun Double.toRadians(): Double = this * PI / 180.0

/** Outline user glyph from the masthead profile button (App.tsx, 24x24 viewBox SVG). */
@Composable
fun ProfileIcon(color: Color = AppColors.antiqueGold, size: androidx.compose.ui.unit.Dp = 19.dp) {
    Canvas(Modifier.size(size)) {
        val u = this.size.width / 24f
        val stroke = Stroke(width = 2.2f * u, cap = StrokeCap.Round)
        drawCircle(color, radius = 3.5f * u, center = Offset(12f * u, 8f * u), style = stroke)
        val shoulders = Path().apply {
            moveTo(5f * u, 20f * u)
            cubicTo(5.8f * u, 16.6f * u, 8.2f * u, 14.8f * u, 12f * u, 14.8f * u)
            cubicTo(15.8f * u, 14.8f * u, 18.2f * u, 16.6f * u, 19f * u, 20f * u)
        }
        drawPath(shoulders, color, style = stroke)
    }
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
            .clip(RoundedCornerShape(16.dp))
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
            .clip(RoundedCornerShape(16.dp))
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
            .clip(RoundedCornerShape(12.dp))
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
            .clip(CircleShape)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { content() }
}

val ScreenPadding = PaddingValues(horizontal = 20.dp)
