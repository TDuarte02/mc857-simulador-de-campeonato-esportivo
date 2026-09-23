@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.domain.model.TournamentFormat
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar
import kotlinx.coroutines.delay

private enum class DrawState { IDLE, DRAWING, DONE }

/** Mirrors DrawSetup (mode==='normal' branch), App.tsx:1279-1421. */
@Composable
fun DrawSetupScreen(
    team: TeamData,
    teams: List<TeamData>,
    onNext: (List<PoolTeam>) -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    val rivalPool = remember(team) { teams.filter { it.name != team.name }.take(TournamentFormat.CLASSIC.teamCount - 1).map { PoolTeam(it.name, it.flag) } }
    var state by remember { mutableStateOf(DrawState.IDLE) }
    var shuffled by remember { mutableStateOf(listOf<PoolTeam>()) }
    var revealedCount by remember { mutableStateOf(0) }
    var infoOpen by remember { mutableStateOf(false) }

    androidx.compose.runtime.LaunchedEffect(state) {
        if (state == DrawState.DRAWING) {
            shuffled.indices.forEach { i ->
                delay(if (i == 0) 180L else 90L)
                revealedCount = i + 1
            }
            state = DrawState.DONE
        }
    }

    Box(Modifier.fillMaxSize()) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Sorteio do torneio", sub = "Modo Clássico", onBack = onBack, onReset = onReset)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(horizontal = 20.dp).padding(vertical = 16.dp)) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .hardShadow(cornerRadius = 16.dp)
                    .background(AppColors.cream, RoundedCornerShape(16.dp))
                    .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(16.dp))
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.size(48.dp).background(AppColors.card2, RoundedCornerShape(12.dp)), contentAlignment = Alignment.Center) {
                    Text(team.flag, fontSize = 22.sp)
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    KickerLabel("Sua seleção")
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 20.sp, color = AppColors.ink)
                }
            }
            Spacer(Modifier.height(16.dp))

            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                modifier = Modifier.fillMaxWidth().height(420.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(4) { groupIndex ->
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .hardShadow(cornerRadius = 16.dp)
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
                    ) {
                        Box(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 10.dp, vertical = 6.dp)) {
                            Text("GRUPO ${('A' + groupIndex)}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                        }
                        Column(Modifier.padding(6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            repeat(4) { slot ->
                                val isHead = groupIndex == 0 && slot == 0
                                val globalIndex = groupIndex * 4 + slot - 1
                                val item = if (isHead) PoolTeam(team.name, team.flag) else shuffled.getOrNull(globalIndex)
                                val visible = isHead || (item != null && globalIndex < revealedCount)
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .background(if (isHead) AppColors.ticketOrangeBg else AppColors.paper, RoundedCornerShape(6.dp))
                                        .padding(horizontal = 6.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    Text(if (visible) (item?.flag ?: "🎱") else "🎱", fontSize = 14.sp)
                                    Spacer(Modifier.width(6.dp))
                                    Text(
                                        if (visible) (item?.name ?: "") else "A sortear",
                                        fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 11.sp, color = AppColors.ink,
                                        maxLines = 1,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            when (state) {
                DrawState.IDLE -> RetroPrimaryButton(
                    text = "Sortear grupos",
                    onClick = {
                        shuffled = rivalPool.shuffled()
                        revealedCount = 0
                        state = DrawState.DRAWING
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
                DrawState.DRAWING -> RetroPrimaryButton(text = "Sorteando…", enabled = false, onClick = {}, modifier = Modifier.fillMaxWidth())
                DrawState.DONE -> RetroPrimaryButton(
                    text = "Ir para escalação",
                    onClick = { onNext(shuffled) },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }

    Box(Modifier.fillMaxSize().padding(20.dp), contentAlignment = Alignment.BottomEnd) {
        Box(Modifier.padding(bottom = 96.dp)) {
            CircleFab(onClick = { infoOpen = true }, modifier = Modifier.size(36.dp)) {
                Text("i", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 15.sp, color = AppColors.cream)
            }
        }
    }
    } // Box

    if (infoOpen) {
        ModalBottomSheet(onDismissRequest = { infoOpen = false }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 24.dp)) {
                KickerLabel("Fase de grupos")
                Spacer(Modifier.height(6.dp))
                Text("4 GRUPOS DE 4 SELEÇÕES", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 22.sp, color = AppColors.ink)
                Spacer(Modifier.height(6.dp))
                Text(
                    "As duas melhores de cada grupo avançam para as quartas. Empate no mata-mata vai direto para os pênaltis.",
                    fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
                )
                Spacer(Modifier.height(16.dp))
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(AppColors.ink, RoundedCornerShape(16.dp))
                        .clickable { infoOpen = false }
                        .padding(vertical = 12.dp),
                    horizontalArrangement = Arrangement.Center,
                ) {
                    Text("ENTENDI", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 13.sp, letterSpacing = 1.sp, color = AppColors.paper)
                }
            }
        }
    }
}
