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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.tieLoser
import com.mc857.copaamerica.domain.logic.userCampaign
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.KnockoutTie
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.platform.shareText
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RetroSecondaryButton
import com.mc857.copaamerica.ui.components.TopBar

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

    val sub = when {
        over -> "Torneio encerrado"
        ko.sf.all { it.winner != null } -> "Semifinais concluídas"
        else -> "Quartas de final concluídas"
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
                    val shareLines = buildList {
                        add("🏆 Copa América Histórica")
                        add("🥇 ${champion.flag} ${champion.name}")
                        tieLoser(ko.final)?.let { add("🥈 ${it.flag} ${it.name}") }
                        ko.third.winner?.let { add("🥉 ${it.flag} ${it.name}") }
                        add("")
                        add("Minha campanha com ${team.flag} ${team.name} (${record.first}V ${record.second}E ${record.third}D):")
                        campaign.forEach { add("• ${it.label} — ${it.goals}–${it.rivalGoals} ${it.rival?.flag ?: ""} ${it.rival?.name ?: ""}".trim()) }
                    }
                    RetroSecondaryButton("Compartilhar resultado", onClick = { shareText("Copa América Histórica", shareLines.joinToString("\n")) }, modifier = Modifier.fillMaxWidth())
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
