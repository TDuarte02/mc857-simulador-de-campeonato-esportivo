@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.groupCount
import com.mc857.copaamerica.domain.logic.groupMatchLabel
import com.mc857.copaamerica.domain.logic.groupTieBreakers
import com.mc857.copaamerica.domain.logic.rankGroups
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.GroupMatch
import com.mc857.copaamerica.domain.model.MatchStatus
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar

private val FORMAT_LABEL = "Modo clássico"

/** Mirrors GroupStage, App.tsx:1446-1585. */
@Composable
fun GroupStageScreen(
    bracket: DrawnBracket,
    team: TeamData,
    onPlayNext: (GroupMatch) -> Unit,
    onQuarterfinals: () -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    var tiebreakOpen by remember { mutableStateOf(false) }
    val userGroup = bracket.groups.firstOrNull { g -> g.teams.any { it.name == team.name } }
    val userMatches = userGroup?.matches?.filter { it.home.name == team.name || it.away.name == team.name } ?: emptyList()
    val nextMatch = userMatches.firstOrNull { it.status == MatchStatus.PENDING }
    val groupsComplete = bracket.groups.isNotEmpty() && bracket.groups.all { g -> g.matches.all { it.status == MatchStatus.PLAYED } }
    val rankedGroups = rankGroups(bracket.groups)

    Box(Modifier.fillMaxSize()) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Fase de grupos", sub = "$FORMAT_LABEL · ${groupCount(bracket.format)} grupos de 4", onBack = onBack, onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(20.dp)) {
            if (!groupsComplete && userGroup != null) {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp)
                        .hardShadow(color = AppColors.antiqueGold.copy(alpha = 0.35f), cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp)),
                ) {
                    Row(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 12.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("SEU GRUPO · GRUPO ${userGroup.name}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                        Text("${userMatches.count { it.status == MatchStatus.PLAYED }}/3 partidas", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                    }
                    userMatches.forEachIndexed { index, match ->
                        Row(
                            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text("J${index + 1}", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                            Text(groupMatchLabel(match), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink, modifier = Modifier.weight(1f), maxLines = 1)
                            when {
                                match.status == MatchStatus.PLAYED -> Text("${match.homeGoals}–${match.awayGoals}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ticketGreen)
                                match.id == nextMatch?.id -> Text("PRÓXIMO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.antiqueGold)
                                else -> Text("PENDENTE", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.kicker)
                            }
                        }
                    }
                }
            }

            KickerLabel(if (groupsComplete) "Classificação final" else "Classificação provisória", modifier = Modifier.padding(bottom = 8.dp))

            rankedGroups.forEach { group ->
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 12.dp)
                        .hardShadow(cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
                ) {
                    Row(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 12.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("GRUPO ${group.name}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                        if (group.name == userGroup?.name) {
                            Text("${userMatches.count { it.status == MatchStatus.PLAYED }}/3 jogos seus", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                        }
                    }
                    group.standings.forEachIndexed { index, standing ->
                        val qualified = groupsComplete && index < 2
                        val isUser = standing.team.name == team.name
                        val eliminated = groupsComplete && isUser && !qualified
                        val rowBg = when {
                            isUser && groupsComplete -> if (qualified) AppColors.winGreenBg else AppColors.lossRedBg
                            isUser -> AppColors.ticketOrangeBg
                            qualified -> AppColors.winGreenBg
                            else -> Color.Transparent
                        }
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .background(rowBg)
                                .padding(start = 10.dp, end = 12.dp, top = 10.dp, bottom = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Box(Modifier.width(4.dp).height(20.dp).background(if (qualified) AppColors.ticketGreen else if (eliminated) AppColors.lossRed else Color.Transparent))
                            Spacer(Modifier.width(8.dp))
                            Text("${index + 1}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = if (qualified) AppColors.ticketGreen else if (eliminated) AppColors.lossRed else AppColors.mutedText)
                            Spacer(Modifier.width(6.dp))
                            Text(standing.team.flag, fontSize = 15.sp)
                            Spacer(Modifier.width(6.dp))
                            Text(
                                standing.team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp,
                                color = if (isUser) AppColors.antiqueGold else AppColors.ink, modifier = Modifier.weight(1f), maxLines = 1,
                            )
                            if (qualified) Text("CLASSIFICADO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 9.sp, color = AppColors.ticketGreen)
                            if (eliminated) Text("ELIMINADO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 9.sp, color = AppColors.lossRed)
                            Spacer(Modifier.width(6.dp))
                            Text("${standing.played}J", fontFamily = monoFontFamily(), fontSize = 10.sp, color = AppColors.mutedText)
                            Spacer(Modifier.width(4.dp))
                            Text("${standing.won}V ${standing.drawn}E ${standing.lost}D", fontFamily = monoFontFamily(), fontSize = 10.sp, color = AppColors.mutedText)
                            Spacer(Modifier.width(6.dp))
                            Text("${standing.points}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ink)
                        }
                    }
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            when {
                nextMatch != null && !groupsComplete -> RetroPrimaryButton("Jogar próxima partida", onClick = { onPlayNext(nextMatch) }, modifier = Modifier.fillMaxWidth())
                groupsComplete -> RetroPrimaryButton("Ver quartas de final", onClick = onQuarterfinals, modifier = Modifier.fillMaxWidth())
                else -> Box(
                    Modifier
                        .fillMaxWidth()
                        .background(AppColors.winGreenBg, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.ticketGreen), RoundedCornerShape(16.dp))
                        .padding(vertical = 12.dp),
                    contentAlignment = Alignment.Center,
                ) { Text("PROCESSANDO CLASSIFICAÇÃO", fontFamily = monoFontFamily(), fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.ticketGreen) }
            }
        }
    }

    Box(Modifier.fillMaxSize().padding(20.dp), contentAlignment = Alignment.BottomEnd) {
        Box(Modifier.padding(bottom = 96.dp)) {
            CircleFab(onClick = { tiebreakOpen = true }) { Text("i", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 18.sp, color = AppColors.cream) }
        }
    }
    } // Box

    if (tiebreakOpen) {
        ModalBottomSheet(onDismissRequest = { tiebreakOpen = false }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 24.dp)) {
                KickerLabel("Critérios de desempate")
                Spacer(Modifier.height(6.dp))
                Text("QUEM PASSA NA FRENTE", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 22.sp, color = AppColors.ink)
                Spacer(Modifier.height(6.dp))
                Text("Os 2 primeiros de cada grupo avançam para as quartas.", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
                Spacer(Modifier.height(10.dp))
                groupTieBreakers().forEachIndexed { index, criterion ->
                    Row(Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier.width(20.dp).height(20.dp).background(AppColors.ticketOrangeBg, androidx.compose.foundation.shape.CircleShape)
                                .border(BorderStroke(1.dp, AppColors.antiqueGold), androidx.compose.foundation.shape.CircleShape),
                            contentAlignment = Alignment.Center,
                        ) { Text("${index + 1}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, color = AppColors.kicker) }
                        Spacer(Modifier.width(8.dp))
                        Text(criterion, fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
                    }
                }
            }
        }
    }
}
