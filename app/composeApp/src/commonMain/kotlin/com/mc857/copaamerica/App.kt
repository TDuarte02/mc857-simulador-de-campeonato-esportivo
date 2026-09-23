package com.mc857.copaamerica

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.mc857.copaamerica.domain.data.FIRST_MATCH_CARDS
import com.mc857.copaamerica.domain.logic.KnockoutRound
import com.mc857.copaamerica.domain.logic.applyGroupResult
import com.mc857.copaamerica.domain.logic.completeGroupStage
import com.mc857.copaamerica.domain.logic.decideTie
import com.mc857.copaamerica.domain.logic.finishKnockout
import com.mc857.copaamerica.domain.logic.groupMatchCards
import com.mc857.copaamerica.domain.logic.groupMatchScore
import com.mc857.copaamerica.domain.logic.koIndexOf
import com.mc857.copaamerica.domain.logic.makeDrawnBracket
import com.mc857.copaamerica.domain.logic.settleRound
import com.mc857.copaamerica.domain.logic.simulateTie
import com.mc857.copaamerica.domain.model.CardStatus
import com.mc857.copaamerica.domain.model.DrawnBracket
import com.mc857.copaamerica.domain.model.FormKey
import com.mc857.copaamerica.domain.model.MatchStatus
import com.mc857.copaamerica.domain.model.Phase
import com.mc857.copaamerica.domain.model.Player
import com.mc857.copaamerica.domain.model.PoolTeam
import com.mc857.copaamerica.domain.model.SlotCat
import com.mc857.copaamerica.domain.model.TeamData
import com.mc857.copaamerica.domain.model.TournamentFormat
import com.mc857.copaamerica.domain.repository.MockPlayerRepository
import com.mc857.copaamerica.domain.repository.MockTeamRepository
import com.mc857.copaamerica.nav.Screen
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.theme.monoFontFamily
import com.mc857.copaamerica.ui.screens.DrawSetupScreen
import com.mc857.copaamerica.ui.screens.EliminationScreen
import com.mc857.copaamerica.ui.screens.GroupStageScreen
import com.mc857.copaamerica.ui.screens.HomeScreen
import com.mc857.copaamerica.ui.screens.MatchResultScreen
import com.mc857.copaamerica.ui.screens.PhaseOverviewScreen
import com.mc857.copaamerica.ui.screens.PreMatchLineupScreen
import com.mc857.copaamerica.ui.screens.SquadBuilderScreen
import com.mc857.copaamerica.ui.screens.TeamSelectionScreen
import com.mc857.copaamerica.ui.screens.TournamentBracketScreen

/**
 * Root composable: owns the navigation stack and tournament state, mirroring
 * the `App()` component in design/src/App.tsx:2667-3046 for the
 * `gameMode==='normal'` (Modo Clássico) path — the only mode wired up in this
 * pass. Modo Rápido and Multiplayer stay as disabled entries on the Home
 * screen (see HomeScreen.kt).
 */
@Composable
fun CopaAmericaApp() {
    val teamRepository = remember { MockTeamRepository() }
    val playerRepository = remember { MockPlayerRepository() }
    var teams by remember { mutableStateOf<List<TeamData>>(emptyList()) }
    var pool by remember { mutableStateOf<List<Player>>(emptyList()) }

    LaunchedEffect(Unit) {
        teams = teamRepository.getTeams()
        pool = playerRepository.getPlayerPool()
    }

    if (teams.isEmpty() || pool.isEmpty()) {
        Box(Modifier.fillMaxSize().background(AppColors.surface), contentAlignment = Alignment.Center) {
            Text("CARREGANDO…", fontFamily = monoFontFamily(), color = AppColors.mutedText)
        }
        return
    }

    var stack by remember { mutableStateOf(listOf(Screen.HOME)) }
    var team by remember { mutableStateOf(teams[0]) }
    var lockedSquad by remember { mutableStateOf(listOf<Player>()) }
    var bracket by remember { mutableStateOf<DrawnBracket?>(null) }
    var phase by remember { mutableStateOf(Phase.GROUP) }
    var currentGroupMatchId by remember { mutableStateOf<String?>(null) }
    var lineup by remember { mutableStateOf(listOf<Player?>()) }
    var formKey by remember { mutableStateOf(FormKey.F442) }
    var cards by remember { mutableStateOf(mapOf<Int, CardStatus>()) }
    var matchesPlayed by remember { mutableStateOf(0) }

    fun nav(s: Screen) { stack = stack + s }
    fun goBack() { if (stack.size > 1) stack = stack.dropLast(1) }
    fun reset() {
        stack = listOf(Screen.HOME)
        team = teams[0]
        lockedSquad = emptyList()
        bracket = null
        phase = Phase.GROUP
        currentGroupMatchId = null
        lineup = emptyList()
        formKey = FormKey.F442
        cards = emptyMap()
        matchesPlayed = 0
    }

    val currentGroupMatch = bracket?.let { b -> currentGroupMatchId?.let { id -> b.groups.flatMap { it.matches }.firstOrNull { it.id == id } } }
    val koTies = bracket?.let { b -> if (phase == Phase.SF) b.ko.sf else if (phase == Phase.THIRD) listOf(b.ko.third) else b.ko.qf } ?: emptyList()
    val koTie = koTies.getOrNull(koIndexOf(koTies, team.name))
    val koRival = koTie?.let { if (it.home?.name == team.name) it.away else it.home }
    val currentOpponent: PoolTeam = currentGroupMatch?.let { if (it.home.name == team.name) it.away else it.home }
        ?: koRival ?: PoolTeam("Uruguai", "🇺🇾")

    val summaryCta: Pair<String, Screen>? = bracket?.let { b ->
        if (b.ko.final.winner != null) null
        else if (b.ko.sf.all { it.winner != null }) "Disputar o 3º lugar" to Screen.ELIMINATION
        else "Jogar a semifinal" to Screen.PRE_MATCH
    }

    /**
     * Books the two cards from the narrative's opening match (see
     * FIRST_MATCH_CARDS) onto whoever actually started, and drops the sent-off
     * player from the lineup. Mirrors App.tsx:2777-2797.
     */
    fun finishMatch() {
        if (matchesPlayed == 0) {
            val fielded = lineup.filterNotNull()
            val onField = fielded.ifEmpty { lockedSquad }
            val outfield = onField.filter { it.pos != SlotCat.GK }
            val candidates = if (outfield.size >= 2) outfield else onField
            val booked = mutableMapOf<Int, CardStatus>()
            val red = candidates.firstOrNull { FIRST_MATCH_CARDS[it.name] == CardStatus.RED } ?: candidates.lastOrNull()
            red?.let { booked[it.id] = CardStatus.RED }
            val yellow = candidates.firstOrNull { FIRST_MATCH_CARDS[it.name] == CardStatus.YELLOW && it.id != red?.id }
                ?: candidates.firstOrNull { it.id != red?.id }
            yellow?.let { booked[it.id] = CardStatus.YELLOW }
            cards = booked
            lineup = lineup.map { p -> if (p != null && booked[p.id] == CardStatus.RED) null else p }
        }
        matchesPlayed += 1
    }

    Box(Modifier.fillMaxSize().background(AppColors.surface).systemBarsPadding()) {
        when (val screen = stack.last()) {
            Screen.HOME -> HomeScreen(onClassic = { nav(Screen.TEAM_SELECTION) })

            Screen.TEAM_SELECTION -> TeamSelectionScreen(
                teams = teams,
                onNext = { t -> team = t; nav(Screen.SQUAD_BUILDER) },
                onBack = { goBack() },
            )

            Screen.SQUAD_BUILDER -> SquadBuilderScreen(
                team = team, pool = pool,
                onNext = { sq -> lockedSquad = sq; nav(Screen.DRAW_SETUP) },
                onBack = { goBack() }, onReset = { reset() },
            )

            Screen.DRAW_SETUP -> DrawSetupScreen(
                team = team, teams = teams,
                onNext = { shuffledRivals ->
                    val drawn = makeDrawnBracket(PoolTeam(team.name, team.flag), shuffledRivals, TournamentFormat.CLASSIC)
                    bracket = drawn
                    val first = drawn.groups.firstOrNull { g -> g.teams.any { it.name == team.name } }
                        ?.matches?.firstOrNull { it.home.name == team.name || it.away.name == team.name }
                    currentGroupMatchId = first?.id
                    phase = Phase.GROUP
                    nav(Screen.PRE_MATCH)
                },
                onBack = { goBack() }, onReset = { reset() },
            )

            Screen.PRE_MATCH -> PreMatchLineupScreen(
                team = team, opponent = currentOpponent, squad = lockedSquad, pool = pool,
                phase = phase, cards = cards, lineup = lineup, formKey = formKey,
                onLineupChange = { lineup = it }, onFormKeyChange = { formKey = it },
                onNext = { nav(Screen.MATCH_RESULT) },
                onBack = { goBack() }, onReset = { reset() },
            )

            Screen.MATCH_RESULT -> MatchResultScreen(
                team = team, opponent = currentOpponent, phase = phase,
                groupMatch = if (phase == Phase.GROUP) currentGroupMatch else null,
                squad = lockedSquad,
                onNext = {
                    finishMatch()
                    val b = bracket
                    when {
                        phase == Phase.GROUP && currentGroupMatchId != null && b != null -> {
                            val match = b.groups.flatMap { it.matches }.firstOrNull { it.id == currentGroupMatchId }
                            if (match != null) {
                                val (homeGoals, awayGoals) = groupMatchScore(match)
                                val withCards = groupMatchCards(match)
                                val groups = b.groups.map { g -> if (g.matches.any { it.id == match.id }) applyGroupResult(g, withCards, homeGoals, awayGoals) else g }
                                val userGames = groups.flatMap { it.matches }.count { (it.home.name == team.name || it.away.name == team.name) && it.status == MatchStatus.PLAYED }
                                val updated = b.copy(groups = groups)
                                bracket = if (userGames >= 3) completeGroupStage(updated) else updated
                                currentGroupMatchId = null
                                phase = Phase.GROUP
                                nav(Screen.GROUP_STAGE)
                            }
                        }
                        phase == Phase.SF && koTie != null && b != null -> {
                            val settled = settleRound(b.ko, KnockoutRound.SF, koIndexOf(b.ko.sf, team.name), decideTie(koTie, currentOpponent, 2, 1))
                            bracket = b.copy(ko = settled)
                            phase = Phase.THIRD
                            nav(Screen.ELIMINATION)
                        }
                        phase == Phase.THIRD && koTie != null && b != null -> {
                            val third = decideTie(koTie, PoolTeam(team.name, team.flag), 2, 1)
                            bracket = b.copy(ko = finishKnockout(b.ko.copy(third = third)))
                            nav(Screen.PHASE_OVERVIEW)
                        }
                        koTie != null && b != null -> {
                            val settled = settleRound(b.ko, KnockoutRound.QF, koIndexOf(b.ko.qf, team.name), decideTie(koTie, PoolTeam(team.name, team.flag), 2, 1))
                            bracket = b.copy(ko = settled)
                            phase = Phase.SF
                            nav(Screen.BRACKET)
                        }
                        else -> nav(Screen.ELIMINATION)
                    }
                },
                onBack = { goBack() }, onReset = { reset() },
            )

            Screen.GROUP_STAGE -> bracket?.let { b ->
                GroupStageScreen(
                    bracket = b, team = team,
                    onPlayNext = { match -> currentGroupMatchId = match.id; phase = Phase.GROUP; nav(Screen.PRE_MATCH) },
                    onQuarterfinals = { phase = Phase.QF; nav(Screen.BRACKET) },
                    onBack = { goBack() }, onReset = { reset() },
                )
            }

            Screen.BRACKET -> bracket?.let { b ->
                TournamentBracketScreen(
                    team = team, bracket = b,
                    onAdvance = { nav(Screen.PRE_MATCH) },
                    onSummary = { nav(Screen.PHASE_OVERVIEW) },
                    onBack = { goBack() }, onReset = { reset() },
                )
            }

            Screen.ELIMINATION -> bracket?.let { b ->
                EliminationScreen(
                    team = team, bracket = b,
                    onPlayThird = { phase = Phase.THIRD; nav(Screen.PRE_MATCH) },
                    onSimulateRest = { bracket = b.copy(ko = finishKnockout(b.ko.copy(third = simulateTie(b.ko.third)))) },
                    onSeeResults = { nav(Screen.PHASE_OVERVIEW) },
                    onBack = { goBack() },
                )
            }

            Screen.PHASE_OVERVIEW -> bracket?.let { b ->
                PhaseOverviewScreen(
                    team = team, bracket = b,
                    ctaLabel = summaryCta?.first,
                    onNext = summaryCta?.let { (_, target) -> { nav(target) } },
                    onBack = { goBack() }, onReset = { reset() },
                )
            }
        }
    }
}
