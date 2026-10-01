package com.mc857.copaamerica.domain.data

import com.mc857.copaamerica.domain.model.TeamAttributes

// FIFA 22 nationalities: top 11 players by overall, with the best available goalkeeper.
val NATIONAL_TEAM_ATTRIBUTES: Map<String, TeamAttributes> = mapOf(
    "Argentina" to TeamAttributes(82.6, 80.0, 55.4, 85.0),
    "Bolívia" to TeamAttributes(60.7, 61.4, 53.5, 70.0),
    "Brasil" to TeamAttributes(70.2, 76.4, 77.9, 88.0),
    "Colômbia" to TeamAttributes(72.9, 73.2, 62.4, 84.0),
    "Chile" to TeamAttributes(69.5, 73.2, 65.6, 83.0),
    "Equador" to TeamAttributes(69.2, 69.3, 56.5, 73.0),
    "Paraguai" to TeamAttributes(68.1, 68.8, 60.8, 75.0),
    "Venezuela" to TeamAttributes(70.6, 69.0, 53.4, 76.0),
    "Uruguai" to TeamAttributes(70.8, 72.8, 68.3, 79.0),
    "Estados Unidos" to TeamAttributes(67.6, 71.6, 67.7, 83.0),
    "México" to TeamAttributes(75.3, 75.6, 62.1, 83.0),
    "Costa Rica" to TeamAttributes(63.4, 66.2, 58.3, 89.0),
    "Panamá" to TeamAttributes(61.1, 62.6, 57.5, 76.0),
    "Haiti" to TeamAttributes(56.0, 57.0, 54.3, 70.0),
    "Jamaica" to TeamAttributes(67.5, 67.9, 59.6, 80.0),
    "Peru" to TeamAttributes(67.9, 70.6, 65.6, 75.0),
)

private val averageTeamAttributes = TeamAttributes(65.0, 65.0, 65.0, 70.0)

fun teamAttributesFor(teamName: String): TeamAttributes =
    NATIONAL_TEAM_ATTRIBUTES[teamName] ?: averageTeamAttributes