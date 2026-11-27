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
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.logic.Outcome
import com.mc857.copaamerica.domain.logic.outcomeFor
import com.mc857.copaamerica.domain.logic.scoreFor
import com.mc857.copaamerica.domain.model.CardType
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.MatchResult
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.FlagImage
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideFlagName
import com.mc857.copaamerica.ui.components.WideInkHeaderCard
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader

private enum class EventKind(val icon: String, val label: String) {
    GOAL("⚽", "GOL"),
    YELLOW("🟨", "AMARELO"),
    RED("🟥", "VERMELHO"),
    INJURY("+", "LESÃO"),
}

/** One line of the timeline; [score] is the running score after a goal. */
private data class TimelineEvent(
    val minute: Int,
    val kind: EventKind,
    val squadId: String,
    val player: String,
    val detail: String = "",
    val score: String = "",
)

/** Goals, cards and injuries in match order, with the score from [squadId]'s side. */
private fun timeline(result: MatchResult, squadId: String): List<TimelineEvent> {
    var own = 0
    var other = 0
    val goals = result.goals.sortedBy { it.minute }.map { goal ->
        if (goal.squad == squadId) own++ else other++
        TimelineEvent(goal.minute, EventKind.GOAL, goal.squad, goal.player.name ?: "Jogador", score = "$own – $other")
    }
    val cards = result.cards.map {
        val kind = if (it.type == CardType.RED) EventKind.RED else EventKind.YELLOW
        TimelineEvent(it.minute, kind, it.squad, it.player.name ?: "Jogador")
    }
    val injuries = result.injuries.map {
        val games = if (it.matchesOut == 1) "1 jogo fora" else "${it.matchesOut} jogos fora"
        TimelineEvent(it.minute, EventKind.INJURY, it.squad, it.player.name ?: "Jogador", detail = games)
    }
    return (goals + cards + injuries).sortedBy { it.minute }
}

/** The played match exactly as the server reported it. */
@Composable
fun MatchResultScreen(
    team: Squad,
    match: Match,
    next: NextStep,
    onNext: () -> Unit,
    onReset: () -> Unit,
) {
    val result = match.result ?: return
    val opponent = match.opponentOf(team.id)
    val resultLabel = match.stage.label
    val (teamGoals, opponentGoals) = match.scoreFor(team.id)
    val outcome = match.outcomeFor(team.id)
    val didWin = outcome == Outcome.WIN
    val didLose = outcome == Outcome.LOSS
    val penaltiesText = result.penalties?.let {
        val teamIsHome = match.home.id == team.id
        val own = if (teamIsHome) it.home else it.away
        val other = if (teamIsHome) it.away else it.home
        "PÊNALTIS $own – $other"
    }
    val events = timeline(result, team.id)

    val bannerColor = if (didWin) AppColors.ticketGreen else if (didLose) AppColors.lossRed else AppColors.antiqueGold
    val bannerBg = if (didWin) AppColors.winGreenBg else if (didLose) AppColors.lossRedBg else AppColors.ticketOrangeBg
    val resultWord = if (didWin) "Vitória" else if (didLose) "Derrota" else "Empate"
    val continueText = when (next) {
        is NextStep.Play -> when (next.match.stage) {
            Stage.GROUP -> "Voltar para a fase de grupos"
            Stage.THIRD_PLACE -> "Continuar"
            else -> "Ver chaveamento"
        }
        NextStep.DrawPlayoffs -> "Ver classificação final"
        NextStep.Eliminated -> if (match.stage == Stage.GROUP) "Ver classificação final" else "Continuar"
        NextStep.Finished -> "Ver resumo do torneio"
    }

    if (LocalWideLayout.current) {
        WidePage {
            WidePageHeader("FIM DE", "JOGO", kicker = "Resultado · $resultLabel")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .hardShadow(color = bannerColor.copy(alpha = 0.3f), cornerRadius = 16.dp)
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, bannerColor), RoundedCornerShape(16.dp))
                            .padding(28.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(20.dp),
                    ) {
                        Box(
                            Modifier
                                .background(bannerBg, RoundedCornerShape(50))
                                .border(BorderStroke(2.dp, bannerColor), RoundedCornerShape(50))
                                .padding(horizontal = 16.dp, vertical = 8.dp),
                        ) {
                            Text("${resultWord.uppercase()} · ${resultLabel.uppercase()}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.5.sp, color = bannerColor)
                        }
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            WideFlagName(team.flag, team.name, AppColors.antiqueGold, Modifier.weight(1f), flagSize = 64.sp)
                            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("$teamGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 96.sp, lineHeight = 96.sp, color = AppColors.ink)
                                    Text(" – ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 56.sp, color = AppColors.mutedText)
                                    Text("$opponentGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 96.sp, lineHeight = 96.sp, color = if (didLose) AppColors.lossRed else AppColors.bodyText)
                                }
                                Text(penaltiesText ?: "FIM DE JOGO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.kicker)
                            }
                            WideFlagName(opponent.flag, opponent.name, AppColors.bodyText, Modifier.weight(1f), flagSize = 64.sp)
                        }
                    }
                    RetroPrimaryButton(
                        text = continueText,
                        onClick = onNext,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                WideInkHeaderCard("Eventos da partida", "${events.size} lances", Modifier.width(440.dp)) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        if (events.isEmpty()) Text("Sem lances de destaque.", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
                        events.forEach { ev -> MatchEventRow(ev, team, opponent) }
                    }
                }
            }
        }
        return
    }

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Fim de jogo", sub = "Resultado · $resultLabel", onReset = onReset)

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
                    FlagImage(team.flag, height = 34.dp)
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = AppColors.antiqueGold, maxLines = 1)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("$teamGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 46.sp, color = AppColors.ink)
                        Text(" – ", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, color = AppColors.mutedText)
                        Text("$opponentGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 46.sp, color = if (didLose) AppColors.lossRed else AppColors.bodyText)
                    }
                    Text(penaltiesText ?: "FIM DE JOGO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.5.sp, color = AppColors.kicker)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    FlagImage(opponent.flag, height = 34.dp)
                    Text(opponent.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = AppColors.bodyText, maxLines = 1)
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
                    MatchEventRow(ev, team, opponent)
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(
                text = continueText,
                onClick = onNext,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun MatchEventRow(ev: TimelineEvent, team: Squad, opponent: Squad) {
    val isTeam = ev.squadId == team.id
    val isGoal = ev.kind == EventKind.GOAL
    val highlight = isGoal && isTeam
    val squad = if (isTeam) team else opponent
    Row(verticalAlignment = Alignment.Top) {
        Box(
            Modifier
                .size(28.dp)
                .background(if (highlight) AppColors.winGreenBg else AppColors.cream, CircleShape)
                .border(BorderStroke(2.dp, if (highlight) AppColors.ticketGreen else AppColors.paperBorder), CircleShape),
            contentAlignment = Alignment.Center,
        ) { Text(ev.kind.icon, fontSize = 13.sp, color = AppColors.lossRed) }
        Spacer(Modifier.width(10.dp))
        Column(
            Modifier
                .weight(1f)
                .background(if (highlight) AppColors.winGreenBg else if (isGoal) AppColors.cream else androidx.compose.ui.graphics.Color.Transparent, RoundedCornerShape(10.dp))
                .padding(horizontal = 10.dp, vertical = 8.dp),
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(ev.player.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                if (isGoal) {
                    Text(ev.score, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.antiqueGold)
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("${ev.minute}'", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                FlagImage(squad.flag, height = 10.dp)
                Text(
                    squad.name,
                    fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp,
                    color = if (isTeam) AppColors.ticketGreen else AppColors.mutedText,
                )
                Text(listOf(ev.kind.label, ev.detail).filter { it.isNotEmpty() }.joinToString(" · "), fontFamily = monoFontFamily(), fontSize = 10.sp, color = AppColors.mutedText)
            }
        }
    }
}
