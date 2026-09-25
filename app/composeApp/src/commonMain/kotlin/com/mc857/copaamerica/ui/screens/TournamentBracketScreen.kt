package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import com.mc857.copaamerica.domain.logic.koStageLabel
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.BracketTree
import com.mc857.copaamerica.ui.components.KnockoutSummary
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar

/** Mirrors TournamentBracket, App.tsx:1588-1639. */
@Composable
fun TournamentBracketScreen(
    team: TeamData,
    bracket: DrawnBracket,
    onAdvance: () -> Unit,
    onSummary: () -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    val ko = bracket.ko
    val inSf = koIndexOf(ko.sf, team.name) >= 0
    val stageTies = if (inSf) ko.sf else ko.qf
    val userIndex = koIndexOf(stageTies, team.name)
    val userTie = stageTies.getOrNull(userIndex)
    val rival = userTie?.let { if (it.home?.name == team.name) it.away else it.home }
    val stageLabel = koStageLabel(ko, team.name)

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Chaveamento", sub = "$stageLabel · Modo clássico", onBack = onBack, onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(16.dp)) {
            Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stageLabel.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.ink)
                Text("${(if (inSf) ko.sf.size else ko.qf.size)} jogos", fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
            }
            BracketTree(qf = ko.qf, sf = ko.sf, final = ko.final, highlightName = team.name)
            androidx.compose.foundation.layout.Spacer(Modifier.height(8.dp))
            KnockoutSummary(third = ko.third, final = ko.final)
            if (rival != null && ko.final.winner == null) {
                Column(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 12.dp)
                        .hardShadow(color = AppColors.antiqueGold.copy(alpha = 0.35f), cornerRadius = 16.dp)
                        .background(AppColors.cream, RoundedCornerShape(16.dp))
                        .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp))
                        .padding(16.dp),
                ) {
                    com.mc857.copaamerica.ui.components.KickerLabel("Seu confronto")
                    androidx.compose.foundation.layout.Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(team.flag, fontSize = 20.sp)
                            Text(" ${team.name}", fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                        }
                        Text("VS", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 18.sp, color = AppColors.antiqueGold)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("${rival.name} ", fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                            Text(rival.flag, fontSize = 20.sp)
                        }
                    }
                }
            }
        }
        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(
                text = if (ko.final.winner != null) "Ver resumo da fase" else "Avançar para a partida",
                onClick = if (ko.final.winner != null) onSummary else onAdvance,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}
