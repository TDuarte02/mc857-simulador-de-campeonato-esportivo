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
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
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
import com.mc857.copaamerica.domain.model.SlotRole
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.displayFontFamily
import com.mc857.copaamerica.theme.hardShadow
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.theme.retroPaper
import com.mc857.copaamerica.ui.components.ChevronDownIcon
import com.mc857.copaamerica.ui.components.CircleFab
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.PlayTriangle
import com.mc857.copaamerica.ui.components.RetroPrimaryButton
import com.mc857.copaamerica.ui.components.RoleChip
import com.mc857.copaamerica.ui.components.TopBar
import com.mc857.copaamerica.ui.components.WideBackLink
import com.mc857.copaamerica.ui.components.WideCaption
import com.mc857.copaamerica.ui.components.WideChip
import com.mc857.copaamerica.ui.components.WideGrid
import com.mc857.copaamerica.ui.components.WideInkHeaderCard
import com.mc857.copaamerica.ui.components.WidePage
import com.mc857.copaamerica.ui.components.WideProgressBar
import com.mc857.copaamerica.ui.components.WideSearchField
import com.mc857.copaamerica.ui.components.WideTitle

private val SQUAD_TOTALS = mapOf(SlotCat.GK to 3, SlotCat.DEF to 8, SlotCat.MID to 8, SlotCat.FW to 7)

/** Auto-fill options: title, hint, squad builder. */
private val SQUAD_PRESETS: List<Triple<String, String, (List<Player>) -> List<Player>>> = listOf(
    Triple("Elenco Atual", "Os 26 convocados mais recentes", ::currentSquad),
    Triple("Seleção das Lendas", "Os 26 maiores da história", ::legendsSquad),
    Triple("Elenco Equilibrado", "18 atuais + 8 lendas", ::balancedSquad),
    Triple("Aleatório", "Sorteia cada posição", ::randomSquad),
)

private val SECTOR_LABELS = mapOf(SlotCat.GK to "Goleiros", SlotCat.DEF to "Defensores", SlotCat.MID to "Meio-campo", SlotCat.FW to "Atacantes")

private fun sectorColor(pos: SlotCat) = Color(roleColor(SlotRole.entries.first { it.sector == pos }))

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
    fun canAdd(player: Player) = player.id !in selected && (counts[player.pos] ?: 0) < (SQUAD_TOTALS[player.pos] ?: 0)
    fun toggle(player: Player) {
        selected = if (player.id in selected) selected - player.id else if (canAdd(player)) selected + player.id else selected
    }

    val visible = pool
        .filter { (filter == PosFilter.ALL || it.pos.name == filter.name) && it.name.contains(search, ignoreCase = true) }
        .sortedWith(if (sortByRating) compareByDescending<Player> { it.rating }.thenBy { it.name } else compareBy { it.name })

    val squad = pool.filter { it.id in selected }

    if (LocalWideLayout.current) {
        WideSquadBuilder(
            team = team, visible = visible, selected = selected, counts = counts, complete = complete,
            filter = filter, onFilter = { filter = it }, search = search, onSearch = { search = it },
            sortByRating = sortByRating, onSortByRating = { sortByRating = it },
            canAdd = ::canAdd, onToggle = ::toggle,
            onPreset = { preset -> applySquad(preset(pool)) }, onClear = { selected = emptySet() },
            onConfirm = { onNext(squad) }, onBack = onBack,
        )
        return
    }

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
                            .clip(RoundedCornerShape(8.dp))
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
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { sortMenuOpen = true }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("ORDENAR POR", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 11.sp, letterSpacing = 1.sp, color = AppColors.kicker)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            if (sortByRating) "Nota: maior primeiro" else "Nome: A–Z",
                            fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 13.sp, color = AppColors.ink,
                        )
                        ChevronDownIcon(color = AppColors.kicker)
                    }
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
                PlayerCard(player = player, selected = isSel, dimmed = !isSel && !canAdd(player), onClick = { toggle(player) })
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
        val presets = SQUAD_PRESETS.map { (title, hint, build) -> Triple(title, hint) { build(pool) } }
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
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { applySquad(apply()); presetSheetOpen = false }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text(title, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 15.sp, color = AppColors.ink)
                            Text(hint, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.mutedText)
                        }
                        PlayTriangle(color = AppColors.antiqueGold, size = 12.dp)
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
            .clip(RoundedCornerShape(12.dp))
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

@Composable
private fun WideSquadBuilder(
    team: TeamData,
    visible: List<Player>,
    selected: Set<Int>,
    counts: Map<SlotCat, Int>,
    complete: Boolean,
    filter: PosFilter,
    onFilter: (PosFilter) -> Unit,
    search: String,
    onSearch: (String) -> Unit,
    sortByRating: Boolean,
    onSortByRating: (Boolean) -> Unit,
    canAdd: (Player) -> Boolean,
    onToggle: (Player) -> Unit,
    onPreset: ((List<Player>) -> List<Player>) -> Unit,
    onClear: () -> Unit,
    onConfirm: () -> Unit,
    onBack: () -> Unit,
) {
    WidePage {
        WideBackLink("${team.flag} ${team.name} · Todos os tempos", onBack)
        Spacer(Modifier.height(4.dp))
        WideTitle("MONTAR", "ELENCO")
        Spacer(Modifier.height(24.dp))

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
            Column(Modifier.width(230.dp), verticalArrangement = Arrangement.spacedBy(22.dp)) {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    WideCaption("Posição")
                    PosFilter.entries.forEach { tab ->
                        val pos = SlotCat.entries.firstOrNull { it.name == tab.name }
                        WideSidebarTab(
                            label = pos?.let { SECTOR_LABELS.getValue(it) } ?: "Todos",
                            count = if (pos == null) "${selected.size}/26" else "${counts[pos] ?: 0}/${SQUAD_TOTALS.getValue(pos)}",
                            active = filter == tab,
                            onClick = { onFilter(tab) },
                        )
                    }
                }
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    WideCaption("Montar automaticamente")
                    SQUAD_PRESETS.forEach { (title, hint, build) ->
                        Column(
                            Modifier
                                .fillMaxWidth()
                                .background(AppColors.cream, RoundedCornerShape(12.dp))
                                .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(12.dp))
                                .clip(RoundedCornerShape(12.dp))
                                .clickable { onPreset(build) }
                                .padding(horizontal = 14.dp, vertical = 10.dp),
                        ) {
                            Text(title, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 17.sp, color = AppColors.ink)
                            Text(hint, fontFamily = monoFontFamily(), fontSize = 11.sp, color = AppColors.bodyText)
                        }
                    }
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .height(40.dp)
                            .border(BorderStroke(2.dp, AppColors.paperBorder), RoundedCornerShape(12.dp))
                            .clip(RoundedCornerShape(12.dp))
                            .clickable(onClick = onClear),
                        contentAlignment = Alignment.Center,
                    ) { Text("LIMPAR SELEÇÃO", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.5.sp, color = AppColors.kicker) }
                }
            }

            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    WideSearchField(search, onSearch, "Buscar jogadores…", Modifier.weight(1f))
                    WideChip("Nota", active = sortByRating, onClick = { onSortByRating(true) })
                    WideChip("Nome", active = !sortByRating, onClick = { onSortByRating(false) })
                }
                Text("${visible.size} jogadores · clique para selecionar", fontFamily = monoFontFamily(), fontSize = 13.sp, color = AppColors.bodyText)
                WideGrid(visible, minCellWidth = 180.dp, gap = 12.dp) { player ->
                    val isSel = player.id in selected
                    Box(Modifier.alpha(if (!isSel && !canAdd(player)) 0.45f else 1f)) {
                        PlayerCard(player = player, selected = isSel, dimmed = false, onClick = { onToggle(player) })
                    }
                }
            }

            WideInkHeaderCard("Seu elenco", "${selected.size}/26", Modifier.width(290.dp)) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    WideProgressBar(selected.size / 26f, AppColors.antiqueGold, height = 10.dp)
                    SlotCat.entries.forEach { pos ->
                        val count = counts[pos] ?: 0
                        val total = SQUAD_TOTALS.getValue(pos)
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(SECTOR_LABELS.getValue(pos).uppercase(), fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, letterSpacing = 1.sp, color = AppColors.ink)
                                Text("$count/$total", fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = if (count == total) AppColors.ticketGreenText else AppColors.kicker)
                            }
                            WideProgressBar(count / total.toFloat(), sectorColor(pos), height = 6.dp)
                        }
                    }
                    RetroPrimaryButton(
                        text = if (complete) "Confirmar elenco" else "Faltam ${26 - selected.size} jogadores",
                        enabled = complete,
                        onClick = onConfirm,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun WideSidebarTab(label: String, count: String, active: Boolean, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .height(44.dp)
            .background(if (active) AppColors.ink else AppColors.cream, RoundedCornerShape(12.dp))
            .border(BorderStroke(2.dp, if (active) AppColors.ink else AppColors.paperBorder), RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, fontFamily = displayFontFamily(), fontWeight = FontWeight.ExtraBold, fontSize = 17.sp, color = if (active) AppColors.paper else AppColors.ink)
        Text(count, fontFamily = monoFontFamily(), fontWeight = FontWeight.Bold, fontSize = 12.sp, color = if (active) AppColors.antiqueGold else AppColors.kicker)
    }
}

