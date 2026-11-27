package com.mc857.copaamerica.domain.logic

import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.Position.DEF
import com.mc857.copaamerica.domain.model.Position.FW
import com.mc857.copaamerica.domain.model.Position.GK
import com.mc857.copaamerica.domain.model.Position.MID
import com.mc857.copaamerica.domain.model.SlotCfg

/** Slot layouts (x/y in percent of the pitch) for each formation. */
val FIELD_FORMATIONS: Map<FormKey, List<SlotCfg>> = mapOf(
    FormKey.F442 to listOf(
        SlotCfg("CA", FW, 36f, 17f), SlotCfg("CA", FW, 64f, 17f),
        SlotCfg("MEI", MID, 14f, 40f), SlotCfg("MC", MID, 38f, 44f), SlotCfg("MC", MID, 62f, 44f), SlotCfg("VOL", MID, 86f, 40f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    FormKey.F433 to listOf(
        SlotCfg("PE", FW, 18f, 18f), SlotCfg("CA", FW, 50f, 14f), SlotCfg("PD", FW, 82f, 18f),
        SlotCfg("MEI", MID, 25f, 40f), SlotCfg("MC", MID, 50f, 34f), SlotCfg("VOL", MID, 75f, 40f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    FormKey.F352 to listOf(
        SlotCfg("CA", FW, 36f, 16f), SlotCfg("CA", FW, 64f, 16f),
        SlotCfg("PE", MID, 10f, 39f), SlotCfg("MEI", MID, 30f, 34f), SlotCfg("MC", MID, 50f, 29f), SlotCfg("MC", MID, 70f, 34f), SlotCfg("PD", MID, 90f, 39f),
        SlotCfg("ZAG", DEF, 22f, 70f), SlotCfg("ZAG", DEF, 50f, 70f), SlotCfg("ZAG", DEF, 78f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
    FormKey.F4231 to listOf(
        SlotCfg("CA", FW, 50f, 14f),
        SlotCfg("PE", MID, 18f, 32f), SlotCfg("MEI", MID, 50f, 27f), SlotCfg("PD", MID, 82f, 32f),
        SlotCfg("VOL", MID, 36f, 47f), SlotCfg("VOL", MID, 64f, 47f),
        SlotCfg("LE", DEF, 12f, 70f), SlotCfg("ZAG", DEF, 37f, 70f), SlotCfg("ZAG", DEF, 63f, 70f), SlotCfg("LD", DEF, 88f, 70f),
        SlotCfg("GOL", GK, 50f, 89f),
    ),
)
