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
import com.mc857.copaamerica.domain.logic.CampaignGame
import com.mc857.copaamerica.domain.logic.koIndexOf
import com.mc857.copaamerica.domain.logic.tieLoser
import com.mc857.copaamerica.domain.logic.userCampaign
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.KnockoutTie
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.platform.shareText
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.BracketTree
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

/** Mirrors PhaseOverview, App.tsx:2049-2210. */
@Composable
fun PhaseOverviewScreen(
    team: TeamData,
    bracket: DrawnBracket,
    ctaLabel: String?,
    onNext: (() -> Unit)?,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    val ko = bracket.ko
    val champion = ko.final.winner
    val over = champion != null

    val rounds = listOf(
        "Quartas de final" to ko.qf,
        "Semifinais" to ko.sf,
        "Disputa de 3º lugar" to listOf(ko.third),
        "Final" to listOf(ko.final),
    ).filter { (_, ties) -> ties.any { it.winner != null } }

    val podium = listOfNotNull(
        champion?.let { Triple("🥇", "Campeão", it) },
        tieLoser(ko.final)?.let { Triple("🥈", "Vice-campeão", it) },
        ko.third.winner?.let { Triple("🥉", "3º lugar", it) },
    )

    val campaign = userCampaign(bracket, team.name)
    val record = campaign.fold(Triple(0, 0, 0)) { (w, d, l), g ->
        if (g.drew) Triple(w, d + 1, l) else if (g.won) Triple(w + 1, d, l) else Triple(w, d, l + 1)
    }

    fun shareResult() {
        val champ = champion ?: return
        val lines = buildList {
            add("🏆 Copa América Histórica")
            add("🥇 ${champ.flag} ${champ.name}")
            tieLoser(ko.final)?.let { add("🥈 ${it.flag} ${it.name}") }
            ko.third.winner?.let { add("🥉 ${it.flag} ${it.name}") }
            add("")
            add("Minha campanha com ${team.flag} ${team.name} (${record.first}V ${record.second}E ${record.third}D):")
            campaign.forEach { add("• ${it.label} — ${it.goals}–${it.rivalGoals} ${it.rival?.flag ?: ""} ${it.rival?.name ?: ""}".trim()) }
        }
        shareText("Copa América Histórica", lines.joinToString("\n"))
    }

    val sub = when {
        over -> "Torneio encerrado"
        ko.sf.all { it.winner != null } -> "Semifinais concluídas"
        else -> "Quartas de final concluídas"
    }

    if (LocalWideLayout.current) {
        val reached = when {
            champion?.name == team.name -> "Campeã"
            tieLoser(ko.final)?.name == team.name -> "Vice"
            ko.third.winner?.name == team.name -> "3º lugar"
            tieLoser(ko.third)?.name == team.name -> "4º lugar"
            koIndexOf(ko.sf, team.name) >= 0 -> "Semifinal"
            koIndexOf(ko.qf, team.name) >= 0 -> "Quartas"
            else -> "Grupos"
        }
        val goalsFor = campaign.sumOf { it.goals }
        val goalsAgainst = campaign.sumOf { it.rivalGoals }
        WidePage {
            WidePageHeader(
                if (over) "RESUMO DO" else "RESUMO DA", if (over) "TORNEIO" else "FASE",
                back = "Voltar" to onBack, kicker = "$sub · Modo clássico",
            )

            Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                if (champion != null) {
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
                                    Text(champion.flag, fontSize = 40.sp)
                                    Text(" ${champion.name.uppercase()}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 56.sp, lineHeight = 56.sp, color = AppColors.antiqueGold)
                                }
                                Text("MELHOR SELEÇÃO HISTÓRICA", fontFamily = displayFontFamily(), fontSize = 15.sp, color = AppColors.bodyText)
                            }
                        }
                        Spacer(Modifier.height(20.dp))
                        RetroSecondaryButton("Compartilhar resultado", onClick = ::shareResult, modifier = Modifier.width(260.dp))
                    }
                } else {
                    Text(
                        "Os resultados do mata-mata aparecem aqui conforme as fases forem disputadas.",
                        fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.bodyText, modifier = Modifier.weight(1f),
                    )
                }
                WideInkHeaderCard("Pódio", if (over) "Final" else "Parcial", Modifier.width(420.dp).fillMaxHeight()) {
                    if (podium.isEmpty()) {
                        Text(
                            "Definido ao fim do mata-mata.", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
                            modifier = Modifier.padding(16.dp),
                        )
                    } else {
                        PodiumBlocks(podium, Modifier.fillMaxWidth().weight(1f).padding(horizontal = 20.dp).padding(top = 20.dp))
                    }
                }
            }

            if (campaign.isNotEmpty()) {
                Spacer(Modifier.height(32.dp))
                WideSectionRule("Sua campanha · ${team.flag} ${team.name}")
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
                WideGrid(campaign, minCellWidth = 200.dp, gap = 12.dp) { game -> CampaignGameCard(game) }
            }

            if (rounds.isNotEmpty()) {
                Spacer(Modifier.height(32.dp))
                WideSectionRule("Mata-mata")
                Spacer(Modifier.height(16.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                    Column(
                        Modifier
                            .weight(1f)
                            .hardShadow(cornerRadius = 16.dp)
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp))
                            .padding(20.dp),
                    ) {
                        BracketTree(qf = ko.qf, sf = ko.sf, final = ko.final, highlightName = team.name, large = true)
                    }
                    if (ko.third.winner != null) {
                        Column(Modifier.width(240.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            WideCaption("Disputa de 3º lugar")
                            TieCard(ko.third, "3º lugar", highlightName = team.name, large = true)
                        }
                    }
                }
            }

            Spacer(Modifier.height(32.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.End)) {
                if (ctaLabel != null && onNext != null) {
                    RetroSecondaryButton("Novo torneio", onClick = onReset, modifier = Modifier.width(260.dp))
                    RetroPrimaryButton(ctaLabel, onClick = onNext, modifier = Modifier.width(300.dp))
                } else {
                    RetroPrimaryButton("Novo torneio", onClick = onReset, modifier = Modifier.width(300.dp))
                }
            }
        }
        return
    }

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Resumo da fase", sub = "$sub · Modo clássico", onBack = onBack, onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(20.dp)) {
            if (champion != null) {
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
                        Text(champion.flag, fontSize = 26.sp)
                        Text(" ${champion.name.uppercase()}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, color = AppColors.antiqueGold)
                    }
                    Text("MELHOR SELEÇÃO HISTÓRICA", fontFamily = displayFontFamily(), fontSize = 12.sp, color = AppColors.bodyText)
                    Spacer(Modifier.height(12.dp))
                    RetroSecondaryButton("Compartilhar resultado", onClick = ::shareResult, modifier = Modifier.fillMaxWidth())
                }
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
                    CampaignRows(campaign)
                }
            }

            rounds.forEach { (label, ties) ->
                KickerLabel(label, modifier = Modifier.padding(bottom = 8.dp))
                Column(Modifier.fillMaxWidth().padding(bottom = 20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    ties.filter { it.winner != null }.forEach { tie -> ResultRow(tie, team.name) }
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (ctaLabel != null && onNext != null) {
                RetroPrimaryButton(ctaLabel, onClick = onNext, modifier = Modifier.fillMaxWidth())
                RetroSecondaryButton("Novo torneio", onClick = onReset, modifier = Modifier.fillMaxWidth())
            } else {
                RetroPrimaryButton("Novo torneio", onClick = onReset, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}

@Composable
private fun ResultRow(tie: KnockoutTie, highlightName: String) {
    val isUserTie = tie.home?.name == highlightName || tie.away?.name == highlightName
    Column(
        Modifier
            .fillMaxWidth()
            .background(if (isUserTie) AppColors.ticketOrangeBg else AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, if (isUserTie) AppColors.antiqueGold else AppColors.paperBorder), RoundedCornerShape(12.dp)),
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            SideLabel(tie.home, tie.winner, Modifier.weight(1f), TextAlignStart = true)
            Text("${tie.homeGoals ?: "-"} – ${tie.awayGoals ?: "-"}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ink)
            SideLabel(tie.away, tie.winner, Modifier.weight(1f), TextAlignStart = false)
        }
    }
}

@Composable
private fun SideLabel(side: com.mc857.copaamerica.domain.model.PoolTeam?, winner: com.mc857.copaamerica.domain.model.PoolTeam?, modifier: Modifier, TextAlignStart: Boolean) {
    val isWinner = winner != null && winner.name == side?.name
    val color = if (isWinner) AppColors.ink else AppColors.mutedText
    Row(
        modifier,
        horizontalArrangement = if (TextAlignStart) Arrangement.Start else Arrangement.End,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (TextAlignStart) {
            Text(side?.flag ?: "🎱", fontSize = 15.sp)
            Spacer(Modifier.width(4.dp))
        }
        Text(side?.name?.uppercase() ?: "A DEFINIR", fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = color, maxLines = 1)
        if (!TextAlignStart) {
            Spacer(Modifier.width(4.dp))
            Text(side?.flag ?: "🎱", fontSize = 15.sp)
        }
    }
}

@Composable
private fun PodiumRows(podium: List<Triple<String, String, PoolTeam>>) {
    podium.forEachIndexed { i, (medal, label, side) ->
        if (i != 0) Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(medal, fontSize = 18.sp)
            Spacer(Modifier.width(8.dp))
            Text(side.flag, fontSize = 16.sp)
            Spacer(Modifier.width(8.dp))
            Text(side.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink, modifier = Modifier.weight(1f), maxLines = 1)
            Text(label.uppercase(), fontFamily = monoFontFamily(), fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText)
        }
    }
}

@Composable
private fun CampaignRows(campaign: List<CampaignGame>) {
    campaign.forEachIndexed { i, game ->
        if (i != 0) Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(
                if (game.drew) "E" else if (game.won) "V" else "D",
                fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp,
                color = if (game.drew) AppColors.mutedText else if (game.won) AppColors.ticketGreen else AppColors.lossRed,
            )
            Spacer(Modifier.width(8.dp))
            Text(game.label.uppercase(), fontFamily = monoFontFamily(), fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText, modifier = Modifier.width(64.dp))
            Text(
                "${game.rival?.flag ?: ""} ${game.rival?.name ?: "A definir"}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp,
                color = AppColors.bodyText, modifier = Modifier.weight(1f), maxLines = 1,
            )
            Text("${game.goals}–${game.rivalGoals}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.ink)
        }
    }
}

/** 2nd · 1st · 3rd blocks of increasing/decreasing height, like a real podium. */
@Composable
private fun PodiumBlocks(podium: List<Triple<String, String, PoolTeam>>, modifier: Modifier) {
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
                Text(side.flag, fontSize = 36.sp)
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
private fun CampaignGameCard(game: CampaignGame) {
    val color = if (game.drew) AppColors.kicker else if (game.won) AppColors.ticketGreen else AppColors.lossRed
    val bg = if (game.drew) AppColors.ticketOrangeBg else if (game.won) AppColors.winGreenBg else AppColors.lossRedBg
    Row(
        Modifier
            .fillMaxWidth()
            .background(bg, RoundedCornerShape(14.dp))
            .border(BorderStroke(2.dp, color), RoundedCornerShape(14.dp))
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(game.rival?.flag ?: "🎱", fontSize = 28.sp)
        Column(Modifier.weight(1f)) {
            Text(game.label.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.mutedText)
            Text(game.rival?.name?.uppercase() ?: "A DEFINIR", fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 16.sp, color = AppColors.ink, maxLines = 1)
        }
        Column(horizontalAlignment = Alignment.End) {
            Text("${game.goals}–${game.rivalGoals}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 24.sp, color = AppColors.ink)
            Text(if (game.drew) "EMPATE" else if (game.won) "VITÓRIA" else "DERROTA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = color)
        }
    }
}

