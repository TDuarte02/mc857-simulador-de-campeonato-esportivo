package com.mc857.copaamerica.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Vintage matchday paper: warm cream background + a grid of faint halftone
 * dots. Mirrors `.retro-paper` in design/src/index.css (radial-gradient dots,
 * 9px grid).
 */
fun Modifier.retroPaper(
    dotColor: Color = AppColors.ink.copy(alpha = 0.055f),
    spacing: Dp = 9.dp,
    dotRadius: Dp = 1.1.dp,
): Modifier = this
    .background(AppColors.paper)
    .drawWithCache {
        val spacingPx = spacing.toPx()
        val radiusPx = dotRadius.toPx()
        onDrawBehind {
            var y = spacingPx / 2
            while (y < size.height) {
                var x = spacingPx / 2
                while (x < size.width) {
                    drawCircle(color = dotColor, radius = radiusPx, center = Offset(x, y))
                    x += spacingPx
                }
                y += spacingPx
            }
        }
    }

/**
 * Diagonal pinstripes layered over a colored bar. Mirrors `.ticket-stripe`
 * (repeating-linear-gradient at 135deg, 6px stripe / 6px gap).
 */
fun Modifier.ticketStripe(
    stripeColor: Color = Color.White.copy(alpha = 0.30f),
    stripeWidth: Dp = 5.dp,
    gap: Dp = 7.dp,
): Modifier = this.drawWithCache {
    val stripeWidthPx = stripeWidth.toPx()
    val periodPx = stripeWidthPx + gap.toPx()
    onDrawBehind {
        rotate(degrees = -45f) {
            val diag = size.width + size.height
            var x = -diag
            while (x < diag) {
                drawRect(
                    color = stripeColor,
                    topLeft = Offset(x, -diag / 2f),
                    size = Size(stripeWidthPx, diag * 2f),
                )
                x += periodPx
            }
        }
    }
}

/**
 * Hard, un-blurred offset shadow, like the `box-shadow: Npx Npx 0 rgba(...)`
 * used on every card/button in the design. `Modifier.shadow` in Compose
 * always blurs, so this is a small custom draw instead.
 */
fun Modifier.hardShadow(
    color: Color = AppColors.ink.copy(alpha = 0.16f),
    offsetX: Dp = 3.dp,
    offsetY: Dp = 3.dp,
    cornerRadius: Dp = 16.dp,
): Modifier = this.drawBehind {
    drawRoundRect(
        color = color,
        topLeft = Offset(offsetX.toPx(), offsetY.toPx()),
        size = size,
        cornerRadius = CornerRadius(cornerRadius.toPx()),
    )
}

/** Small rotated-square "diamond" bullet used before kicker labels (◆ / •). */
fun Modifier.diamondBullet(color: Color, sizeDp: Dp = 6.dp): Modifier =
    this.size(sizeDp).background(color)
