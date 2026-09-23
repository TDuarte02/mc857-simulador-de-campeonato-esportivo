package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.koIndexOf
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RetroSecondaryButton
import com.mc857.copaamerica.ui.components.TopBar

/** Mirrors Elimination, App.tsx:2213-2351. */
@Composable
fun EliminationScreen(
    team: TeamData,
    bracket: DrawnBracket,
    onPlayThird: () -> Unit,
    onSimulateRest: () -> Unit,
    onSeeResults: () -> Unit,
    onBack: () -> Unit,
) {
    val ko = bracket.ko
    val sfTie = ko.sf.getOrNull(koIndexOf(ko.sf, team.name))
    val teamIsHome = sfTie?.home?.name == team.name
    val teamGoals = (if (teamIsHome) sfTie?.homeGoals else sfTie?.awayGoals) ?: 1
    val rivalGoals = (if (teamIsHome) sfTie?.awayGoals else sfTie?.homeGoals) ?: 2
    val rival = if (teamIsHome) sfTie?.away else sfTie?.home
    val champion = ko.final.winner

    val champTies = (ko.sf + ko.final).filter { it.winner?.name == champion?.name }
    val champGoals = champTies.sumOf { if (it.home?.name == champion?.name) it.homeGoals ?: 0 else it.awayGoals ?: 0 }
    val champAgainst = champTies.sumOf { if (it.home?.name == champion?.name) it.awayGoals ?: 0 else it.homeGoals ?: 0 }
    val awards = listOf(
        "Artilheiro" to "$champGoals ${if (champGoals == 1) "gol" else "gols"}",
        "Melhor goleiro" to "$champAgainst ${if (champAgainst == 1) "sofrido" else "sofridos"}",
        "Bola de ouro" to (champion?.name ?: "—"),
    )

    val tournamentOver = ko.third.winner != null
    val inThird = ko.third.home?.name == team.name || ko.third.away?.name == team.name

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Eliminado", sub = if (tournamentOver) "Semifinal · Torneio encerrado" else "Semifinal · Disputa de 3º lugar", onBack = onBack)

        Column(Modifier.background(AppColors.lossRedBg).padding(20.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(team.flag, fontSize = 30.sp)
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, color = AppColors.mutedText, maxLines = 1)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("$teamGoals – $rivalGoals", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 34.sp, color = AppColors.ink)
                    Text("ELIMINADA NA SEMI", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.lossRed)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(rival?.flag ?: "🎱", fontSize = 30.sp)
                    Text(rival?.name?.uppercase() ?: "—", fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, color = AppColors.ink, maxLines = 1)
                }
            }
        }

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(20.dp)) {
            if (champion != null) {
                KickerLabel("Prêmios do campeão", modifier = Modifier.padding(bottom = 8.dp))
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp)
                        .hardShadow(cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
                ) {
                    awards.forEachIndexed { i, (label, value) ->
                        Row(
                            Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(label.uppercase(), fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                            Text(value, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 14.sp, color = AppColors.ink)
                        }
                        if (i != awards.lastIndex) androidx.compose.foundation.layout.Box(Modifier.fillMaxWidth().height(1.dp).background(AppColors.rowBorder))
                    }
                }
            }
            if (!tournamentOver) {
                Text(
                    if (inThird) "Você ainda disputa o 3º lugar. Jogue essa partida ou deixe o app simular o resultado." else "A disputa de 3º lugar segue em aberto.",
                    fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
                )
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            when {
                !tournamentOver && inThird -> {
                    RetroPrimaryButton("Jogar a disputa de 3º lugar", onClick = onPlayThird, modifier = Modifier.fillMaxWidth())
                    RetroSecondaryButton("Simular e ver resultados", onClick = { onSimulateRest(); onSeeResults() }, modifier = Modifier.fillMaxWidth())
                }
                else -> RetroPrimaryButton("Ver resumo da fase", onClick = onSeeResults, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}
