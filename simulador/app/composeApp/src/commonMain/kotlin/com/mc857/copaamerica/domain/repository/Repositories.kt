package com.mc857.copaamerica.domain.repository

import com.mc857.copaamerica.domain.data.MOCK_PLAYER_POOL
import com.mc857.copaamerica.domain.data.MOCK_STADIUMS
import com.mc857.copaamerica.domain.data.MOCK_TEAMS
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.Stadium
import com.mc857.copaamerica.domain.model.TeamData

/**
 * Data sources for the tournament. Mocked for now (see MOCK_* in
 * domain/data) — the plan is to swap these for real endpoint-backed
 * implementations later without touching domain logic or UI.
 */
interface TeamRepository {
    suspend fun getTeams(): List<TeamData>
}

interface PlayerRepository {
    suspend fun getPlayerPool(): List<Player>
}

interface StadiumRepository {
    suspend fun getStadiums(): List<Stadium>
}

class MockTeamRepository : TeamRepository {
    override suspend fun getTeams(): List<TeamData> = MOCK_TEAMS
}

class MockPlayerRepository : PlayerRepository {
    override suspend fun getPlayerPool(): List<Player> = MOCK_PLAYER_POOL
}

class MockStadiumRepository : StadiumRepository {
    override suspend fun getStadiums(): List<Stadium> = MOCK_STADIUMS
}
