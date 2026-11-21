package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.SlotCat
import com.mc857.copaamerica.domain.model.SlotCfg
import com.mc857.copaamerica.domain.model.SlotRole

/** Squad size per sector — always 3 GK / 8 DEF / 8 MID / 7 FW (26 total). Mirrors App.tsx:391. */
val SQUAD_TOTALS: Map<SlotCat, Int> = mapOf(
    SlotCat.GK to 3, SlotCat.DEF to 8, SlotCat.MID to 8, SlotCat.FW to 7,
)

/**
 * "Elenco atual" is meant to be a real call-up list kept outside the code;
 * empty here just like design/src/App.tsx:395, so the preset falls back to
 * the rating-based fill below.
 */
val CURRENT_SQUAD_NAMES: List<String> = emptyList()

/** Builds a valid 26-player squad giving `priority` first pick per sector, filling the rest by rating. Mirrors App.tsx:399-412. */
fun squadByPriority(pool: List<Player>, priority: List<Player>, priorityPerPos: Map<SlotCat, Int> = SQUAD_TOTALS): List<Player> {
    val drawn = mutableListOf<Player>()
    for (pos in listOf(SlotCat.GK, SlotCat.DEF, SlotCat.MID, SlotCat.FW)) {
        val cap = priorityPerPos[pos] ?: SQUAD_TOTALS.getValue(pos)
        val prio = priority.filter { it.pos == pos }.take(cap)
        val usedIds = prio.map { it.id }.toSet()
        val fillCount = SQUAD_TOTALS.getValue(pos) - prio.size
        val fill = pool
            .filter { it.pos == pos && it.id !in usedIds }
            .sortedByDescending { it.rating }
            .take(fillCount)
        drawn += prio
        drawn += fill
    }
    return drawn
}

fun defaultSquad(pool: List<Player>): List<Player> {
    fun top(pos: SlotCat, n: Int) = pool.filter { it.pos == pos }.sortedByDescending { it.rating }.take(n)
    return top(SlotCat.GK, 3) + top(SlotCat.DEF, 8) + top(SlotCat.MID, 8) + top(SlotCat.FW, 7)
}

fun currentSquad(pool: List<Player>): List<Player> {
    val byName = pool.associateBy { it.name }
    val named = CURRENT_SQUAD_NAMES.mapNotNull { byName[it] }
    return squadByPriority(pool, named, SQUAD_TOTALS)
}

fun legendsSquad(pool: List<Player>): List<Player> =
    squadByPriority(pool, pool.sortedByDescending { it.rating }, SQUAD_TOTALS)

/** 18 current call-ups + 8 legends filling the rest. Mirrors App.tsx:420-422. */
fun balancedSquad(pool: List<Player>): List<Player> =
    squadByPriority(pool, currentSquad(pool), mapOf(SlotCat.GK to 2, SlotCat.DEF to 6, SlotCat.MID to 5, SlotCat.FW to 5))

fun randomSquad(pool: List<Player>): List<Player> =
    listOf(SlotCat.GK, SlotCat.DEF, SlotCat.MID, SlotCat.FW).flatMap { pos ->
        pool.filter { it.pos == pos }.shuffled().take(SQUAD_TOTALS.getValue(pos))
    }

/**
 * Repositions players already on the pitch when the formation changes: keeps
 * them grouped by sector instead of clearing the whole lineup. Mirrors
 * App.tsx:330-340.
 */
fun remapLineup(previous: List<Player?>, nextSlots: List<SlotCfg>): List<Player?> {
    val bySector: MutableMap<SlotCat, MutableList<Player>> = mutableMapOf(
        SlotCat.GK to mutableListOf(), SlotCat.DEF to mutableListOf(),
        SlotCat.MID to mutableListOf(), SlotCat.FW to mutableListOf(),
    )
    previous.filterNotNull().forEach { bySector.getValue(it.pos).add(it) }
    val used = mutableSetOf<Int>()
    return nextSlots.map { slot ->
        val found = bySector.getValue(slot.cat).firstOrNull { it.id !in used }
        found?.also { used.add(it.id) }
    }
}

private val ROLE_COLOR: Map<SlotCat, Long> = mapOf(
    SlotCat.GK to 0xFFB45309, SlotCat.DEF to 0xFF2563EB, SlotCat.MID to 0xFF059669, SlotCat.FW to 0xFFB91C1C,
)

fun roleColor(role: SlotRole): Long = ROLE_COLOR.getValue(role.sector)

private val SECONDARY_ROLE: Map<SlotRole, String> = mapOf(
    SlotRole.CA to "MA", SlotRole.PD to "CA", SlotRole.PE to "CA",
    SlotRole.MEI to "MC", SlotRole.MC to "VOL", SlotRole.VOL to "ZAG",
    SlotRole.ZAG to "VOL", SlotRole.LD to "ZAG", SlotRole.LE to "ZAG",
)

fun secondaryRole(role: SlotRole): String? = SECONDARY_ROLE[role]

data class PlayerAttrs(val keys: Triple<String, String, String>, val values: Triple<Int, Int, Int>)

/** Derived attribute readout shown on player cards. Mirrors App.tsx:382-388. */
fun playerAttrs(player: Player): PlayerAttrs? {
    if (player.pos == SlotCat.GK) return null
    val isBackline = player.role in setOf(SlotRole.ZAG, SlotRole.LD, SlotRole.LE, SlotRole.VOL)
    return if (isBackline) {
        PlayerAttrs(Triple("DES", "FOR", "CAB"), Triple(player.rating - 1, player.rating - 4, player.rating - 6))
    } else {
        PlayerAttrs(Triple("FIN", "VEL", "PAS"), Triple(player.rating - 1, player.rating - 7, player.rating - 9))
    }
}

val DEFAULT_FORM_KEY = FormKey.F442
