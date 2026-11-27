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
import androidx.compose.foundation.layout.width
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
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.domain.model.TournamentMode
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
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideFlagName
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader
import com.mc857.copaamerica.ui.components.WideTicketCard

/** The knockout tree from GET /{sessionId}/history, with the user's next tie below it. */
@Composable
fun TournamentBracketScreen(
    team: Squad,
    history: History,
    next: NextStep,
    onAdvance: () -> Unit,
    onReset: () -> Unit,
    mode: TournamentMode = TournamentMode.FULL,
) {
    val upcoming = (next as? NextStep.Play)?.match ?: return
    val rival = upcoming.opponentOf(team.id)
    val stageLabel = upcoming.stage.label
    val ties = when (upcoming.stage) {
        Stage.QUARTER_FINAL -> history.bracket.quarterFinals.size
        Stage.SEMI_FINAL -> history.bracket.semiFinals.size
        else -> 1
    }
    val tiesLabel = if (ties == 1) "1 jogo" else "$ties jogos"

    if (LocalWideLayout.current) {
        WidePage {
            WidePageHeader("CHAVEAMENTO DO", "MATA-MATA", trailing = {
                Text(
                    "${stageLabel.uppercase()} · ${tiesLabel.uppercase()}",
                    fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.sp, color = AppColors.bodyText,
                )
            })
            Column(
                Modifier
                    .fillMaxWidth()
                    .hardShadow(cornerRadius = 16.dp)
                    .background(AppColors.cream, RoundedCornerShape(16.dp))
                    .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp))
                    .padding(24.dp),
            ) {
                BracketTree(history.bracket, userSquadId = team.id, large = true)
            }
            Spacer(Modifier.height(24.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                WideTicketCard(Modifier.width(400.dp)) {
                    Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                        Text("SEU CONFRONTO · ${stageLabel.uppercase()}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 2.sp, color = AppColors.ticketOrangeText)
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            WideFlagName(team.flag, team.name, AppColors.antiqueGold, Modifier.weight(1f))
                            Text("×", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.mutedText)
                            WideFlagName(rival.flag, rival.name, AppColors.ink, Modifier.weight(1f))
                        }
                        RetroPrimaryButton("Avançar para a partida", onClick = onAdvance, modifier = Modifier.fillMaxWidth())
                    }
                }
            }
        }
        return
    }

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Chaveamento", sub = "$stageLabel · ${mode.label}", onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(16.dp)) {
            Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stageLabel.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.ink)
                Text(tiesLabel, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
            }
            BracketTree(history.bracket, userSquadId = team.id)
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp)
                    .hardShadow(color = AppColors.antiqueGold.copy(alpha = 0.35f), cornerRadius = 16.dp)
                    .background(AppColors.cream, RoundedCornerShape(16.dp))
                    .border(BorderStroke(2.dp, AppColors.antiqueGold), RoundedCornerShape(16.dp))
                    .padding(16.dp),
            ) {
                KickerLabel("Seu confronto")
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        FlagImage(team.flag, height = 18.dp)
                        Text(team.name, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                    }
                    Text("VS", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 18.sp, color = AppColors.antiqueGold)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(rival.name, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink)
                        FlagImage(rival.flag, height = 18.dp)
                    }
                }
            }
        }
        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton("Avançar para a partida", onClick = onAdvance, modifier = Modifier.fillMaxWidth())
        }
    }
}
