package com.mc857.copaamerica.data

/** Fachada usada por App.kt e pelas telas; troque por um fake nos testes. */
interface GameRepository {
    suspend fun nations(): List<NationDto>
    suspend fun pool(nation: String): PoolDto
    suspend fun createGame(userTeam: String, squad: List<String>, seed: Int? = null): CreateGameDto
    suspend fun state(gameId: String): GameStateDto
    suspend fun advance(gameId: String): AdvanceDto
    suspend fun startMatch(gameId: String, picks: List<PickDto>? = null): ActiveMatchDto
    suspend fun changeLineup(gameId: String, picks: List<PickDto>, formation: List<String>? = null): ActiveMatchDto
    suspend fun play(gameId: String, until: String): PlayDto
    suspend fun secondHalf(gameId: String): ActiveMatchDto
    suspend fun cancelMatch(gameId: String): GameStateDto
    suspend fun simulate(gameId: String): GameStateDto
    suspend fun result(gameId: String): FinalResultDto
    suspend fun matchView(gameId: String, matchId: String): MatchViewDto
}

class ApiGameRepository(private val api: GameApi = GameApi()) : GameRepository {
    override suspend fun nations() = api.nations()
    override suspend fun pool(nation: String) = api.players(nation)
    override suspend fun createGame(userTeam: String, squad: List<String>, seed: Int?) = api.createGame(userTeam, squad, seed)
    override suspend fun state(gameId: String) = api.game(gameId)
    override suspend fun advance(gameId: String) = api.advance(gameId)
    override suspend fun startMatch(gameId: String, picks: List<PickDto>?) = api.startMatch(gameId, picks)
    override suspend fun changeLineup(gameId: String, picks: List<PickDto>, formation: List<String>?) = api.changeLineup(gameId, picks, formation)
    override suspend fun play(gameId: String, until: String) = api.play(gameId, until)
    override suspend fun secondHalf(gameId: String) = api.secondHalf(gameId)
    override suspend fun cancelMatch(gameId: String) = api.cancelMatch(gameId)
    override suspend fun simulate(gameId: String) = api.simulate(gameId)
    override suspend fun result(gameId: String) = api.result(gameId)
    override suspend fun matchView(gameId: String, matchId: String) = api.matchView(gameId, matchId)
}

/** Mapeamento `SlotRole` (UI) -> posição canônica do motor, para montar os `picks`. */
fun canonicalSlot(role: String): String = when (role) {
    "GOL" -> "GK"; "LD", "LE" -> "FB"; "ZAG" -> "CB"; "VOL" -> "DM"
    "MC" -> "CM"; "MEI" -> "AM"; "PD", "PE" -> "W"; "CA" -> "ST"
    else -> role  // GK/RB/LB/CB/CM/RW/ST… já são aceitos pelo motor
}
