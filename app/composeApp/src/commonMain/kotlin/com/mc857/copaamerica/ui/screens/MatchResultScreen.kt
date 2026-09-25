package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.buildMatchEvents
import com.mc857.copaamerica.domain.logic.groupMatchScore
import com.mc857.copaamerica.domain.model.GroupMatch
import com.mc857.copaamerica.domain.model.MatchEventType
import com.mc857.copaamerica.domain.model.MatchSide
import com.mc857.copaamerica.domain.model.Phase
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar

/** Mirrors MatchResult, App.tsx:1848-1966. */
@Composable
fun MatchResultScreen(
    team: TeamData,
    opponent: PoolTeam,
    phase: Phase,
    groupMatch: GroupMatch?,
    squad: List<Player>,
    onNext: () -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    val isGroupMatch = phase == Phase.GROUP && groupMatch != null
    val isSemiFinal = phase == Phase.SF
    val isThirdPlace = phase == Phase.THIRD
    val resultLabel = when {
        isGroupMatch -> "Fase de grupos"
        isSemiFinal -> "Semifinal"
        isThirdPlace -> "Disputa de 3º lugar"
        else -> "Quartas de final"
    }
    val groupScore = groupMatch?.let { groupMatchScore(it) } ?: (2 to 1)
    val teamIsHome = groupMatch?.home?.name == team.name
    val teamGoals = if (isGroupMatch) (if (teamIsHome) groupScore.first else groupScore.second) else if (isSemiFinal) 1 else 2
    val opponentGoals = if (isGroupMatch) (if (teamIsHome) groupScore.second else groupScore.first) else if (isSemiFinal) 2 else 1
    val didWin = teamGoals > opponentGoals
    val didLose = teamGoals < opponentGoals

    val stats = when {
        didWin -> listOf("14–8" to "CHUTES", "62%–38%" to "POSSE", "2.4–0.9" to "xG")
        didLose -> listOf("8–14" to "CHUTES", "38%–62%" to "POSSE", "0.9–2.4" to "xG")
        else -> listOf("11–11" to "CHUTES", "50%–50%" to "POSSE", "1.4–1.4" to "xG")
    }
    val events = buildMatchEvents(teamGoals, opponentGoals, squad)

    val bannerColor = if (didWin) AppColors.ticketGreen else if (didLose) AppColors.lossRed else AppColors.antiqueGold
    val bannerBg = if (didWin) AppColors.winGreenBg else if (didLose) AppColors.lossRedBg else AppColors.ticketOrangeBg
    val resultWord = if (didWin) "Vitória" else if (didLose) "Derrota" else "Empate"

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Fim de jogo", sub = "Resultado · $resultLabel", onBack = onBack, onReset = onReset)

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Box(
                    Modifier
                        .background(bannerBg, RoundedCornerShape(50))
                        .border(BorderStroke(2.dp, bannerColor), RoundedCornerShape(50))
                        .padding(horizontal = 14.dp, vertical = 6.dp),
                ) {
                    Text(
                        "${resultWord.uppercase()} · ${resultLabel.uppercase()}",
                        fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = bannerColor,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(team.flag, fontSize = 34.sp)
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = AppColors.antiqueGold, maxLines = 1)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("$teamGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 46.sp, color = AppColors.ink)
                        Text(" – ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, color = AppColors.mutedText)
                        Text("$opponentGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 46.sp, color = if (didLose) AppColors.lossRed else AppColors.bodyText)
                    }
                    Text("FIM DE JOGO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.5.sp, color = AppColors.kicker)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(opponent.flag, fontSize = 34.sp)
                    Text(opponent.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = AppColors.bodyText, maxLines = 1)
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(
                Modifier.fillMaxWidth().padding(top = 12.dp).border(BorderStroke(0.dp, AppColors.rowBorder)),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                stats.forEach { (value, label) ->
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(label, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText)
                        Text(value, fontFamily = displayFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.ink)
                    }
                }
            }
        }

        Column(Modifier.weight(1f).retroPaper().padding(20.dp)) {
            Text(
                "EVENTOS DA PARTIDA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp,
                color = AppColors.kicker, modifier = Modifier.padding(bottom = 12.dp),
            )
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(events) { ev ->
                    val isTeam = ev.side == MatchSide.TEAM
                    val icon = if (ev.type == MatchEventType.GOAL) "⚽" else "🟨"
                    Row(verticalAlignment = Alignment.Top) {
                        Box(
                            Modifier
                                .size(28.dp)
                                .background(if (ev.type == MatchEventType.GOAL && isTeam) AppColors.winGreenBg else AppColors.cream, CircleShape)
                                .border(BorderStroke(2.dp, if (ev.type == MatchEventType.GOAL && isTeam) AppColors.ticketGreen else AppColors.paperBorder), CircleShape),
                            contentAlignment = Alignment.Center,
                        ) { Text(icon, fontSize = 13.sp) }
                        Spacer(Modifier.width(10.dp))
                        Column(
                            Modifier
                                .weight(1f)
                                .background(if (ev.type == MatchEventType.GOAL && isTeam) AppColors.winGreenBg else if (ev.type == MatchEventType.GOAL) AppColors.cream else androidx.compose.ui.graphics.Color.Transparent, RoundedCornerShape(10.dp))
                                .padding(horizontal = 10.dp, vertical = 8.dp),
                        ) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(ev.player.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                                if (ev.type == MatchEventType.GOAL) {
                                    Text(ev.score, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.antiqueGold)
                                }
                            }
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("${ev.minute}'", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                                Text(
                                    if (isTeam) "${team.flag} ${team.name}" else "${opponent.flag} ${opponent.name}",
                                    fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp,
                                    color = if (isTeam) AppColors.ticketGreen else AppColors.mutedText,
                                )
                                Text(if (ev.type == MatchEventType.GOAL) "GOL" else "AMARELO", fontFamily = monoFontFamily(), fontSize = 10.sp, color = AppColors.mutedText)
                            }
                        }
                    }
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(
                text = if (isGroupMatch) "Voltar para a fase de grupos" else "Ver resumo da fase",
                onClick = onNext,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}
