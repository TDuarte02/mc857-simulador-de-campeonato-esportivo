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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.data.FIELD_FORMATIONS
import com.mc857.copaamerica.domain.logic.defaultSquad
import com.mc857.copaamerica.domain.logic.remapLineup
import com.mc857.copaamerica.domain.logic.secondaryRole
import com.mc857.copaamerica.domain.model.CardStatus
import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.Phase
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.SlotCfg
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.DieFiveIcon
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RetroSecondaryButton
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideCaption
import com.mc857.copaamerica.ui.components.WideChip
import com.mc857.copaamerica.ui.components.WideFlagName
import com.mc857.copaamerica.ui.components.WideInkHeaderCard
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WidePageHeader
import com.mc857.copaamerica.ui.components.WideTicketCard

/** Mirrors PreMatchLineup, App.tsx:1642-1810. */
@Composable
fun PreMatchLineupScreen(
    team: TeamData,
    opponent: PoolTeam,
    squad: List<Player>,
    pool: List<Player>,
    phase: Phase,
    cards: Map<Int, CardStatus>,
    lineup: List<Player?>,
    formKey: FormKey,
    onLineupChange: (List<Player?>) -> Unit,
    onFormKeyChange: (FormKey) -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    val effectiveSquad = squad.ifEmpty { defaultSquad(pool) }
    val slots = FIELD_FORMATIONS.getValue(formKey)
    val sized = List(slots.size) { lineup.getOrNull(it) }
    var activeSlot by remember { mutableStateOf<Int?>(null) }

    val suspendedIds = effectiveSquad.filter { cards[it.id] == CardStatus.RED }.map { it.id }.toSet()
    val yellowIds = effectiveSquad.filter { cards[it.id] == CardStatus.YELLOW }.map { it.id }.toSet()
    val availableSquad = effectiveSquad.filterNot { it.id in suspendedIds }
    val selectedIds = sized.filterNotNull().map { it.id }.toSet()
    val selectedCount = sized.count { it != null }

    fun changeFormation(next: FormKey) {
        onFormKeyChange(next)
        onLineupChange(remapLineup(sized, FIELD_FORMATIONS.getValue(next)))
        activeSlot = null
    }

    val eligiblePlayers = activeSlot?.let { idx ->
        val cat = slots[idx].cat
        val free = availableSquad.filter { it.pos == cat && it.id !in selectedIds }
        val suspended = effectiveSquad.filter { it.pos == cat && it.id in suspendedIds }
        (free + suspended).sortedWith(compareBy<Player> { if (it.id in suspendedIds) 1 else 0 }.thenByDescending { it.rating })
    } ?: emptyList()

    fun choosePlayer(player: Player) {
        val idx = activeSlot ?: return
        onLineupChange(sized.mapIndexed { i, current -> if (i == idx) player else current })
        activeSlot = null
    }

    fun fillRandom() {
        val used = mutableSetOf<Int>()
        val drawn = slots.map { slot ->
            val candidates = availableSquad.filter { it.pos == slot.cat && it.id !in used }
            candidates.randomOrNull()?.also { used.add(it.id) }
        }
        onLineupChange(drawn)
        activeSlot = null
    }

    val hasPreviousLineup = lineup.any { it != null }
    val confirmText = if (selectedCount == 11) "Simular partida" else "Escale ${11 - selectedCount} jogador${if (11 - selectedCount == 1) "" else "es"}"

    if (LocalWideLayout.current) {
        WidePage {
            WidePageHeader("SUA", "ESCALAÇÃO", back = "Voltar" to onBack, kicker = if (hasPreviousLineup) "Ajuste a escalação" else "Monte seus titulares")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(28.dp)) {
                Column(Modifier.width(460.dp)) {
                    LineupPitch(slots, sized, suspendedIds, yellowIds, activeSlot, onSlotClick = { activeSlot = it }, large = true)
                    Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("Clique em uma posição para escolher o jogador", fontFamily = monoFontFamily(), fontSize = 12.sp, color = AppColors.mutedText)
                        Text("$selectedCount / 11", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.ticketGreen)
                    }
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(20.dp)) {
                    WideTicketCard {
                        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                WideFlagName(team.flag, team.name, AppColors.antiqueGold, Modifier.weight(1f))
                                Text("×", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 28.sp, color = AppColors.mutedText)
                                WideFlagName(opponent.flag, opponent.name, AppColors.ink, Modifier.weight(1f))
                            }
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                WideCaption("Formação")
                                Spacer(Modifier.width(4.dp))
                                FormKey.entries.forEach { fk -> WideChip(fk.label, active = formKey == fk, onClick = { changeFormation(fk) }) }
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                RetroSecondaryButton("Sortear escalação", onClick = ::fillRandom, modifier = Modifier.weight(1f))
                                RetroPrimaryButton(confirmText, enabled = selectedCount == 11, onClick = onNext, modifier = Modifier.weight(1f))
                            }
                        }
                    }
                    WideInkHeaderCard(
                        "Escolha o jogador",
                        activeSlot?.let { "Posição ${slots[it].label}" } ?: "",
                    ) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            when {
                                activeSlot == null -> Text(
                                    "Selecione uma posição no campo para ver os jogadores disponíveis.",
                                    fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText,
                                )
                                eligiblePlayers.isEmpty() -> Text("Nenhum jogador disponível para esta posição.", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
                                else -> eligiblePlayers.forEach { player ->
                                    PlayerPickRow(player, suspended = player.id in suspendedIds, hasYellow = player.id in yellowIds, onChoose = { choosePlayer(player) })
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
        TopBar(title = "Escalação", sub = if (hasPreviousLineup) "Ajuste a escalação" else "Monte seus titulares", onBack = onBack, onReset = onReset)

        Column(Modifier.background(AppColors.paper).padding(horizontal = 20.dp, vertical = 12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(team.flag, fontSize = 18.sp)
                    Spacer(Modifier.width(6.dp))
                    Text(team.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 14.sp, color = AppColors.antiqueGold)
                }
                Text("VS", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 16.sp, color = AppColors.ink)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(opponent.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 14.sp, color = AppColors.bodyText)
                    Spacer(Modifier.width(6.dp))
                    Text(opponent.flag, fontSize = 18.sp)
                }
            }
            Spacer(Modifier.height(10.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                FormKey.entries.forEach { fk ->
                    val active = formKey == fk
                    Box(
                        Modifier
                            .background(if (active) AppColors.ticketOrange else AppColors.cream, RoundedCornerShape(50))
                            .border(BorderStroke(2.dp, if (active) AppColors.ink else AppColors.paperBorder), RoundedCornerShape(50))
                            .clip(RoundedCornerShape(50))
                            .clickable { changeFormation(fk) }
                            .padding(horizontal = 12.dp, vertical = 6.dp),
                    ) {
                        Text(fk.label, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = if (active) AppColors.cream else AppColors.bodyText)
                    }
                }
            }
        }

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).retroPaper().padding(16.dp)) {
            LineupPitch(slots, sized, suspendedIds, yellowIds, activeSlot = null, onSlotClick = { activeSlot = it })
            Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    if (hasPreviousLineup) "Toque para trocar quem quiser" else "Toque em uma posição para escolher",
                    fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText,
                )
                Text("$selectedCount / 11", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = AppColors.ticketGreen)
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(
                text = confirmText,
                enabled = selectedCount == 11,
                onClick = onNext,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }

    Box(Modifier.fillMaxSize().padding(20.dp), contentAlignment = Alignment.BottomEnd) {
        Box(Modifier.padding(bottom = 96.dp)) {
            CircleFab(onClick = ::fillRandom) { DieFiveIcon(color = AppColors.cream) }
        }
    }
    } // Box

    val slotIndex = activeSlot
    if (slotIndex != null) {
        ModalBottomSheet(onDismissRequest = { activeSlot = null }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 24.dp).height(420.dp)) {
                Text("ESCOLHA O JOGADOR", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                Text("Posição ${slots[slotIndex].label}", fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = 20.sp, color = AppColors.ink)
                Spacer(Modifier.height(10.dp))
                if (eligiblePlayers.isEmpty()) {
                    Text("Nenhum jogador disponível para esta posição.", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText, modifier = Modifier.padding(vertical = 24.dp))
                } else {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(eligiblePlayers, key = { it.id }) { player ->
                            PlayerPickRow(player, suspended = player.id in suspendedIds, hasYellow = player.id in yellowIds, onChoose = { choosePlayer(player) })
                        }
                    }
                }
            }
        }
    }
}

/** The pitch with one tappable circle per formation slot. [activeSlot] is outlined in gold (wide layout). */
@Composable
private fun LineupPitch(
    slots: List<SlotCfg>,
    lineup: List<Player?>,
    suspendedIds: Set<Int>,
    yellowIds: Set<Int>,
    activeSlot: Int?,
    onSlotClick: (Int) -> Unit,
    large: Boolean = false,
) {
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(100f / 136f)
            .clip(RoundedCornerShape(16.dp))
            .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(16.dp))
            .background(
                Brush.verticalGradient(listOf(AppColors.fieldGreenTop, AppColors.fieldGreenMid, AppColors.fieldGreenBottom)),
            ),
    ) {
        PitchMarkings()
        slots.forEachIndexed { index, slot ->
            val player = lineup.getOrNull(index)
            val card = player?.let { p -> if (p.id in suspendedIds) CardStatus.RED else if (p.id in yellowIds) CardStatus.YELLOW else null }
            val isActive = index == activeSlot
            Box(Modifier.fillMaxSize()) {
                Column(
                    modifier = Modifier
                        .align(androidx.compose.ui.BiasAlignment(2f * slot.x / 100f - 1f, 2f * slot.y / 100f - 1f))
                        .clickable { onSlotClick(index) },
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Box(
                        Modifier
                            .size(if (large) 52.dp else 44.dp)
                            .background(if (player != null) AppColors.ticketOrange else Color.White.copy(alpha = 0.12f), CircleShape)
                            .border(
                                BorderStroke(if (isActive) 3.dp else 2.dp, if (isActive) AppColors.antiqueGold else if (player != null) AppColors.ink else Color.White.copy(alpha = 0.85f)),
                                CircleShape,
                            ),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(slot.label, fontFamily = displayFontFamily(), fontWeight = FontWeight.Black, fontSize = if (large) 13.sp else 11.sp, color = if (player != null) AppColors.cream else Color.White)
                        if (card != null) {
                            Text(
                                if (card == CardStatus.RED) "🟥" else "🟨",
                                fontSize = 13.sp,
                                modifier = Modifier.align(Alignment.TopEnd).offset(x = 6.dp, y = (-6).dp),
                            )
                        }
                    }
                    if (player != null) {
                        Text(
                            player.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = if (large) 12.sp else 9.sp,
                            color = Color.White, maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}

/** One choosable (or suspended) player in the position picker. */
@Composable
private fun PlayerPickRow(player: Player, suspended: Boolean, hasYellow: Boolean, onChoose: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(if (suspended) AppColors.lossRedBg else AppColors.paper, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, if (suspended) Color(0xFFE0B4B4) else AppColors.paperBorder), RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .then(if (!suspended) Modifier.clickable(onClick = onChoose) else Modifier)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            player.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 14.sp,
            color = if (suspended) Color(0xFFB0A488) else AppColors.ink, modifier = Modifier.weight(1f),
        )
        if (hasYellow) Text("🟨", fontSize = 13.sp)
        if (suspended) {
            Text("🟥 SUSPENSO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.lossRed)
        } else {
            Text(player.role.name, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 12.sp, color = AppColors.kicker)
            secondaryRole(player.role)?.let { Text("($it)", fontFamily = monoFontFamily(), fontSize = 10.sp, color = AppColors.mutedText) }
        }
        Text("${player.rating}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AppColors.kicker)
    }
}

@Composable
private fun PitchMarkings() {
    androidx.compose.foundation.Canvas(Modifier.fillMaxSize()) {
        val strokeColor = Color.White.copy(alpha = 0.32f)
        val stroke = Stroke(width = 1.dp.toPx())
        drawRect(color = strokeColor, style = stroke, topLeft = Offset(size.width * 0.04f, size.height * 0.03f), size = androidx.compose.ui.geometry.Size(size.width * 0.92f, size.height * 0.94f))
        drawLine(strokeColor, Offset(size.width * 0.04f, size.height * 0.5f), Offset(size.width * 0.96f, size.height * 0.5f), strokeWidth = stroke.width)
        drawCircle(strokeColor, radius = size.width * 0.13f, center = Offset(size.width * 0.5f, size.height * 0.5f), style = stroke)
        drawRect(strokeColor, topLeft = Offset(size.width * 0.26f, size.height * 0.03f), size = androidx.compose.ui.geometry.Size(size.width * 0.48f, size.height * 0.125f), style = stroke)
        drawRect(strokeColor, topLeft = Offset(size.width * 0.26f, size.height * 0.845f), size = androidx.compose.ui.geometry.Size(size.width * 0.48f, size.height * 0.125f), style = stroke)
    }
}
