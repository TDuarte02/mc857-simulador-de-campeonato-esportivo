@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.mc857.copaamerica.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mc857.copaamerica.domain.logic.balancedSquad
import com.mc857.copaamerica.domain.logic.currentSquad
import com.mc857.copaamerica.domain.logic.legendsSquad
import com.mc857.copaamerica.domain.logic.playerAttrs
import com.mc857.copaamerica.domain.logic.randomSquad
import com.mc857.copaamerica.domain.logic.roleColor
import com.mc857.copaamerica.domain.logic.secondaryRole
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.PosFilter
import com.mc857.copaamerica.domain.model.SlotCat
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RoleChip
import com.mc857.copaamerica.ui.components.TopBar

private val SQUAD_TOTALS = mapOf(SlotCat.GK to 3, SlotCat.DEF to 8, SlotCat.MID to 8, SlotCat.FW to 7)

/** Mirrors SquadBuilder, App.tsx:925-1144. */
@Composable
fun SquadBuilderScreen(
    team: TeamData,
    pool: List<Player>,
    onNext: (List<Player>) -> Unit,
    onBack: () -> Unit,
    onReset: () -> Unit,
) {
    var selected by remember { mutableStateOf(setOf<Int>()) }
    var filter by remember { mutableStateOf(PosFilter.ALL) }
    var search by remember { mutableStateOf("") }
    var sortByRating by remember { mutableStateOf(true) }
    var sortMenuOpen by remember { mutableStateOf(false) }
    var presetSheetOpen by remember { mutableStateOf(false) }

    fun posOf(id: Int) = pool.firstOrNull { it.id == id }?.pos
    val counts = SlotCat.entries.associateWith { pos -> selected.count { posOf(it) == pos } }
    val complete = SQUAD_TOTALS.all { (pos, total) -> counts[pos] == total }

    fun applySquad(players: List<Player>) { selected = players.map { it.id }.toSet() }

    val visible = pool
        .filter { (filter == PosFilter.ALL || it.pos.name == filter.name) && it.name.contains(search, ignoreCase = true) }
        .sortedWith(if (sortByRating) compareByDescending<Player> { it.rating }.thenBy { it.name } else compareBy { it.name })

    val squad = pool.filter { it.id in selected }

    Box(Modifier.fillMaxSize()) {
    Column(Modifier.fillMaxSize().retroPaper()) {
        TopBar(title = "Montar elenco", sub = "${team.flag} ${team.name} · Todos os tempos", onBack = onBack, onReset = onReset)

        Column(Modifier.background(AppColors.paper).padding(horizontal = 16.dp, vertical = 10.dp)) {
            Box(
                Modifier
                    .fillMaxWidth()
                    .background(AppColors.cream, RoundedCornerShape(10.dp))
                    .border(BorderStroke(2.dp, AppColors.ink), RoundedCornerShape(10.dp)),
            ) {
                BasicTextField(
                    value = search,
                    onValueChange = { search = it },
                    singleLine = true,
                    textStyle = TextStyle(fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.ink),
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
                    decorationBox = { inner ->
                        if (search.isEmpty()) Text("Buscar jogadores…", fontFamily = monoFontFamily(), fontSize = 14.sp, color = AppColors.mutedText)
                        inner()
                    },
                )
            }
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                PosFilter.entries.forEach { tab ->
                    val active = filter == tab
                    val label = if (tab == PosFilter.ALL) "TODOS" else "${tab.name} ${counts[SlotCat.valueOf(tab.name)] ?: 0}/${SQUAD_TOTALS[SlotCat.valueOf(tab.name)] ?: 0}"
                    Box(
                        Modifier
                            .weight(1f)
                            .background(if (active) AppColors.ink else AppColors.cream, RoundedCornerShape(8.dp))
                            .border(BorderStroke(2.dp, if (active) AppColors.ink else AppColors.paperBorder), RoundedCornerShape(8.dp))
                            .clickable { filter = tab }
                            .padding(vertical = 6.dp),
                    ) {
                        Text(
                            label, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 10.sp,
                            color = if (active) AppColors.paper else AppColors.bodyText, textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Box {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(AppColors.cream, RoundedCornerShape(8.dp))
                        .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(8.dp))
                        .clickable { sortMenuOpen = true }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text("ORDENAR POR", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                    Text(
                        (if (sortByRating) "Nota: maior primeiro" else "Nome: A–Z") + " ⌄",
                        fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink,
                    )
                }
                DropdownMenu(expanded = sortMenuOpen, onDismissRequest = { sortMenuOpen = false }) {
                    DropdownMenuItem(text = { Text("Nota: maior primeiro") }, onClick = { sortByRating = true; sortMenuOpen = false })
                    DropdownMenuItem(text = { Text("Nome: A–Z") }, onClick = { sortByRating = false; sortMenuOpen = false })
                }
            }
        }

        Text(
            "${visible.size} jogadores · Toque para selecionar",
            fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.kicker,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(visible, key = { it.id }) { player ->
                val isSel = player.id in selected
                val canAdd = !isSel && (counts[player.pos] ?: 0) < (SQUAD_TOTALS[player.pos] ?: 0)
                PlayerCard(
                    player = player, selected = isSel, dimmed = !isSel && !canAdd,
                    onClick = {
                        selected = if (isSel) selected - player.id else if (canAdd) selected + player.id else selected
                    },
                )
            }
        }

        Column(Modifier.background(AppColors.paper).padding(20.dp)) {
            RetroPrimaryButton(
                text = if (complete) "Confirmar elenco · 26/26" else "${selected.size}/26 selecionados",
                enabled = complete,
                onClick = { onNext(squad) },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }

    Box(Modifier.fillMaxSize().padding(20.dp), contentAlignment = Alignment.BottomEnd) {
        Box(Modifier.padding(bottom = 96.dp)) {
            CircleFab(onClick = { presetSheetOpen = true }) {
                Text("✨", fontSize = 20.sp)
            }
        }
    }
    } // Box

    if (presetSheetOpen) {
        val presets = listOf(
            Triple("Elenco Atual", "Os 26 convocados mais recentes") { currentSquad(pool) },
            Triple("Seleção das Lendas", "Os 26 maiores da história") { legendsSquad(pool) },
            Triple("Elenco Equilibrado", "18 atuais + 8 lendas") { balancedSquad(pool) },
            Triple("Aleatório", "Sorteia cada posição") { randomSquad(pool) },
        )
        ModalBottomSheet(onDismissRequest = { presetSheetOpen = false }, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.padding(horizontal = 20.dp).padding(bottom = 24.dp)) {
                Text(
                    "MONTAR ELENCO AUTOMATICAMENTE", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold,
                    fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.kicker, modifier = Modifier.padding(bottom = 12.dp),
                )
                presets.forEach { (title, hint, apply) ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .padding(bottom = 8.dp)
                            .background(AppColors.cream, RoundedCornerShape(12.dp))
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(12.dp))
                            .clickable { applySquad(apply()); presetSheetOpen = false }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text(title, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 15.sp, color = AppColors.ink)
                            Text(hint, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                        }
                        Text("▶", color = AppColors.antiqueGold, fontSize = 16.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun PlayerCard(player: Player, selected: Boolean, dimmed: Boolean, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(if (selected) AppColors.ticketOrangeBg else AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, if (selected) AppColors.antiqueGold else AppColors.paperBorder), RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(10.dp)
            .then(if (dimmed) Modifier else Modifier),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(56.dp)
                .background(AppColors.card2, RoundedCornerShape(8.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text("⚽", fontSize = 22.sp, modifier = Modifier.align(Alignment.Center))
            Box(Modifier.align(Alignment.BottomEnd).background(AppColors.ink.copy(alpha = 0.85f), RoundedCornerShape(6.dp)).padding(horizontal = 4.dp, vertical = 1.dp)) {
                Text("${player.rating}", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, color = AppColors.paper)
            }
        }
        Spacer(Modifier.height(6.dp))
        Text(player.name.uppercase(), fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink, maxLines = 1)
        Row(Modifier.padding(top = 2.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(player.era, fontFamily = monoFontFamily(), fontSize = 9.sp, color = AppColors.bodyText)
            Spacer(Modifier.weight(1f))
            RoleChip(player.role.name, androidx.compose.ui.graphics.Color(roleColor(player.role)))
            secondaryRole(player.role)?.let {
                Text("($it)", fontFamily = monoFontFamily(), fontSize = 9.sp, color = AppColors.kicker)
            }
        }
        playerAttrs(player)?.let { attrs ->
            Text(
                "${attrs.keys.first} ${attrs.values.first} · ${attrs.keys.second} ${attrs.values.second} · ${attrs.keys.third} ${attrs.values.third}",
                fontFamily = monoFontFamily(), fontSize = 9.sp, color = AppColors.mutedText, maxLines = 1,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
