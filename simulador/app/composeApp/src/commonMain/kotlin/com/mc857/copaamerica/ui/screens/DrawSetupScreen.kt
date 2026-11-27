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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.model.Draw
import com.mc857.copaamerica.domain.model.Squad
import com.mc857.copaamerica.domain.model.TournamentMode
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.FlagImage
import com.mc857.copaamerica.ui.components.KickerLabel
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideCaption
import com.mc857.copaamerica.ui.components.WideGrid
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader
import com.mc857.copaamerica.ui.components.WideTicketCard
import kotlinx.coroutines.delay

/** The board the draw fills: 4 groups of 4, or Modo Rápido's 4 quarter-finals. */
private class DrawBoard(
    val slotsPerCard: Int,
    val drawLabel: String,
    val caption: String,
    val kicker: String,
    val rules: String,
    val cardTitle: (Int) -> String,
) {
    val slotCount get() = CARD_COUNT * slotsPerCard
}

private const val CARD_COUNT = 4

private const val KNOCKOUT_RULES = "Empate no mata-mata vai direto para os pênaltis."

private fun boardFor(mode: TournamentMode) = when (mode) {
    TournamentMode.FULL -> DrawBoard(
        slotsPerCard = 4,
        drawLabel = "Sortear grupos",
        caption = "4 grupos de 4 seleções",
        kicker = "Fase de grupos",
        rules = "As duas melhores de cada grupo avançam para as quartas. $KNOCKOUT_RULES",
        cardTitle = { "GRUPO ${'A' + it}" },
    )
    TournamentMode.FAST -> DrawBoard(
        slotsPerCard = 2,
        drawLabel = "Sortear confrontos",
        caption = "8 seleções direto nas quartas",
        kicker = "Mata-mata direto",
        rules = "Cada uma das 4 seleções mais fortes enfrenta uma das 4 mais fracas. $KNOCKOUT_RULES",
        cardTitle = { "QUARTAS ${it + 1}" },
    )
}

/**
 * The groups (or, in Modo Rápido, the quarter-finals) come from GET
 * /{sessionId}/draw; this screen only reveals them one team at a time. [onBack]
 * is null once drawn: the call-up can no longer change.
 */
@Composable
fun DrawSetupScreen(
    team: Squad,
    draw: Draw?,
    mode: TournamentMode = TournamentMode.FULL,
    onDraw: () -> Unit,
    onNext: () -> Unit,
    onBack: (() -> Unit)?,
    onReset: () -> Unit,
) {
    var revealedCount by remember(draw) { mutableStateOf(0) }
    var infoOpen by remember { mutableStateOf(false) }
    val board = boardFor(mode)
    val slotCount = board.slotCount

    androidx.compose.runtime.LaunchedEffect(draw) {
        if (draw != null) {
            repeat(slotCount) { i ->
                delay(if (i == 0) 180L else 90L)
                revealedCount = i + 1
            }
        }
    }

    val drawButton: @Composable (Modifier) -> Unit = { modifier ->
        when {
            draw == null -> RetroPrimaryButton(text = board.drawLabel, onClick = onDraw, modifier = modifier)
            revealedCount < slotCount -> RetroPrimaryButton(text = "Sorteando…", enabled = false, onClick = {}, modifier = modifier)
            else -> RetroPrimaryButton(text = "Ir para escalação", onClick = onNext, modifier = modifier)
        }
    }

    if (LocalWideLayout.current) {
        WidePage {
            WidePageHeader("SORTEIO DO", "TORNEIO", back = onBack?.let { "Elenco" to it })
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Column(Modifier.width(320.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    WideTicketCard {
                        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                            KickerLabel("Sua seleção")
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                                FlagImage(team.flag, height = 40.dp)
                                Column {
                                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 30.sp, lineHeight = 30.sp, color = AppColors.ink)
                                    Text(draw?.let { userDrawLabel(it, team) }?.takeIf { revealedCount == slotCount } ?: "AGUARDANDO SORTEIO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                                }
                            }
                            drawButton(Modifier.fillMaxWidth())
                        }
                    }
                    // The phone layout hides this behind the "i" button.
                    Column(Modifier.padding(horizontal = 4.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        WideCaption(board.caption)
                        Text(
                            board.rules,
                            fontFamily = monoFontFamily(), fontSize = 13.sp, lineHeight = 20.sp, color = AppColors.bodyText,
                        )
                    }
                }
                WideGrid((0 until CARD_COUNT).toList(), minCellWidth = 300.dp, modifier = Modifier.weight(1f), gap = 16.dp) { groupIndex ->
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .hardShadow(cornerRadius = 16.dp)
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp))
                            .clip(RoundedCornerShape(16.dp)),
                    ) {
                        Box(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 14.dp, vertical = 10.dp)) {
                            Text(board.cardTitle(groupIndex), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, letterSpacing = 1.5.sp, color = AppColors.kicker)
                        }
                        Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            repeat(board.slotsPerCard) { slot ->
                                val item = drawnSlot(draw, board, groupIndex, slot, revealedCount)
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .background(if (item?.id == team.id) AppColors.ticketOrangeBg else AppColors.paper, RoundedCornerShape(8.dp))
                                        .padding(horizontal = 10.dp, vertical = 10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                ) {
                                    if (item != null) FlagImage(item.flag, height = 18.dp) else Text("🎱", fontSize = 20.sp)
                                    Text(
                                        item?.name?.uppercase() ?: "A SORTEAR",
                                        fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 16.sp,
                                        color = if (item != null) AppColors.ink else AppColors.mutedText, maxLines = 1,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
        return
    }

    Box(Modifier.fillMaxSize()) {
    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Sorteio do torneio", sub = mode.label, onBack = onBack, onReset = onReset)
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
                    FlagImage(team.flag, height = 24.dp)
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
                // Fixed height: a lazy grid cannot measure itself inside the scrolling column.
                modifier = Modifier.fillMaxWidth().height(if (board.slotsPerCard == 4) 420.dp else 220.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(CARD_COUNT) { groupIndex ->
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .hardShadow(cornerRadius = 16.dp)
                            .background(AppColors.cream, RoundedCornerShape(16.dp))
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(16.dp)),
                    ) {
                        Box(Modifier.fillMaxWidth().background(AppColors.ticketOrangeBg).padding(horizontal = 10.dp, vertical = 6.dp)) {
                            Text(board.cardTitle(groupIndex), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                        }
                        Column(Modifier.padding(6.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            repeat(board.slotsPerCard) { slot ->
                                val item = drawnSlot(draw, board, groupIndex, slot, revealedCount)
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .background(if (item?.id == team.id) AppColors.ticketOrangeBg else AppColors.paper, RoundedCornerShape(6.dp))
                                        .padding(horizontal = 6.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    if (item != null) FlagImage(item.flag, height = 12.dp) else Text("🎱", fontSize = 14.sp)
                                    Spacer(Modifier.width(6.dp))
                                    Text(
                                        item?.name ?: "A sortear",
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
            drawButton(Modifier.fillMaxWidth())
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
                KickerLabel(board.kicker)
                Spacer(Modifier.height(6.dp))
                Text(board.caption.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 22.sp, color = AppColors.ink)
                Spacer(Modifier.height(6.dp))
                Text(
                    board.rules,
                    fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
                )
                Spacer(Modifier.height(16.dp))
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(AppColors.ink, RoundedCornerShape(16.dp))
                        .clip(RoundedCornerShape(16.dp))
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

/**
 * Squad in slot [slot] of card [cardIndex] (a group, or a quarter-final in Modo
 * Rápido), or null while the draw has not revealed it.
 */
private fun drawnSlot(draw: Draw?, board: DrawBoard, cardIndex: Int, slot: Int, revealedCount: Int): Squad? {
    if (draw == null || cardIndex * board.slotsPerCard + slot >= revealedCount) return null
    if (draw.groups.isNotEmpty()) return draw.groups.getOrNull(cardIndex)?.squads?.getOrNull(slot)
    val match = draw.matches.sortedBy { it.id }.getOrNull(cardIndex) ?: return null
    return if (slot == 0) match.home else match.away
}

/** Where the draw put the user's squad: "GRUPO B", or its quarter-final rival in Modo Rápido. */
private fun userDrawLabel(draw: Draw, team: Squad): String? {
    if (draw.groups.isNotEmpty()) {
        return draw.groups.firstOrNull { group -> group.squads.any { it.id == team.id } }?.let { "GRUPO ${it.name}" }
    }
    val rival = draw.matches.firstOrNull { it.involves(team.id) }?.opponentOf(team.id) ?: return null
    return "QUARTAS CONTRA ${rival.name.uppercase()}"
}
