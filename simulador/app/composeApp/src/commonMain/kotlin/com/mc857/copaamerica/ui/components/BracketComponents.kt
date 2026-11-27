package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.model.Bracket
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.monoFontFamily

/** One tie of the bracket: two rows, one per side. [match] null means the sides are still unknown. */
@Composable
fun TieCard(match: Match?, label: String, userSquadId: String, large: Boolean = false) {
    val isUserTie = match != null && match.involves(userSquadId)
    val borderColor = if (isUserTie) AppColors.antiqueGold else AppColors.paperBorder
    val result = match?.result
    Column(
        Modifier
            .width(if (large) 200.dp else 104.dp)
            .background(AppColors.cream, RoundedCornerShape(8.dp))
            .border(BorderStroke(2.dp, borderColor), RoundedCornerShape(8.dp)),
    ) {
        Text(
            text = label,
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = if (large) 12.sp else 11.sp,
            letterSpacing = 0.5.sp,
            color = if (isUserTie) AppColors.antiqueGold else AppColors.kicker,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .fillMaxWidth()
                .background(if (isUserTie) AppColors.ticketOrangeBg else AppColors.paper)
                .padding(horizontal = if (large) 10.dp else 6.dp, vertical = if (large) 4.dp else 2.dp),
        )
        val penalties = result?.penalties
        TieCardRow(match?.home, goalsLabel(result?.homeGoals, penalties?.home), result?.winner, userSquadId, large)
        Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        TieCardRow(match?.away, goalsLabel(result?.awayGoals, penalties?.away), result?.winner, userSquadId, large)
    }
}

/** "1", or "1 (4)" after a shootout. */
private fun goalsLabel(goals: Int?, penalties: Int?): String = when {
    goals == null -> "–"
    penalties == null -> "$goals"
    else -> "$goals ($penalties)"
}

@Composable
private fun TieCardRow(side: Squad?, goals: String, winner: String?, userSquadId: String, large: Boolean) {
    val isWinner = side != null && winner == side.id
    val isUser = side != null && side.id == userSquadId
    val textColor = when {
        isWinner -> AppColors.antiqueGold
        side == null -> AppColors.mutedText
        isUser -> AppColors.antiqueGold
        else -> AppColors.ink
    }
    Row(
        Modifier
            .fillMaxWidth()
            .background(if (isWinner) AppColors.ticketOrangeBg else Color.Transparent)
            .padding(horizontal = if (large) 10.dp else 6.dp, vertical = if (large) 8.dp else 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        FlagImage(side?.flag, height = if (large) 16.dp else 10.dp)
        Spacer(Modifier.width(if (large) 8.dp else 4.dp))
        Text(
            text = side?.name ?: "A definir",
            fontFamily = displayFontFamily(),
            fontWeight = FontWeight.ExtraBold,
            fontSize = if (large) 16.sp else 11.sp,
            color = textColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = goals,
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = if (large) 14.sp else 11.sp,
            color = if (isWinner) AppColors.antiqueGold else AppColors.kicker,
        )
    }
}

@Composable
private fun TieColumn(ties: List<Match?>, labels: List<String>, userSquadId: String, large: Boolean) {
    Column(Modifier.fillMaxHeight(), verticalArrangement = Arrangement.SpaceEvenly) {
        ties.forEachIndexed { index, match ->
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                TieCard(match = match, label = labels.getOrElse(index) { "" }, userSquadId = userSquadId, large = large)
            }
        }
    }
}

@Composable
private fun ConnectorColumn(pairCount: Int, width: Dp = 20.dp) {
    Column(Modifier.width(width).fillMaxHeight()) {
        repeat(pairCount) {
            Box(Modifier.weight(1f).fillMaxWidth()) {
                // Simple "]"-style connector: a vertical tick centered in the pair's band.
                Box(
                    Modifier
                        .align(Alignment.Center)
                        .width(width / 2)
                        .height(1.dp)
                        .background(AppColors.paperBorder),
                )
            }
        }
    }
}

/**
 * The whole knockout tree: quarters → semis → final, left to right.
 * [large] is the wide (desktop/web) variant: bigger cards spread over the full width.
 */
@Composable
fun BracketTree(bracket: Bracket, userSquadId: String, large: Boolean = false) {
    val connector = if (large) 56.dp else 20.dp
    val quarterFinals = List(4) { bracket.quarterFinals.getOrNull(it) }
    val semiFinals = List(2) { bracket.semiFinals.getOrNull(it) }
    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .height(if (large) 480.dp else 340.dp),
        horizontalArrangement = if (large) Arrangement.Center else Arrangement.Start,
    ) {
        TieColumn(quarterFinals, listOf("Quartas 1", "Quartas 2", "Quartas 3", "Quartas 4"), userSquadId, large)
        ConnectorColumn(pairCount = quarterFinals.size / 2, width = connector)
        TieColumn(semiFinals, listOf("Semifinal 1", "Semifinal 2"), userSquadId, large)
        ConnectorColumn(pairCount = semiFinals.size / 2, width = connector)
        TieColumn(listOf(bracket.final), listOf("Final"), userSquadId, large)
    }
}
