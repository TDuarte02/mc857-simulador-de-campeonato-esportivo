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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.Outcome
import com.mc857.copaamerica.domain.logic.outcomeFor
import com.mc857.copaamerica.domain.logic.scoreFor
import com.mc857.copaamerica.domain.logic.scoreLabel
import com.mc857.copaamerica.domain.logic.stageReached
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Match
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.platform.shareText
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.BracketTree
import com.mc857.copaamerica.ui.components.FlagImage
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RetroSecondaryButton
import com.mc857.copaamerica.ui.components.TieCard
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideCaption
import com.mc857.copaamerica.ui.components.WideGrid
import com.mc857.copaamerica.ui.components.WideInkHeaderCard
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader
import com.mc857.copaamerica.ui.components.WideSectionRule

/** "Grupos" for any group game, otherwise the stage's name. */
private fun Match.shortLabel(): String = when (stage) {
    Stage.GROUP -> "Grupos"
    Stage.QUARTER_FINAL -> "Quartas"
    Stage.SEMI_FINAL -> "Semifinal"
    Stage.THIRD_PLACE -> "3º lugar"
    Stage.FINAL -> "Final"
}

/** The finished cup, from GET /{sessionId}/history: champion, podium and the user's campaign. */
@Composable
fun PhaseOverviewScreen(
    team: Squad,
    history: History,
    onReset: () -> Unit,
) {
    val podiumSquads = history.podium ?: return
    val champion = podiumSquads.champion
    val bracket = history.bracket

    val rounds = listOf(
        "Quartas de final" to bracket.quarterFinals,
        "Semifinais" to bracket.semiFinals,
        "Disputa de 3º lugar" to listOfNotNull(bracket.thirdPlace),
        "Final" to listOfNotNull(bracket.final),
    )

    val podium = listOf(
        Triple("🥇", "Campeão", podiumSquads.champion),
        Triple("🥈", "Vice-campeão", podiumSquads.runnerUp),
        Triple("🥉", "3º lugar", podiumSquads.third),
    )

    val campaign = history.userPath
    val record = Triple(
        campaign.count { it.outcomeFor(team.id) == Outcome.WIN },
        campaign.count { it.outcomeFor(team.id) == Outcome.DRAW },
        campaign.count { it.outcomeFor(team.id) == Outcome.LOSS },
    )

    fun shareResult() {
        val lines = buildList {
            add("🏆 Copa América Histórica")
            podium.forEach { (medal, _, side) -> add("$medal ${side.name}") }
            add("")
            add("Minha campanha com ${team.name} (${record.first}V ${record.second}E ${record.third}D):")
            campaign.forEach { add("• ${it.shortLabel()} — ${it.scoreLabel(team.id)} ${it.opponentOf(team.id).name}") }
        }
        shareText("Copa América Histórica", lines.joinToString("\n"))
    }

    if (LocalWideLayout.current) {
        val reached = stageReached(history)
        val goalsFor = campaign.sumOf { it.scoreFor(team.id).first }
        val goalsAgainst = campaign.sumOf { it.scoreFor(team.id).second }
        WidePage {
            WidePageHeader("RESUMO DO", "TORNEIO", kicker = "Torneio encerrado · Modo clássico")

            Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                    Column(
                        Modifier
                            .weight(1f)
                            .fillMaxHeight()
                            .hardShadow(color = AppColors.antiqueGold.copy(alpha = 0.35f), cornerRadius = 16.dp)
                            .background(
                                Brush.linearGradient(listOf(AppColors.antiqueGold.copy(alpha = 0.18f), AppColors.antiqueGold.copy(alpha = 0.05f))),
                                RoundedCornerShape(16.dp),
                            )
                            .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp))
                            .padding(28.dp),
                        verticalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                            Text("🏆", fontSize = 72.sp)
                            Column {
                                Text("CAMPEÃO DA COPA AMÉRICA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.kicker)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    FlagImage(champion.flag, height = 40.dp)
                                    Text(" ${champion.name.uppercase()}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 56.sp, lineHeight = 56.sp, color = AppColors.antiqueGold)
                                }
                                Text("MELHOR SELEÇÃO HISTÓRICA", fontFamily = displayFontFamily(), fontSize = 15.sp, color = AppColors.bodyText)
                            }
                        }
                        Spacer(Modifier.height(20.dp))
                        RetroSecondaryButton("Compartilhar resultado", onClick = ::shareResult, modifier = Modifier.width(260.dp))
                    }
                WideInkHeaderCard("Pódio", "Final", Modifier.width(420.dp).fillMaxHeight()) {
                    PodiumBlocks(podium, Modifier.fillMaxWidth().weight(1f).padding(horizontal = 20.dp).padding(top = 20.dp))
                }
            }

            if (campaign.isNotEmpty()) {
                Spacer(Modifier.height(32.dp))
                WideSectionRule("Sua campanha · ${team.name}")
                Spacer(Modifier.height(16.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    CampaignStat("Fase alcançada", reached, AppColors.antiqueGold, Modifier.weight(1.4f))
                    CampaignStat("Vitórias", "${record.first}", AppColors.ticketGreen, Modifier.weight(1f))
                    CampaignStat("Empates", "${record.second}", AppColors.kicker, Modifier.weight(1f))
                    CampaignStat("Derrotas", "${record.third}", AppColors.lossRed, Modifier.weight(1f))
                    CampaignStat("Gols pró", "$goalsFor", AppColors.ink, Modifier.weight(1f))
                    CampaignStat("Gols contra", "$goalsAgainst", AppColors.ink, Modifier.weight(1f))
                    CampaignStat("Saldo", (goalsFor - goalsAgainst).let { if (it > 0) "+$it" else if (it < 0) "−${-it}" else "0" }, AppColors.ink, Modifier.weight(1f))
                }
                Spacer(Modifier.height(16.dp))
                WideGrid(campaign, minCellWidth = 200.dp, gap = 12.dp) { game -> CampaignGameCard(game, team.id) }
            }

            Spacer(Modifier.height(32.dp))
            WideSectionRule("Mata-mata")
            Spacer(Modifier.height(16.dp))
            Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Column(
                    Modifier
                        .weight(1f)
                        .hardShadow(cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp))
                        .padding(20.dp),
                ) {
                    BracketTree(bracket, userSquadId = team.id, large = true)
                }
                // As wide as a large TieCard, so the card ends on the page's right edge.
                Column(Modifier.width(200.dp).fillMaxHeight(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    WideCaption("Disputa de 3º lugar")
                    TieCard(bracket.thirdPlace, "3º lugar", userSquadId = team.id, large = true)
                    // Pushes the button down to line up with the bottom of the bracket.
                    Spacer(Modifier.weight(1f))
                    RetroPrimaryButton("Novo torneio", onClick = onReset, modifier = Modifier.fillMaxWidth())
                }
            }
        }
        return
    }

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Resumo do torneio", sub = "Torneio encerrado · Modo clássico", onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(20.dp)) {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 20.dp)
                        .hardShadow(color = AppColors.antiqueGold.copy(alpha = 0.35f), cornerRadius = 16.dp)
                        .background(
                            Brush.linearGradient(listOf(AppColors.antiqueGold.copy(alpha = 0.18f), AppColors.antiqueGold.copy(alpha = 0.05f))),
                            RoundedCornerShape(16.dp),
                        )
                        .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp))
                        .padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("🏆", fontSize = 40.sp)
                    Text("CAMPEÃO DA COPA AMÉRICA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        FlagImage(champion.flag, height = 26.dp)
                        Text(" ${champion.name.uppercase()}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, color = AppColors.antiqueGold)
                    }
                    Text("MELHOR SELEÇÃO HISTÓRICA", fontFamily = displayFontFamily(), fontSize = 12.sp, color = AppColors.bodyText)
                    Spacer(Modifier.height(12.dp))
                    RetroSecondaryButton("Compartilhar resultado", onClick = ::shareResult, modifier = Modifier.fillMaxWidth())
                }

            KickerLabel("Pódio", modifier = Modifier.padding(bottom = 8.dp))
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
                    .hardShadow(cornerRadius = 16.dp)
                    .background(AppColors.cream, RoundedCornerShape(16.dp))
                    .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
            ) {
                PodiumRows(podium)
            }

            if (campaign.isNotEmpty()) {
                Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    KickerLabel("Sua campanha")
                    Text("${record.first}V ${record.second}E ${record.third}D", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.bodyText)
                }
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 20.dp)
                        .hardShadow(cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
                ) {
                    CampaignRows(campaign, team.id)
                }
            }

            rounds.forEach { (label, ties) ->
                KickerLabel(label, modifier = Modifier.padding(bottom = 8.dp))
                Column(Modifier.fillMaxWidth().padding(bottom = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    ties.forEach { tie -> ResultRow(tie, team.id) }
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton("Novo torneio", onClick = onReset, modifier = Modifier.fillMaxWidth())
        }
    }
}

@Composable
private fun ResultRow(tie: Match, userSquadId: String) {
    val isUserTie = tie.involves(userSquadId)
    val result = tie.result
    Column(
        Modifier
            .fillMaxWidth()
            .background(if (isUserTie) AppColors.ticketOrangeBg else AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, if (isUserTie) AppColors.antiqueGold else AppColors.paperBorder), RoundedCornerShape(12.dp)),
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            SideLabel(tie.home, result?.winner == tie.home.id, Modifier.weight(1f), alignStart = true)
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("${result?.homeGoals ?: "-"} – ${result?.awayGoals ?: "-"}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ink)
                result?.penalties?.let {
                    Text("${it.home}–${it.away} pên.", fontFamily = monoFontFamily(), fontSize = 9.sp, color = AppColors.mutedText)
                }
            }
            SideLabel(tie.away, result?.winner == tie.away.id, Modifier.weight(1f), alignStart = false)
        }
    }
}

@Composable
private fun SideLabel(side: Squad, isWinner: Boolean, modifier: Modifier, alignStart: Boolean) {
    Row(
        modifier,
        horizontalArrangement = if (alignStart) Arrangement.Start else Arrangement.End,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (alignStart) {
            FlagImage(side.flag, height = 14.dp)
            Spacer(Modifier.width(4.dp))
        }
        Text(side.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = if (isWinner) AppColors.ink else AppColors.mutedText, maxLines = 1)
        if (!alignStart) {
            Spacer(Modifier.width(4.dp))
            FlagImage(side.flag, height = 14.dp)
        }
    }
}

@Composable
private fun PodiumRows(podium: List<Triple<String, String, Squad>>) {
    podium.forEachIndexed { i, (medal, label, side) ->
        if (i != 0) Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(medal, fontSize = 18.sp)
            Spacer(Modifier.width(8.dp))
            FlagImage(side.flag, height = 14.dp)
            Spacer(Modifier.width(8.dp))
            Text(side.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink, modifier = Modifier.weight(1f), maxLines = 1)
            Text(label.uppercase(), fontFamily = monoFontFamily(), fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText)
        }
    }
}

private val Outcome.letter get() = when (this) { Outcome.WIN -> "V"; Outcome.DRAW -> "E"; Outcome.LOSS -> "D" }

private val Outcome.color get() = when (this) {
    Outcome.WIN -> AppColors.ticketGreen
    Outcome.DRAW -> AppColors.mutedText
    Outcome.LOSS -> AppColors.lossRed
}

@Composable
private fun CampaignRows(campaign: List<Match>, userSquadId: String) {
    campaign.forEachIndexed { i, game ->
        val outcome = game.outcomeFor(userSquadId)
        val rival = game.opponentOf(userSquadId)
        if (i != 0) Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(outcome.letter, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = outcome.color)
            Spacer(Modifier.width(8.dp))
            Text(game.shortLabel().uppercase(), fontFamily = monoFontFamily(), fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText, modifier = Modifier.width(64.dp))
            FlagImage(rival.flag, height = 12.dp)
            Spacer(Modifier.width(6.dp))
            Text(
                rival.name, fontFamily = displayFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp,
                color = AppColors.bodyText, modifier = Modifier.weight(1f), maxLines = 1,
            )
            Text(game.scoreLabel(userSquadId), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.ink)
        }
    }
}

/** 2nd · 1st · 3rd blocks of increasing/decreasing height, like a real podium. */
@Composable
private fun PodiumBlocks(podium: List<Triple<String, String, Squad>>, modifier: Modifier) {
    // podium is ordered champion, runner-up, third; draw it 2nd · 1st · 3rd.
    val order = listOf(1, 0, 2).mapNotNull { podium.getOrNull(it)?.let { entry -> it to entry } }
    Row(modifier, verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        order.forEach { (place, entry) ->
            val (_, label, side) = entry
            val (blockHeight, color) = when (place) {
                0 -> 120.dp to AppColors.antiqueGold
                1 -> 88.dp to Color(0xFFAEB4BD)
                else -> 64.dp to Color(0xFFB4693C)
            }
            Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                FlagImage(side.flag, height = 34.dp)
                Text(side.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 16.sp, color = AppColors.ink, maxLines = 1)
                Text(label.uppercase(), fontFamily = monoFontFamily(), fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText, maxLines = 1)
                Spacer(Modifier.height(8.dp))
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(blockHeight)
                        .background(color, RoundedCornerShape(topStart = 10.dp, topEnd = 10.dp))
                        .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(topStart = 10.dp, topEnd = 10.dp)),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("${place + 1}º", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 32.sp, color = AppColors.cream)
                }
            }
        }
    }
}

@Composable
private fun CampaignStat(label: String, value: String, color: Color, modifier: Modifier) {
    Column(
        modifier
            .background(AppColors.cream, RoundedCornerShape(14.dp))
            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(14.dp))
            .padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        Text(label.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText, maxLines = 1)
        Text(value.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, color = color, maxLines = 1)
    }
}

@Composable
private fun CampaignGameCard(game: Match, userSquadId: String) {
    val outcome = game.outcomeFor(userSquadId)
    val rival = game.opponentOf(userSquadId)
    val color = if (outcome == Outcome.DRAW) AppColors.kicker else outcome.color
    val bg = when (outcome) {
        Outcome.WIN -> AppColors.winGreenBg
        Outcome.DRAW -> AppColors.ticketOrangeBg
        Outcome.LOSS -> AppColors.lossRedBg
    }
    Row(
        Modifier
            .fillMaxWidth()
            .background(bg, RoundedCornerShape(14.dp))
            .border(BorderStroke(2.dp, color), RoundedCornerShape(14.dp))
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        FlagImage(rival.flag, height = 24.dp)
        Column(Modifier.weight(1f)) {
            Text(game.shortLabel().uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText)
            Text(rival.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 16.sp, color = AppColors.ink, maxLines = 1)
        }
        Column(horizontalAlignment = Alignment.End) {
            val (own, other) = game.scoreFor(userSquadId)
            Text("$own–$other", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 24.sp, color = AppColors.ink)
            val verdict = when (outcome) { Outcome.WIN -> "VITÓRIA"; Outcome.DRAW -> "EMPATE"; Outcome.LOSS -> "DERROTA" }
            val shootout = if (game.result?.penalties != null) " NOS PÊNALTIS" else ""
            Text(verdict + shootout, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = color)
        }
    }
}
