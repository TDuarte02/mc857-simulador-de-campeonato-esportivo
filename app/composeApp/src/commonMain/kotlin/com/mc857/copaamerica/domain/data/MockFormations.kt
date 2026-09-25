package com.mc857.copaamerica.domain.data

import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.FormKey.F352
import com.mc857.copaamerica.domain.model.FormKey.F433
import com.mc857.copaamerica.domain.model.FormKey.F442
import com.mc857.copaamerica.domain.model.FormKey.F4231
import com.mc857.copaamerica.domain.model.SlotCat.DEF
import com.mc857.copaamerica.domain.model.SlotCat.FW
import com.mc857.copaamerica.domain.model.SlotCat.GK
import com.mc857.copaamerica.domain.model.SlotCat.MID
import com.mc857.copaamerica.domain.model.SlotCfg

/**
 * Slot layouts (x/y in percent of the pitch) for each formation, mirroring
 * design/src/App.tsx:177-213 (FORMATIONS) and :288-314 (FIELD_FORMATIONS).
 * The two sets differ only in which end of the pitch attacks face.
 */
val FORMATIONS: Map<FormKey, List<SlotCfg>> = mapOf(
    F442 to listOf(
        SlotCfg("GOL", GK, 50f, 90f),
        SlotCfg("LE", DEF, 12f, 69f), SlotCfg("ZAG", DEF, 37f, 69f),
        SlotCfg("ZAG", DEF, 63f, 69f), SlotCfg("LD", DEF, 88f, 69f),
        SlotCfg("VOL", MID, 50f, 53f), SlotCfg("MC", MID, 50f, 43f),
        SlotCfg("MEI", MID, 50f, 33f), SlotCfg("MEI", MID, 50f, 33f),
        SlotCfg("PE", FW, 22f, 20f), SlotCfg("PD", FW, 78f, 20f),
    ),
    F433 to listOf(
        SlotCfg("GK", GK, 50f, 88f),
        SlotCfg("RB", DEF, 14f, 71f), SlotCfg("CB", DEF, 34f, 71f),
        SlotCfg("CB", DEF, 66f, 71f), SlotCfg("LB", DEF, 86f, 71f),
        SlotCfg("CM", MID, 24f, 50f), SlotCfg("CM", MID, 50f, 50f), SlotCfg("CM", MID, 76f, 50f),
        SlotCfg("RW", FW, 18f, 24f), SlotCfg("ST", FW, 50f, 21f), SlotCfg("LW", FW, 82f, 24f),
    ),
    F352 to listOf(
        SlotCfg("GK", GK, 50f, 88f),
        SlotCfg("CB", DEF, 22f, 70f), SlotCfg("CB", DEF, 50f, 70f), SlotCfg("CB", DEF, 78f, 70f),
        SlotCfg("RM", MID, 10f, 49f), SlotCfg("CM", MID, 30f, 51f),
        SlotCfg("CM", MID, 50f, 53f), SlotCfg("CM", MID, 70f, 51f), SlotCfg("LM", MID, 90f, 49f),
        SlotCfg("ST", FW, 34f, 24f), SlotCfg("ST", FW, 66f, 24f),
    ),
    F4231 to listOf(
        SlotCfg("GK", GK, 50f, 88f),
        SlotCfg("RB", DEF, 14f, 72f), SlotCfg("CB", DEF, 34f, 72f),
        SlotCfg("CB", DEF, 66f, 72f), SlotCfg("LB", DEF, 86f, 72f),
        SlotCfg("DM", MID, 34f, 57f), SlotCfg("DM", MID, 66f, 57f),
        SlotCfg("RAM", MID, 17f, 37f), SlotCfg("CAM", MID, 50f, 37f), SlotCfg("LAM", MID, 83f, 37f),
        SlotCfg("ST", FW, 50f, 20f),
    ),
)

val FIELD_FORMATIONS: Map<FormKey, List<SlotCfg>> = mapOf(
    F442 to listOf(
        SlotCfg("CA", FW, 36f, 17f), SlotCfg("CA", FW, 64f, 17f),
        SlotCfg("MEI", MID, 14f, 40f), SlotCfg("MC", MID, 38f, 44f), SlotCfg("MC", MID, 62f, 44f), SlotCfg("VOL", MID, 86f, 40f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    F433 to listOf(
        SlotCfg("PE", FW, 18f, 18f), SlotCfg("CA", FW, 50f, 14f), SlotCfg("PD", FW, 82f, 18f),
        SlotCfg("MEI", MID, 25f, 40f), SlotCfg("MC", MID, 50f, 34f), SlotCfg("VOL", MID, 75f, 40f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    F352 to listOf(
        SlotCfg("CA", FW, 36f, 16f), SlotCfg("CA", FW, 64f, 16f),
        SlotCfg("PE", MID, 10f, 39f), SlotCfg("MEI", MID, 30f, 34f), SlotCfg("MC", MID, 50f, 29f), SlotCfg("MC", MID, 70f, 34f), SlotCfg("PD", MID, 90f, 39f),
        SlotCfg("ZAG", DEF, 22f, 70f), SlotCfg("ZAG", DEF, 50f, 70f), SlotCfg("ZAG", DEF, 78f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    F4231 to listOf(
        SlotCfg("CA", FW, 50f, 14f),
        SlotCfg("PE", MID, 18f, 32f), SlotCfg("MEI", MID, 50f, 27f), SlotCfg("PD", MID, 82f, 32f),
        SlotCfg("VOL", MID, 36f, 47f), SlotCfg("VOL", MID, 64f, 47f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
)
