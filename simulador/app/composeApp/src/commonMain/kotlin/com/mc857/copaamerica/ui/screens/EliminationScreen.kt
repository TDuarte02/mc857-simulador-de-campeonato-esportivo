package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.logic.scoreLabel
import com.mc857.copaamerica.domain.model.History
import com.mc857.copaamerica.domain.model.Squad
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
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader

/**
 * Shown after a knockout defeat. A beaten semi-finalist still plays for third
 * place; otherwise the server simulates the rest of the cup.
 */
@Composable
fun EliminationScreen(
    team: Squad,
    history: History,
    next: NextStep,
    onPlayThird: () -> Unit,
    onSimulateRest: () -> Unit,
    onReset: () -> Unit,
) {
    val defeat = history.userPath.lastOrNull() ?: return
    val rival = defeat.opponentOf(team.id)
    val score = defeat.scoreLabel(team.id)
    val stageLabel = defeat.stage.label
    val thirdPlace = (next as? NextStep.Play)?.match
    val explanation = if (thirdPlace != null) {
        "Você ainda disputa o 3º lugar contra ${thirdPlace.opponentOf(team.id).name}."
    } else {
        "Sua seleção está fora. O servidor simula o restante da copa."
    }
    val buttonText = if (thirdPlace != null) "Jogar a disputa de 3º lugar" else "Simular o resto da copa"
    val onButton = if (thirdPlace != null) onPlayThird else onSimulateRest

    if (LocalWideLayout.current) {
        WidePage {
            WidePageHeader("ELIMINADO NAS", stageLabel.uppercase(), kicker = "Fim da linha")
            Column(
                Modifier
                    .fillMaxWidth()
                    .hardShadow(color = AppColors.lossRed.copy(alpha = 0.25f), cornerRadius = 16.dp)
                    .background(AppColors.lossRedBg, RoundedCornerShape(16.dp))
                    .border(BorderStroke(2.dp, AppColors.lossRed), RoundedCornerShape(16.dp))
                    .padding(28.dp),
            ) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    WideFlagName(team.flag, team.name, AppColors.mutedText, Modifier.weight(1f), flagSize = 56.sp)
                    Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(score, fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 56.sp, lineHeight = 60.sp, color = AppColors.ink)
                        Text(stageLabel.uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.5.sp, color = AppColors.lossRed)
                    }
                    WideFlagName(rival.flag, rival.name, AppColors.ink, Modifier.weight(1f), flagSize = 56.sp)
                }
            }
            Column(Modifier.padding(top = 20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text(explanation, fontFamily = monoFontFamily(), fontSize = 14.sp, lineHeight = 21.sp, color = AppColors.bodyText)
                RetroPrimaryButton(buttonText, onClick = onButton, modifier = Modifier.fillMaxWidth())
            }
        }
        return
    }

    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Eliminado", sub = stageLabel, onReset = onReset)

        Column(Modifier.background(AppColors.lossRedBg).padding(20.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    FlagImage(team.flag, height = 30.dp)
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, color = AppColors.mutedText, maxLines = 1)
                }
                Column(Modifier.weight(1.4f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(score, fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.ink)
                    Text("DERROTA", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 10.sp, letterSpacing = 1.sp, color = AppColors.lossRed)
                }
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    FlagImage(rival.flag, height = 30.dp)
                    Text(rival.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, color = AppColors.ink, maxLines = 1)
                }
            }
        }

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(20.dp)) {
            Text(explanation, fontFamily = monoFontFamily(), fontSize = 13.sp, lineHeight = 19.sp, color = AppColors.bodyText)
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(buttonText, onClick = onButton, modifier = Modifier.fillMaxWidth())
        }
    }
}
