package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.theme.ticketStripe

/*
 * Desktop/web layout. Below WideLayoutMinWidth every screen keeps the phone
 * layout from the design; at or above it, App.kt shows WideNavBar on top and
 * the screens that have a wide variant switch to it (see LocalWideLayout).
 */

/** Window width from which the wide (desktop/web) layout is used. */
val WideLayoutMinWidth: Dp = 1000.dp

/** True when the window is at least [WideLayoutMinWidth] wide. Provided by App.kt. */
val LocalWideLayout = staticCompositionLocalOf { false }

/** Max content width of a wide page, inside the navbar. */
private val WidePageMaxWidth = 1200.dp

/** Tournament steps shown in the navbar, in order. */
enum class TournamentStep(val label: String) {
    TEAM("Seleção"),
    SQUAD("Elenco"),
    DRAW("Sorteio"),
    GROUPS("Grupos"),
    KNOCKOUT("Mata-mata"),
}

/** Ink top bar with the logo, the tournament steps and the "new tournament"/profile actions. */
@Composable
fun WideNavBar(step: TournamentStep?, onReset: (() -> Unit)?) {
    Column(Modifier.fillMaxWidth().background(AppColors.ink)) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(vertical = 14.dp),
            horizontalArrangement = Arrangement.Center,
        ) {
            Row(
                Modifier.widthIn(max = WidePageMaxWidth).fillMaxWidth().padding(horizontal = 32.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(28.dp),
            ) {
                Row {
                    Text("COPA ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.paper)
                    Text("AMÉRICA", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.antiqueGold)
                }
                if (step != null) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                        TournamentStep.entries.forEach { NavStep(it, current = step) }
                    }
                }
                Spacer(Modifier.weight(1f))
                if (onReset != null) {
                    Row(
                        Modifier
                            .height(40.dp)
                            .border(BorderStroke(2.dp, NavBorder), RoundedCornerShape(8.dp))
                            .clip(RoundedCornerShape(8.dp))
                            .clickable(onClick = onReset)
                            .padding(horizontal = 14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        RestartIcon(color = NavText)
                        Text("NOVO TORNEIO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.5.sp, color = NavText)
                    }
                }
                Box(
                    Modifier
                        .size(44.dp)
                        .background(AppColors.cream, CircleShape)
                        .border(BorderStroke(2.dp, AppColors.antiqueGold), CircleShape),
                    contentAlignment = Alignment.Center,
                ) { ProfileIcon() }
            }
        }
        Box(Modifier.fillMaxWidth().height(3.dp).background(AppColors.antiqueGold))
    }
}

private val NavText = Color(0xFFE9E2CF)
private val NavMuted = Color(0xFF9AA3B5)
private val NavBorder = Color(0xFF3A4560)

@Composable
private fun NavStep(step: TournamentStep, current: TournamentStep) {
    val done = step.ordinal < current.ordinal
    val isCurrent = step == current
    Row(
        Modifier
            .height(36.dp)
            .background(if (isCurrent) AppColors.antiqueGold else Color.Transparent, RoundedCornerShape(50))
            .padding(start = 6.dp, end = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        val dotModifier = Modifier.size(22.dp)
        Box(
            when {
                isCurrent -> dotModifier.background(AppColors.ink, CircleShape)
                done -> dotModifier.background(AppColors.antiqueGold, CircleShape)
                else -> dotModifier.border(BorderStroke(1.5.dp, Color(0xFF4A5570)), CircleShape)
            },
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "${step.ordinal + 1}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp,
                color = when {
                    isCurrent -> AppColors.antiqueGold
                    done -> AppColors.ink
                    else -> NavMuted
                },
            )
        }
        Text(
            step.label.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp,
            color = when {
                isCurrent -> AppColors.ink
                done -> NavText
                else -> NavMuted
            },
        )
    }
}

/** Scrollable paper page with a centered content column of up to 1200dp. */
@Composable
fun WidePage(content: @Composable ColumnScope.() -> Unit) {
    Box(
        Modifier.fillMaxSize().retroPaper().verticalScroll(rememberScrollState()),
        contentAlignment = Alignment.TopCenter,
    ) {
        Column(
            Modifier.widthIn(max = WidePageMaxWidth).fillMaxWidth().padding(horizontal = 32.dp, vertical = 36.dp),
            content = content,
        )
    }
}

/** The phone layout, centered in a phone-width column (a no-op on actual phones). */
@Composable
fun WideNarrowColumn(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize().retroPaper(), contentAlignment = Alignment.TopCenter) {
        Box(Modifier.widthIn(max = 560.dp).fillMaxHeight()) { content() }
    }
}

/** "‹ LABEL" text link back to the previous step. */
@Composable
fun WideBackLink(text: String, onClick: () -> Unit) {
    Row(
        Modifier
            .clip(RoundedCornerShape(6.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text("‹", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 18.sp, color = AppColors.kicker)
        Text(text.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.kicker)
    }
}

/** Two-tone page title, e.g. "ESCOLHA SEU" + gold "PAÍS"; one text so it wraps between words. */
@Composable
fun WideTitle(text: String, accent: String, fontSize: TextUnit = 52.sp) {
    Text(
        buildAnnotatedString {
            append("$text ")
            withStyle(SpanStyle(color = AppColors.antiqueGold)) { append(accent) }
        },
        fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = fontSize, lineHeight = fontSize, color = AppColors.ink,
    )
}

/**
 * Page heading: a back link or a kicker above a two-tone title, with optional
 * content (a status line, filters…) aligned to the bottom right.
 */
@Composable
fun WidePageHeader(
    title: String,
    accent: String,
    back: Pair<String, () -> Unit>? = null,
    kicker: String? = null,
    trailing: @Composable (RowScope.() -> Unit)? = null,
) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.weight(1f)) {
            back?.let { (label, onClick) -> WideBackLink(label, onClick) }
            kicker?.let { KickerLabel(it) }
            Spacer(Modifier.height(6.dp))
            WideTitle(title, accent)
        }
        trailing?.invoke(this)
    }
    Spacer(Modifier.height(24.dp))
}

/** "◆ LABEL ————" section heading with a rule filling the rest of the row. */
@Composable
fun WideSectionRule(text: String, modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        KickerLabel(text = text, color = AppColors.ink)
        Spacer(Modifier.width(12.dp))
        Box(Modifier.weight(1f).height(2.dp).background(AppColors.paperBorder))
    }
}

/** Small uppercase mono label used above sidebar groups ("POSIÇÃO", "SUA SELEÇÃO"…). */
@Composable
fun WideCaption(text: String, color: Color = AppColors.kicker) {
    Text(text.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 2.sp, color = color)
}

/** Cream card with a striped colored bar on top (the "ticket" look). */
@Composable
fun WideTicketCard(
    modifier: Modifier = Modifier,
    bar: Color = AppColors.ticketOrange,
    border: Color = AppColors.ink,
    background: Color = AppColors.cream,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .hardShadow(cornerRadius = 16.dp)
            .background(background, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, border), RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp)),
    ) {
        Box(Modifier.fillMaxWidth().height(12.dp).background(bar).ticketStripe())
        content()
    }
}

/** Cream card with the ink header strip + gold rule used by the scoreboard and summaries. */
@Composable
fun WideInkHeaderCard(
    title: String,
    trailing: String,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .hardShadow(cornerRadius = 16.dp)
            .background(AppColors.cream, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp)),
    ) {
        Row(
            Modifier.fillMaxWidth().background(AppColors.ink).padding(horizontal = 18.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(title.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.paper)
            Text(trailing.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.antiqueGold)
        }
        Box(Modifier.fillMaxWidth().height(2.dp).background(AppColors.antiqueGold))
        content()
    }
}

/**
 * Non-lazy grid for content inside a scrolling [WidePage]: as many columns of
 * at least [minCellWidth] as fit, items laid out row by row.
 */
@Composable
fun <T> WideGrid(
    items: List<T>,
    minCellWidth: Dp,
    modifier: Modifier = Modifier,
    gap: Dp = 14.dp,
    cell: @Composable (T) -> Unit,
) {
    BoxWithConstraints(modifier) {
        val columns = ((maxWidth + gap) / (minCellWidth + gap)).toInt().coerceAtLeast(1)
        Column(verticalArrangement = Arrangement.spacedBy(gap)) {
            items.chunked(columns).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(gap)) {
                    row.forEach { item -> Box(Modifier.weight(1f)) { cell(item) } }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}

/** Big flag over a team name, for "team × rival" match-ups. */
@Composable
fun WideFlagName(flag: String, name: String, color: Color, modifier: Modifier = Modifier, flagSize: TextUnit = 44.sp) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(flag, fontSize = flagSize)
        Text(name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 20.sp, color = color, maxLines = 1)
    }
}

/** Thin rounded progress bar. */
@Composable
fun WideProgressBar(fraction: Float, color: Color, height: Dp = 8.dp) {
    Box(Modifier.fillMaxWidth().height(height).background(Color(0xFFEFE7D2), RoundedCornerShape(50))) {
        Box(
            Modifier
                .fillMaxWidth(fraction.coerceIn(0f, 1f))
                .height(height)
                .background(color, RoundedCornerShape(50)),
        )
    }
}

/** 44dp-tall search box. */
@Composable
fun WideSearchField(value: String, onValueChange: (String) -> Unit, placeholder: String, modifier: Modifier = Modifier) {
    Box(
        modifier
            .height(44.dp)
            .background(AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(12.dp))
            .padding(horizontal = 14.dp),
        contentAlignment = Alignment.CenterStart,
    ) {
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            singleLine = true,
            textStyle = TextStyle(fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.ink),
            modifier = Modifier.fillMaxWidth(),
            decorationBox = { inner ->
                if (value.isEmpty()) Text(placeholder, fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.mutedText)
                inner()
            },
        )
    }
}

/** 44dp-tall filter chip: ink when active, cream otherwise. */
@Composable
fun WideChip(text: String, active: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .height(44.dp)
            .background(if (active) AppColors.ink else AppColors.cream, RoundedCornerShape(10.dp))
            .border(BorderStroke(2.dp, if (active) AppColors.ink else AppColors.paperBorder), RoundedCornerShape(10.dp))
            .clip(RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.5.sp,
            color = if (active) AppColors.paper else AppColors.ink,
        )
    }
}
