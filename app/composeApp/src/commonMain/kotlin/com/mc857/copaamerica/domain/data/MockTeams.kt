package com.mc857.copaamerica.domain.data

import com.mc857.copaamerica.domain.model.Confederation
import com.mc857.copaamerica.domain.model.Confederation.CONCACAF
import com.mc857.copaamerica.domain.model.Confederation.CONMEBOL
import com.mc857.copaamerica.domain.model.TeamData

/** The 16-nation pool, mirroring design/src/App.tsx:83-100. */
val MOCK_TEAMS: List<TeamData> = listOf(
    TeamData("argentina", "Argentina", "🇦🇷", CONMEBOL),
    TeamData("bolivia", "Bolívia", "🇧🇴", CONMEBOL),
    TeamData("brazil", "Brasil", "🇧🇷", CONMEBOL),
    TeamData("colombia", "Colômbia", "🇨🇴", CONMEBOL),
    TeamData("chile", "Chile", "🇨🇱", CONMEBOL),
    TeamData("ecuador", "Equador", "🇪🇨", CONMEBOL),
    TeamData("paraguay", "Paraguai", "🇵🇾", CONMEBOL),
    TeamData("venezuela", "Venezuela", "🇻🇪", CONMEBOL),
    TeamData("uruguay", "Uruguai", "🇺🇾", CONMEBOL),
    TeamData("usa", "Estados Unidos", "🇺🇸", CONCACAF),
    TeamData("mexico", "México", "🇲🇽", CONCACAF),
    TeamData("costa_rica", "Costa Rica", "🇨🇷", CONCACAF),
    TeamData("panama", "Panamá", "🇵🇦", CONCACAF),
    TeamData("haiti", "Haiti", "🇭🇹", CONCACAF),
    TeamData("jamaica", "Jamaica", "🇯🇲", CONCACAF),
    TeamData("peru", "Peru", "🇵🇪", CONMEBOL),
)
