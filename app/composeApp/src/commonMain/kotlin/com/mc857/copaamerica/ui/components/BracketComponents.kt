package com.mc857.copaamerica.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.tieLine
import com.mc857.copaamerica.domain.model.KnockoutTie
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily

/** One tie of the bracket: two rows, one per side. Mirrors TieCard, App.tsx:1167-1197. */
@Composable
fun TieCard(tie: KnockoutTie, label: String, highlightName: String? = null, emptyLabel: String = "A definir") {
    val isUserTie = tie.home?.name == highlightName || tie.away?.name == highlightName
    val borderColor = if (isUserTie) AppColors.antiqueGold else AppColors.paperBorder
    Column(
        Modifier
            .width(104.dp)
            .background(AppColors.cream, RoundedCornerShape(8.dp))
            .border(BorderStroke(2.dp, borderColor), RoundedCornerShape(8.dp)),
    ) {
        Text(
            text = label,
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = 11.sp,
            letterSpacing = 0.5.sp,
            color = if (isUserTie) AppColors.antiqueGold else AppColors.kicker,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .fillMaxWidth()
                .background(if (isUserTie) AppColors.ticketOrangeBg else AppColors.paper)
                .padding(horizontal = 6.dp, vertical = 2.dp),
        )
        TieCardRow(tie.home, tie.homeGoals, tie.winner, highlightName, emptyLabel)
        Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        TieCardRow(tie.away, tie.awayGoals, tie.winner, highlightName, emptyLabel)
    }
}

@Composable
private fun TieCardRow(side: PoolTeam?, goals: Int?, winner: PoolTeam?, highlightName: String?, emptyLabel: String) {
    val isWinner = winner != null && winner.name == side?.name
    val isUser = side != null && side.name == highlightName
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
            .padding(horizontal = 6.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(side?.flag ?: "🎱", fontSize = 13.sp)
        Spacer(Modifier.width(4.dp))
        Text(
            text = side?.name ?: emptyLabel,
            fontFamily = displayFontFamily(),
            fontWeight = FontWeight.ExtraBold,
            fontSize = 11.sp,
            color = textColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = goals?.toString() ?: "–",
            fontFamily = monoFontFamily(),
            fontWeight = FontWeight.Bold,
            fontSize = 11.sp,
            color = if (isWinner) AppColors.antiqueGold else AppColors.kicker,
        )
    }
}

@Composable
private fun TieColumn(ties: List<KnockoutTie>, labels: List<String>, highlightName: String?, emptyLabel: String = "A definir") {
    Column(Modifier.fillMaxHeight(), verticalArrangement = androidx.compose.foundation.layout.Arrangement.SpaceEvenly) {
        ties.forEachIndexed { index, tie ->
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                TieCard(tie = tie, label = labels.getOrElse(index) { "" }, highlightName = highlightName, emptyLabel = emptyLabel)
            }
        }
    }
}

@Composable
private fun ConnectorColumn(pairCount: Int) {
    Column(Modifier.width(20.dp).fillMaxHeight()) {
        repeat(pairCount) {
            Box(Modifier.weight(1f).fillMaxWidth()) {
                // Simple "]"-style connector: a vertical tick centered in the pair's band.
                Box(
                    Modifier
                        .align(Alignment.Center)
                        .width(10.dp)
                        .height(1.dp)
                        .background(AppColors.paperBorder),
                )
            }
        }
    }
}

/** The whole knockout tree: quarters → semis → final, left to right. Mirrors BracketTree, App.tsx:1237-1250. */
@Composable
fun BracketTree(qf: List<KnockoutTie>, sf: List<KnockoutTie>, final: KnockoutTie, highlightName: String?, emptyLabel: String = "A definir") {
    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .height(340.dp),
    ) {
        TieColumn(ties = qf, labels = listOf("Quartas 1", "Quartas 2", "Quartas 3", "Quartas 4"), highlightName = highlightName, emptyLabel = emptyLabel)
        ConnectorColumn(pairCount = qf.size / 2)
        TieColumn(ties = sf, labels = listOf("Semifinal 1", "Semifinal 2"), highlightName = highlightName)
        ConnectorColumn(pairCount = sf.size / 2)
        TieColumn(ties = listOf(final), labels = listOf("Final"), highlightName = highlightName)
    }
}

/** Podium-style recap blocks for the 3rd-place tie and the final. Mirrors KnockoutSummary, App.tsx:1258-1276. */
@Composable
fun KnockoutSummary(third: KnockoutTie, final: KnockoutTie) {
    if (third.winner == null && final.winner == null) return
    Column(verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(8.dp)) {
        if (third.winner != null) {
            SummaryRow(title = "🥉 Disputa pelo 3º lugar", line = tieLine(third))
        }
        if (final.winner != null) {
            SummaryRow(title = "🏆 Final", line = tieLine(final))
        }
    }
}

@Composable
private fun SummaryRow(title: String, line: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .hardShadow(cornerRadius = 12.dp)
            .background(AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(12.dp))
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        Text(title, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker)
        Text(line, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
    }
}
