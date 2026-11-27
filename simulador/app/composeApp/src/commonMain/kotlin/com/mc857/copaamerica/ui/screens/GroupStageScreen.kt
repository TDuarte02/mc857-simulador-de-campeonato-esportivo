@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.logic.scoreFor
import com.mc857.copaamerica.domain.logic.userGroupMatches
import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.GroupTable
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.SessionPhase
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.bodyFontFamily
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.FlagImage
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideCaption
import com.mc857.copaamerica.ui.components.WideFlagName
import com.mc857.copaamerica.ui.components.WideGrid
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WideTicketCard
import com.mc857.copaamerica.ui.components.WideTitle

private const val FORMAT_LABEL = "Modo clássico"

/** How the server orders a group (simulador/server: compute_standings). */
private val TIE_BREAKERS = listOf(
    "Saldo de gols",
    "Gols marcados",
    "Menos cartões vermelhos",
    "Menos cartões amarelos",
    "Ordem alfabética",
)

/** Group standings and the user's fixtures, from GET /{sessionId}/draw and /history. */
@Composable
fun GroupStageScreen(
    draw: Draw,
    history: History,
    next: NextStep,
    onPlayNext: () -> Unit,
    onDrawPlayoffs: () -> Unit,
    onSimulateRest: () -> Unit,
    onReset: () -> Unit,
) {
    var tiebreakOpen by remember { mutableStateOf(false) }
    val team = draw.userSquad
    val userGroup = history.groups.firstOrNull { g -> g.standings.any { it.squad.id == team.id } }
    val userMatches = userGroupMatches(draw, history)
    val nextMatch = (next as? NextStep.Play)?.match
    val groupsComplete = history.phase != SessionPhase.GROUP_STAGE
    val userEliminated = next == NextStep.Eliminated
    val nextStepLabel = when {
        nextMatch != null -> "Jogar próxima partida"
        userEliminated -> "Simular o resto da copa"
        else -> "Sortear quartas de final"
    }
    val onNextStep = when {
        nextMatch != null -> onPlayNext
        userEliminated -> onSimulateRest
        else -> onDrawPlayoffs
    }

    if (LocalWideLayout.current) {
        WideGroupStage(
            history = history, team = team, userGroup = userGroup, userMatches = userMatches, nextMatch = nextMatch,
            groupsComplete = groupsComplete, userEliminated = userEliminated, nextStepLabel = nextStepLabel,
            onNextStep = onNextStep,
        )
        return
    }

    Box(Modifier.fillMaxSize()) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Fase de grupos", sub = "$FORMAT_LABEL · ${history.groups.size} grupos de 4", onReset = onReset)
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
                        Text("${userMatches.count { it.played }}/3 partidas", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                    }
                    userMatches.forEachIndexed { index, match ->
                        Row(
                            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text("J${index + 1}", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                            FixtureLabel(match, fontSize = 13, modifier = Modifier.weight(1f))
                            when {
                                match.played -> Text("${match.result?.homeGoals}–${match.result?.awayGoals}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ticketGreen)
                                match.id == nextMatch?.id -> Text("PRÓXIMO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.antiqueGold)
                                else -> Text("PENDENTE", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.kicker)
                            }
                        }
                    }
                }
            }

            KickerLabel(if (groupsComplete) "Classificação final" else "Classificação provisória", modifier = Modifier.padding(bottom = 8.dp))

            history.groups.forEach { group ->
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
                            Text("${userMatches.count { it.played }}/3 jogos seus", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                        }
                    }
                    group.standings.forEachIndexed { index, standing ->
                        val qualified = groupsComplete && index < 2
                        val isUser = standing.squad.id == team.id
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
                            FlagImage(standing.squad.flag, height = 14.dp)
                            Spacer(Modifier.width(6.dp))
                            Text(
                                standing.squad.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp,
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
            RetroPrimaryButton(nextStepLabel, onClick = onNextStep, modifier = Modifier.fillMaxWidth())
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
                TIE_BREAKERS.forEachIndexed { index, criterion ->
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

@Composable
private fun WideGroupStage(
    history: History,
    team: Squad,
    userGroup: GroupTable?,
    userMatches: List<Match>,
    nextMatch: Match?,
    groupsComplete: Boolean,
    userEliminated: Boolean,
    nextStepLabel: String,
    onNextStep: () -> Unit,
) {
    val played = userMatches.count { it.played }
    WidePage {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom) {
            Column(Modifier.weight(1f)) {
                KickerLabel("$FORMAT_LABEL · ${history.groups.size} grupos de 4")
                Spacer(Modifier.height(6.dp))
                WideTitle("FASE DE", "GRUPOS")
            }
            Text(
                if (groupsComplete) "Classificação final · os 2 primeiros avançam às quartas" else "Rodada ${played + 1} de 3 · os 2 primeiros avançam às quartas",
                fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
            )
        }
        Spacer(Modifier.height(24.dp))

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
            Column(Modifier.width(340.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                when {
                    groupsComplete -> WideTicketCard(bar = if (userEliminated) AppColors.lossRed else AppColors.ticketGreen) {
                        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                            Text("FASE DE GRUPOS ENCERRADA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = if (userEliminated) AppColors.lossRed else AppColors.ticketGreenText)
                            Text(
                                if (userEliminated) "${team.name} ficou fora das quartas. Veja como o mata-mata terminou." else "Os 2 primeiros de cada grupo seguem para as quartas de final.",
                                fontFamily = bodyFontFamily(), fontWeight = FontWeight.Medium, fontSize = 15.sp, lineHeight = 22.sp, color = AppColors.bodyText,
                            )
                            RetroPrimaryButton(nextStepLabel, onClick = onNextStep, modifier = Modifier.fillMaxWidth())
                        }
                    }
                    nextMatch != null -> WideTicketCard {
                        val rival = nextMatch.opponentOf(team.id)
                        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                            Text("PRÓXIMA PARTIDA · RODADA ${played + 1}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.ticketOrangeText)
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                WideFlagName(team.flag, team.name, AppColors.antiqueGold, Modifier.weight(1f))
                                Text("×", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.mutedText)
                                WideFlagName(rival.flag, rival.name, AppColors.ink, Modifier.weight(1f))
                            }
                            RetroPrimaryButton("Escalar e jogar", onClick = onNextStep, modifier = Modifier.fillMaxWidth())
                        }
                    }
                }

                if (!groupsComplete && userGroup != null) {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp))
                            .clip(RoundedCornerShape(16.dp)),
                    ) {
                        Row(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 18.dp, vertical = 12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("SEU GRUPO · GRUPO ${userGroup.name}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.5.sp, color = AppColors.kicker)
                            Text("$played/3", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.bodyText)
                        }
                        userMatches.forEachIndexed { index, match ->
                            Row(
                                Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 12.dp),
                                verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                            ) {
                                Text("J${index + 1}", fontFamily = monoFontFamily(), fontSize = 12.sp, color = AppColors.mutedText)
                                FixtureLabel(match, fontSize = 16, modifier = Modifier.weight(1f))
                                when {
                                    match.played -> {
                                        val (own, rival) = match.scoreFor(team.id)
                                        val color = when {
                                            own > rival -> AppColors.ticketGreen
                                            own < rival -> AppColors.lossRed
                                            else -> AppColors.kicker
                                        }
                                        Text("${match.result?.homeGoals}–${match.result?.awayGoals}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = color)
                                    }
                                    match.id == nextMatch?.id -> Text("PRÓXIMO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.ticketOrangeText)
                                    else -> Text("PENDENTE", fontFamily = monoFontFamily(), fontSize = 12.sp, color = AppColors.mutedText)
                                }
                            }
                        }
                    }
                }

                // The phone layout hides these behind the "i" button; there is room for them here.
                Column(Modifier.fillMaxWidth().padding(horizontal = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    WideCaption("Critérios de desempate")
                    TIE_BREAKERS.forEachIndexed { index, criterion ->
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("${index + 1}.", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.kicker)
                            Text(criterion, fontFamily = monoFontFamily(), fontSize = 12.sp, color = AppColors.bodyText)
                        }
                    }
                }
            }

            WideGrid(history.groups, minCellWidth = 340.dp, modifier = Modifier.weight(1f), gap = 20.dp) { group ->
                WideGroupTable(group, team, isUserGroup = group.name == userGroup?.name, groupsComplete = groupsComplete, userPlayed = played)
            }
        }
    }
}

@Composable
private fun WideGroupTable(group: GroupTable, team: Squad, isUserGroup: Boolean, groupsComplete: Boolean, userPlayed: Int) {
    Column(
        Modifier
            .fillMaxWidth()
            .hardShadow(color = if (isUserGroup) AppColors.antiqueGold.copy(alpha = 0.3f) else AppColors.ink.copy(alpha = 0.08f), cornerRadius = 16.dp)
            .background(AppColors.cream, RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, if (isUserGroup) AppColors.antiqueGold else AppColors.paperBorder), RoundedCornerShape(16.dp))
            .clip(RoundedCornerShape(16.dp)),
    ) {
        Row(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 16.dp, vertical = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("GRUPO ${group.name}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.5.sp, color = AppColors.kicker)
            if (isUserGroup) Text("SEU GRUPO · $userPlayed/3", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker)
        }
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("#", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText, modifier = Modifier.width(22.dp))
            Text("SELEÇÃO", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText, modifier = Modifier.weight(1f))
            listOf("J", "V", "E", "D", "SG", "PTS").forEach { TableCell(it, color = AppColors.mutedText) }
        }
        group.standings.forEachIndexed { index, standing ->
            // Top two are the qualification places; "classificado/eliminado" only once the group is over.
            val inQualifyingPlace = index < 2
            val isUser = standing.squad.id == team.id
            val rowBg = when {
                isUser && groupsComplete -> if (inQualifyingPlace) AppColors.winGreenBg else AppColors.lossRedBg
                isUser -> AppColors.ticketOrangeBg
                else -> Color.Transparent
            }
            Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
            Row(Modifier.fillMaxWidth().background(rowBg).height(IntrinsicSize.Min), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.width(4.dp).fillMaxHeight().background(if (inQualifyingPlace) AppColors.ticketGreen else Color.Transparent))
                Row(Modifier.weight(1f).padding(start = 12.dp, end = 16.dp, top = 9.dp, bottom = 9.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("${index + 1}", fontFamily = monoFontFamily(), fontSize = 12.sp, color = AppColors.mutedText, modifier = Modifier.width(22.dp))
                    Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FlagImage(standing.squad.flag, height = 15.dp)
                        Text(
                            standing.squad.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 15.sp,
                            color = if (isUser) AppColors.antiqueGold else AppColors.ink, maxLines = 1,
                        )
                    }
                    val goalDiff = standing.goalDifference
                    listOf(standing.played, standing.won, standing.drawn, standing.lost).forEach { TableCell("$it") }
                    TableCell(if (goalDiff > 0) "+$goalDiff" else if (goalDiff < 0) "−${-goalDiff}" else "0")
                    TableCell("${standing.points}", bold = true)
                }
            }
        }
    }
}

/** "🏳 Brasil × Argentina 🏳" on one line. */
@Composable
private fun FixtureLabel(match: Match, fontSize: Int, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        FlagImage(match.home.flag, height = fontSize.dp)
        Text(
            "${match.home.name} × ${match.away.name}",
            fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = fontSize.sp, color = AppColors.ink,
            maxLines = 1, modifier = Modifier.weight(1f, fill = false),
        )
        FlagImage(match.away.flag, height = fontSize.dp)
    }
}

@Composable
private fun TableCell(text: String, color: Color = AppColors.ink, bold: Boolean = false) {
    Text(
        text, fontFamily = monoFontFamily(), fontWeight = if (bold) FontWeight.Bold else FontWeight.Medium,
        fontSize = if (bold) 14.sp else 12.sp, color = color, textAlign = androidx.compose.ui.text.style.TextAlign.End,
        modifier = Modifier.width(if (text == "PTS" || bold) 34.dp else 28.dp),
    )
}

