package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.Availability
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.Position
import com.mc857.copaamerica.domain.model.SlotCfg

/** Call-up shape the API enforces: 3 GK / 8 DEF / 8 MID / 7 FW (26 total). */
val SQUAD_TOTALS: Map<Position, Int> = mapOf(
    Position.GK to 3, Position.DEF to 8, Position.MID to 8, Position.FW to 7,
)

val SQUAD_SIZE: Int = SQUAD_TOTALS.values.sum()

/**
 * Repositions players already on the pitch when the formation changes: keeps
 * them grouped by sector instead of clearing the whole lineup.
 */
fun remapLineup(previous: List<Player?>, nextSlots: List<SlotCfg>): List<Player?> {
    val used = mutableSetOf<Int>()
    val onPitch = previous.filterNotNull()
    return nextSlots.map { slot ->
        onPitch.firstOrNull { it.position == slot.cat && it.id !in used }?.also { used.add(it.id) }
    }
}

/**
 * Who may fill [slot]. Goalkeepers and outfield players do not swap places; the
 * API only waives that when no goalkeeper is fit. A sector with nobody left
 * borrows other outfield players.
 */
fun eligibleFor(slot: SlotCfg, availability: Availability, taken: Set<Int>): List<Player> {
    val available = availability.available.map { it.player }
    val free = available.filter { it.id !in taken }
    val candidates = when {
        slot.cat == Position.GK ->
            if (available.any { it.position == Position.GK }) free.filter { it.position == Position.GK } else free
        else -> free.filter { it.position == slot.cat }
            .ifEmpty { free.filter { it.position != Position.GK } }
    }
    return candidates.sortedByDescending { it.overall }
}

/** A random eligible XI for the given slots; positions nobody can fill stay empty. */
fun randomLineup(slots: List<SlotCfg>, availability: Availability): List<Player?> {
    val taken = mutableSetOf<Int>()
    return slots.map { slot ->
        val candidates = eligibleFor(slot, availability, taken)
        // Prefer the slot's own sector when eligibleFor had to widen the list.
        (candidates.filter { it.position == slot.cat }.ifEmpty { candidates })
            .randomOrNull()
            ?.also { taken.add(it.id) }
    }
}
