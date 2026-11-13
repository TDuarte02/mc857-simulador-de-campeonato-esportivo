package com.mc857.copaamerica.domain.data

import com.mc857.copaamerica.domain.model.TeamAttributes

// FIFA 22 nationalities: players selected and rated only by position-specific attributes.
val NATIONAL_TEAM_ATTRIBUTES: Map<String, TeamAttributes> = mapOf(
    "Argentina" to TeamAttributes(88.7, 80.7, 81.8, 86.0),
    "Bolívia" to TeamAttributes(67.8, 65.4, 68.9, 70.0),
    "Brasil" to TeamAttributes(84.7, 80.7, 84.4, 89.0),
    "Colômbia" to TeamAttributes(81.2, 76.3, 79.3, 84.0),
    "Chile" to TeamAttributes(76.1, 76.9, 76.5, 83.0),
    "Equador" to TeamAttributes(75.0, 72.0, 72.2, 73.0),
    "Paraguai" to TeamAttributes(71.6, 73.6, 75.5, 75.0),
    "Venezuela" to TeamAttributes(75.4, 73.9, 73.5, 76.0),
    "Uruguai" to TeamAttributes(81.4, 78.5, 81.9, 81.0),
    "Estados Unidos" to TeamAttributes(76.0, 75.0, 77.0, 83.0),
    "México" to TeamAttributes(80.5, 77.3, 76.2, 83.0),
    "Costa Rica" to TeamAttributes(71.5, 68.0, 70.8, 89.0),
    "Panamá" to TeamAttributes(66.8, 66.5, 71.2, 76.0),
    "Haiti" to TeamAttributes(62.8, 60.5, 62.5, 70.0),
    "Jamaica" to TeamAttributes(75.5, 71.2, 72.5, 80.0),
    "Peru" to TeamAttributes(74.5, 74.2, 73.9, 75.0),
)

private val averageTeamAttributes = TeamAttributes(65.0, 65.0, 65.0, 70.0)

fun teamAttributesFor(teamName: String): TeamAttributes =
    NATIONAL_TEAM_ATTRIBUTES[teamName] ?: averageTeamAttributes