@file:OptIn(coil3.annotation.ExperimentalCoilApi::class)

package com.mc857.copaamerica

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import coil3.ImageLoader
import coil3.compose.setSingletonImageLoaderFactory
import coil3.network.ktor3.KtorNetworkFetcherFactory
import com.mc857.copaamerica.data.CopaApi
import com.mc857.copaamerica.domain.logic.NextStep
import com.mc857.copaamerica.domain.model.Stage
import com.mc857.copaamerica.nav.Screen
import com.mc857.copaamerica.platform.apiBaseUrl
import com.mc857.copaamerica.platform.apiKey
import com.mc857.copaamerica.platform.deviceStore
import com.mc857.copaamerica.state.PlayerStats
import com.mc857.copaamerica.state.SavedTournament
import com.mc857.copaamerica.state.TournamentController
import com.mc857.copaamerica.theme.AppColors
import com.mc857.copaamerica.ui.components.LocalWideLayout
import com.mc857.copaamerica.ui.components.RequestOverlay
import com.mc857.copaamerica.ui.components.TournamentStep
import com.mc857.copaamerica.ui.components.WideLayoutMinWidth
import com.mc857.copaamerica.ui.components.WideNarrowColumn
import com.mc857.copaamerica.ui.components.WideNavBar
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
 * Root composable: draws the screen the [TournamentController] points at. Only
 * Modo Clássico is wired up; Modo Rápido and Multiplayer stay disabled on Home.
 */
@Composable
fun CopaAmericaApp() {
    setSingletonImageLoaderFactory { context ->
        ImageLoader.Builder(context).components { add(KtorNetworkFetcherFactory()) }.build()
    }
    val scope = rememberCoroutineScope()
    val controller = remember {
        val store = deviceStore()
        TournamentController(CopaApi(apiBaseUrl, apiKey), scope, apiBaseUrl, PlayerStats(store), SavedTournament(store))
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(AppColors.surface).systemBarsPadding()) {
        val wide = maxWidth >= WideLayoutMinWidth
        val screen = controller.screen
        CompositionLocalProvider(LocalWideLayout provides wide) {
            Column(Modifier.fillMaxSize()) {
                if (wide) {
                    WideNavBar(
                        step = tournamentStep(screen, controller),
                        onReset = if (screen == Screen.HOME) null else controller::reset,
                    )
                }
                Box(Modifier.weight(1f).fillMaxWidth()) {
                    // Below the wide breakpoint the phone layout stays phone-width and
                    // centered (tablets, mid-size windows); on a phone this changes nothing.
                    PhoneColumnWhen(!wide) { ScreenContent(controller) }
                }
            }
            RequestOverlay(
                busy = controller.busy,
                error = controller.error,
                onDismiss = controller::dismissError,
                onRestart = controller::reset,
            )
        }
    }
}

@Composable
private fun ScreenContent(controller: TournamentController) {
    val squad = controller.squad
    val draw = controller.draw
    val history = controller.history
    val next = controller.next

    when (controller.screen) {
        Screen.HOME -> HomeScreen(
            onClassic = controller::openTeamSelection,
            singlePlayerWins = controller.cupsWon,
            inProgressSquad = controller.inProgress?.squadName,
            onResume = controller::resumeTournament,
        )

        Screen.TEAM_SELECTION -> TeamSelectionScreen(
            teams = controller.squads,
            onNext = controller::selectSquad,
            onReload = controller::loadSquads,
            onBack = controller::back,
        )

        Screen.SQUAD_BUILDER -> squad?.let {
            SquadBuilderScreen(
                team = it,
                pool = controller.players,
                presets = controller.presets,
                initialSelection = controller.callUp,
                onPreset = controller::applyPreset,
                onNext = controller::confirmCallUp,
                onBack = controller::back,
                onReset = controller::reset,
            )
        }

        Screen.DRAW_SETUP -> squad?.let {
            DrawSetupScreen(
                team = it,
                draw = draw,
                onDraw = controller::runDraw,
                onNext = controller::openLineup,
                // The server refuses a new call-up once the groups are drawn.
                onBack = if (draw == null) controller::back else null,
                onReset = controller::reset,
            )
        }

        Screen.PRE_MATCH -> {
            val match = (next as? NextStep.Play)?.match
            val availability = controller.availability
            if (squad != null && match != null && availability != null) {
                PreMatchLineupScreen(
                    team = squad,
                    match = match,
                    availability = availability,
                    lineup = controller.lineup,
                    formKey = controller.formKey,
                    onLineupChange = { controller.lineup = it },
                    onFormKeyChange = { controller.formKey = it },
                    onNext = controller::playMatch,
                    onBack = controller::back,
                    onReset = controller::reset,
                )
            }
        }

        Screen.MATCH_RESULT -> {
            val match = controller.lastMatch
            if (squad != null && match != null && next != null) {
                MatchResultScreen(
                    team = squad,
                    match = match,
                    next = next,
                    onNext = controller::continueAfterMatch,
                    onReset = controller::reset,
                )
            }
        }

        Screen.GROUP_STAGE -> if (draw != null && history != null && next != null) {
            GroupStageScreen(
                draw = draw,
                history = history,
                next = next,
                onPlayNext = controller::openLineup,
                onDrawPlayoffs = controller::drawPlayoffs,
                onSimulateRest = controller::simulateRest,
                onReset = controller::reset,
            )
        }

        Screen.BRACKET -> if (squad != null && history != null && next != null) {
            TournamentBracketScreen(
                team = squad,
                history = history,
                next = next,
                onAdvance = controller::openLineup,
                onReset = controller::reset,
            )
        }

        Screen.ELIMINATION -> if (squad != null && history != null && next != null) {
            EliminationScreen(
                team = squad,
                history = history,
                next = next,
                onPlayThird = controller::openLineup,
                onSimulateRest = controller::simulateRest,
                onReset = controller::reset,
            )
        }

        Screen.PHASE_OVERVIEW -> if (squad != null && history != null) {
            PhaseOverviewScreen(team = squad, history = history, onReset = controller::reset)
        }
    }
}

@Composable
private fun PhoneColumnWhen(condition: Boolean, content: @Composable () -> Unit) {
    if (condition) WideNarrowColumn(content) else content()
}

/** Navbar step for a screen; matches during the group phase count as "Grupos". */
private fun tournamentStep(screen: Screen, controller: TournamentController): TournamentStep? = when (screen) {
    Screen.HOME -> null
    Screen.TEAM_SELECTION -> TournamentStep.TEAM
    Screen.SQUAD_BUILDER -> TournamentStep.SQUAD
    Screen.DRAW_SETUP -> TournamentStep.DRAW
    Screen.GROUP_STAGE -> TournamentStep.GROUPS
    Screen.PRE_MATCH, Screen.MATCH_RESULT -> {
        val stage = if (screen == Screen.MATCH_RESULT) {
            controller.lastMatch?.stage
        } else {
            (controller.next as? NextStep.Play)?.match?.stage
        }
        if (stage == Stage.GROUP) TournamentStep.GROUPS else TournamentStep.KNOCKOUT
    }
    Screen.BRACKET, Screen.ELIMINATION, Screen.PHASE_OVERVIEW -> TournamentStep.KNOCKOUT
}
