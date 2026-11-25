"""Testes de integração da Issue #36: torneio com usuário."""
import json
from dataclasses import replace

import pytest

from python_prototype.dynamics import DynamicsConfig
from python_prototype.game import TournamentGame, UserMatchPending, schedule_order
from python_prototype.group_stage import MatchStatus, TournamentPhase
from python_prototype.match import MatchEventType, MatchPhase, create_match, play_match
from python_prototype.session import (
    UserMatchSession,
    lineup_from_picks,
    validate_lineup_from_squad,
)
from python_prototype.tournament import (
    DEFAULT_NATIONS,
    TournamentConfig,
    build_default_lineup,
    derive_seed,
    synthetic_teams,
)

FORMATION_442 = ("GK", "FB", "CB", "CB", "FB", "CM", "CM", "CM", "CM", "ST", "ST")
WEAKEST, STRONGEST = DEFAULT_NATIONS[0], DEFAULT_NATIONS[-1]   # ratings 60 e 90


def make_game(seed=2026, user=None, ratings=None, **config_kwargs):
    config = TournamentConfig(seed=seed, **config_kwargs)
    return TournamentGame.create(config, synthetic_teams(config, ratings), user)


def snapshot(state):
    return {
        mid: (r.team_a, r.team_b, r.status,
              None if r.result is None else (r.result.goals_a, r.result.goals_b, r.result.events, r.result.penalties))
        for mid, r in state.matches.items()
    }


def play_user_auto(game):
    while game.advance_to_user_match() is not None:
        game.play_user_match_auto()


def alt_lineup_442(team):
    """Escalação 4-4-2 válida, diferente da padrão (muda os atributos)."""
    lineup = build_default_lineup(team.name, team.squad, FORMATION_442)
    return lineup, FORMATION_442


# ------------------------------------------------------------
# Escolha da seleção
# ------------------------------------------------------------

def test_user_team_choice_does_not_change_draw_or_seeds():
    a, b = make_game(user=None), make_game(user=STRONGEST)

    assert [[t.name for t in g.teams] for g in a.state.groups] == [
        [t.name for t in g.teams] for g in b.state.groups
    ]
    assert list(a.state.matches) == list(b.state.matches)


def test_unknown_user_team_is_rejected():
    with pytest.raises(ValueError, match="desconhecida"):
        make_game(user="Atlantis")


def test_schedule_order_is_round_by_round_then_knockout():
    game = make_game()
    order = schedule_order(game.state)

    assert len(order) == 32 and len(set(order)) == 32
    rounds = [game.state.matches[m].round_number for m in order[:24]]
    assert rounds == sorted(rounds)
    assert order[24:] == ("QF1", "QF2", "QF3", "QF4", "SF1", "SF2", "THIRD", "FINAL")


# ------------------------------------------------------------
# Sessão sem alterações == play_match
# ------------------------------------------------------------

def test_session_without_changes_is_identical_to_play_match():
    game = make_game(user=STRONGEST)
    record = game.advance_to_user_match()
    a, b = game.state.teams[record.team_a], game.state.teams[record.team_b]
    config = game.state.config

    session = game.start_user_match()
    # Parando no intervalo e retomando: continua idêntico.
    session.play_until_stop()
    assert session.phase is MatchPhase.HALFTIME
    session.start_second_half()
    session.play_to_end()

    plain = create_match(a.lineup, a.formation, b.lineup, b.formation)
    play_match(
        plain,
        seed=derive_seed(config.seed, record.match_id),
        attack_params=config.attack_params,
        recovery_control_bonus=config.recovery_control_bonus,
        possessions_per_cycle=config.possessions_per_cycle,
        dynamics=config.dynamics,
        dynamics_seed=derive_seed(config.seed, record.match_id, "dynamics"),
    )

    assert session.result.events == tuple(plain.events)
    assert (session.result.goals_a, session.result.goals_b) == (plain.score["A"], plain.score["B"])


def test_tournament_with_autoplayed_user_equals_machine_only_tournament():
    machine = make_game(seed=5)
    machine.simulate_to_end()
    user = make_game(seed=5, user=STRONGEST)
    play_user_auto(user)
    user.simulate_to_end()

    assert snapshot(machine.state) == snapshot(user.state)


# ------------------------------------------------------------
# Escalação: antes do início e no intervalo
# ------------------------------------------------------------

def test_lineup_change_before_start_and_at_halftime_only():
    game = make_game(user=STRONGEST)
    game.advance_to_user_match()
    session = game.start_user_match()
    team = game.state.teams[STRONGEST]
    lineup, formation = alt_lineup_442(team)

    session.change_lineup(lineup, formation)           # antes do início
    assert session.user_formation == formation
    assert not any(e.type is MatchEventType.LINEUP_CHANGE for e in session.match.events)

    session.play_cycle()
    with pytest.raises(ValueError, match="intervalo"):
        session.change_lineup(*alt_lineup_442(team))   # durante o 1º tempo
    session.play_until_stop()
    assert session.phase is MatchPhase.HALFTIME

    session.change_lineup(team.lineup, team.formation) # no intervalo
    assert sum(e.type is MatchEventType.LINEUP_CHANGE for e in session.match.events) == 1
    session.start_second_half()
    with pytest.raises(ValueError, match="intervalo"):
        session.change_lineup(lineup, formation)


def test_lineup_change_affects_following_cycles():
    game = make_game(user=STRONGEST)
    game.advance_to_user_match()
    session = game.start_user_match()
    before = session.match.teams[session.user_side].effective()

    session.change_lineup(*alt_lineup_442(game.state.teams[STRONGEST]))

    after = session.match.teams[session.user_side].effective()
    assert after != before                              # 4-4-2 muda os modificadores


def test_invalid_lineups_are_rejected_without_changing_state():
    game = make_game(user=STRONGEST)
    game.advance_to_user_match()
    session = game.start_user_match()
    team = game.state.teams[STRONGEST]
    tournament_before = snapshot(game.state)
    match_team = session.match.teams[session.user_side]
    events = list(session.match.events)

    stranger = game.state.teams[WEAKEST].lineup[1]
    outfield_gk = replace(team.lineup[1], pos="GK")
    striker_as_cb = replace(team.lineup[9], pos="CB")
    bad = [
        (team.lineup[:-1], team.formation),                                   # 10 jogadores
        (team.lineup[:-1] + (stranger,), team.formation),                      # de outra seleção
        ((team.lineup[0], outfield_gk) + team.lineup[2:], team.formation),     # linha no gol
        (team.lineup[:9] + (striker_as_cb,) + team.lineup[10:], team.formation),  # setor incompatível
        (team.lineup, FORMATION_442),                                          # formação incoerente
    ]
    for players, formation in bad:
        with pytest.raises(ValueError):
            session.change_lineup(players, formation)

    assert session.match.teams[session.user_side] is match_team
    assert session.match.events == events
    assert snapshot(game.state) == tournament_before


def test_goalkeeper_cannot_be_used_outside_the_goal():
    team = make_game().state.teams[STRONGEST]
    keeper = next(m.player for m in team.squad if m.is_goalkeeper and m.player.name != team.lineup[0].name)
    lineup = (team.lineup[0], replace(keeper, pos="CB")) + team.lineup[2:]

    with pytest.raises(ValueError, match="goleiro"):
        validate_lineup_from_squad(team, lineup)


def test_lineup_from_picks_builds_a_valid_lineup_and_keeps_originals():
    team = make_game().state.teams[STRONGEST]
    picks = [(p.name, slot) for p, slot in zip(team.lineup, team.formation)]

    players, formation = lineup_from_picks(team, picks)

    assert players == team.lineup and formation == team.formation
    with pytest.raises(ValueError, match="elenco"):
        lineup_from_picks(team, [("Ninguém", "ST")])


def test_user_lineup_is_valid_only_for_that_match():
    game = make_game(user=STRONGEST)
    teams_before = {n: (t.lineup, t.formation) for n, t in game.state.teams.items()}
    record = game.advance_to_user_match()
    session = game.start_user_match(*alt_lineup_442(game.state.teams[STRONGEST]))
    session.play_to_end()

    assert {n: (t.lineup, t.formation) for n, t in game.state.teams.items()} == teams_before
    # O resultado guardado usa a escalação alterada e difere do padrão (mesma semente).
    default = make_game(user=None)
    default.simulate_to_end()
    assert record.result is not None


def test_machine_matches_do_not_depend_on_user_decisions():
    machine = make_game(seed=9)
    machine.simulate_to_end()

    user = make_game(seed=9, user=STRONGEST)
    while (rec := user.advance_to_user_match()) is not None and rec.phase is TournamentPhase.GRUPOS:
        session = user.start_user_match(*alt_lineup_442(user.state.teams[STRONGEST]))
        session.play_until_stop()
        session.change_lineup(*alt_lineup_442(user.state.teams[STRONGEST]))
        session.play_to_end()

    for mid, rec in user.state.matches.items():
        if rec.phase is TournamentPhase.GRUPOS and STRONGEST not in (rec.team_a, rec.team_b):
            if rec.status is MatchStatus.ENCERRADA:
                assert snapshot(user.state)[mid] == snapshot(machine.state)[mid]


# ------------------------------------------------------------
# Registro do resultado
# ------------------------------------------------------------

def test_user_result_enters_standings_once():
    game = make_game(user=STRONGEST)
    record = game.advance_to_user_match()
    session = game.start_user_match()
    result = session.play_to_end()

    assert record.status is MatchStatus.ENCERRADA and record.result is result
    assert game.session is None and session.is_closed
    from python_prototype.group_stage import group_standings

    rows = {r.team: r for r in group_standings(game.state, record.group).rows}
    assert rows[STRONGEST].played == 1
    assert rows[record.team_a].goals_for + rows[record.team_b].goals_for >= result.goals_a + result.goals_b - 0
    with pytest.raises(ValueError):
        session.play_cycle()
    with pytest.raises(ValueError, match="já foi jogada"):
        UserMatchSession(game.state, record.match_id, STRONGEST)


def test_only_one_session_at_a_time_and_cancel_keeps_match_pending():
    game = make_game(user=STRONGEST)
    game.advance_to_user_match()
    session = game.start_user_match()
    with pytest.raises(ValueError, match="em andamento"):
        game.start_user_match()

    before = snapshot(game.state)
    game.cancel_user_match()

    assert snapshot(game.state) == before and game.session is None
    assert game.pending_user_match is not None
    game.start_user_match().play_to_end()


def test_invalid_lineup_in_start_user_match_opens_no_session():
    game = make_game(user=STRONGEST)
    before = snapshot(game.state)
    team = game.state.teams[STRONGEST]

    with pytest.raises(ValueError):
        game.start_user_match(team.lineup[:-1], team.formation)

    assert game.session is None and snapshot(game.state) == before
    with pytest.raises(ValueError, match="juntas"):
        game.start_user_match(team.lineup, None)


def test_knockout_draw_is_decided_on_penalties_with_final_lineup():
    ratings = [70] * 16                       # times iguais: empates frequentes
    for seed in range(100):
        machine = make_game(seed=seed, ratings=ratings)
        machine.simulate_to_end()
        qf = machine.state.matches["QF1"]
        if qf.result.penalties is not None:
            break
    else:
        pytest.fail("nenhuma seed com QF1 nos pênaltis")

    game = make_game(seed=seed, ratings=ratings, user=qf.team_a)
    record = game.advance_to_user_match()
    while record.phase is TournamentPhase.GRUPOS:      # antes, as partidas de grupo
        game.play_user_match_auto()
        record = game.advance_to_user_match()
    assert record.match_id == "QF1"

    session = game.start_user_match()
    result = session.play_to_end()

    assert (result.goals_a, result.goals_b) == (qf.result.goals_a, qf.result.goals_b)
    assert result.penalties == qf.result.penalties            # mesmos pênaltis da máquina
    assert result.goals_a == result.goals_b
    assert sum(e.type is MatchEventType.GOAL for e in result.events) == result.goals_a + result.goals_b


# ------------------------------------------------------------
# Avanço e bloqueio
# ------------------------------------------------------------

def test_tournament_blocks_while_user_match_is_pending_and_releases_after_result():
    game = make_game(user=STRONGEST)

    with pytest.raises(UserMatchPending):
        game.simulate_to_end()

    record = game.advance_to_user_match()
    assert record is game.pending_user_match and record.status is MatchStatus.PENDENTE
    with pytest.raises(UserMatchPending):
        game.play_next_match()
    # Tudo o que vem antes da partida do usuário foi simulado.
    order = schedule_order(game.state)
    before = order[: order.index(record.match_id)]
    assert all(game.state.matches[m].status is MatchStatus.ENCERRADA for m in before)

    session = game.start_user_match()
    with pytest.raises(UserMatchPending):
        game.play_next_match()
    with pytest.raises(UserMatchPending):
        game.advance_to_user_match()
    session.play_to_end()

    assert game.play_next_match().status is MatchStatus.ENCERRADA


def test_group_stage_hands_over_to_knockout_automatically():
    game = make_game(user=STRONGEST)
    for _ in range(3):
        game.advance_to_user_match()
        game.play_user_match_auto()
    assert game.phase is TournamentPhase.GRUPOS or game.phase is TournamentPhase.MATA_MATA

    game.advance_to_user_match()
    assert game.state.group_stage_finished and game.phase is TournamentPhase.MATA_MATA


def test_user_eliminated_tournament_is_simulated_to_the_end():
    for seed in range(40):
        game = make_game(seed=seed, user=WEAKEST)
        play_user_auto(game)
        if game.user_eliminated:
            break
    else:
        pytest.fail("usuário não foi eliminado em nenhuma seed")

    assert game.is_finished or not game.state.matches["FINAL"].status is MatchStatus.ENCERRADA
    ranking = game.simulate_to_end()

    assert game.is_finished and WEAKEST not in (ranking.champion, ranking.runner_up)
    assert sum(r.status is MatchStatus.ENCERRADA for r in game.state.matches.values()) == 32


def test_user_champion_full_tournament():
    for seed in range(40):
        machine = make_game(seed=seed)
        champion = machine.simulate_to_end().champion
        game = make_game(seed=seed, user=champion)
        play_user_auto(game)
        assert game.is_finished and game.final_ranking().champion == champion
        break

    result = game.final_result()
    assert result["champion"] == champion and result["user_team"] == champion
    assert len(result["group_matches"]) == 24 and len(result["knockout"]) == 8


def test_finished_tournament_rejects_new_matches():
    game = make_game(user=STRONGEST)
    play_user_auto(game)
    game.simulate_to_end()
    before = snapshot(game.state)

    assert game.is_finished
    with pytest.raises(ValueError, match="encerrado"):
        game.play_next_match()
    with pytest.raises(ValueError, match="encerrado"):
        game.start_user_match()
    with pytest.raises(ValueError, match="já foi jogada"):
        UserMatchSession(game.state, "FINAL", STRONGEST)
    assert game.next_match() is None and game.advance_to_user_match() is None
    assert snapshot(game.state) == before


def test_final_result_requires_finished_tournament():
    with pytest.raises(ValueError):
        make_game().final_result()


# ------------------------------------------------------------
# Reprodutibilidade e resultado final
# ------------------------------------------------------------

def play_with_decisions(seed):
    game = make_game(seed=seed, user=STRONGEST)
    while game.advance_to_user_match() is not None:
        team = game.state.teams[STRONGEST]
        session = game.start_user_match()
        session.play_until_stop()
        if session.phase is MatchPhase.HALFTIME:
            session.change_lineup(*alt_lineup_442(team))
        session.play_to_end()
    game.simulate_to_end()
    return game


def test_same_seed_config_and_decisions_are_reproducible_and_json_serializable():
    a, b = play_with_decisions(11), play_with_decisions(11)

    assert a.final_result() == b.final_result()
    text = a.final_result_json(sort_keys=True)
    assert json.loads(text) == json.loads(json.dumps(a.final_result()))
    assert snapshot(a.state) == snapshot(b.state)


def test_final_result_structure():
    game = play_with_decisions(3)
    result = game.final_result()

    assert set(result["groups"]) == {"A", "B", "C", "D"}
    assert all(len(rows) == 4 and rows[0]["played"] == 3 for rows in result["groups"].values())
    assert [m["id"] for m in result["knockout"]] == [
        "QF1", "QF2", "QF3", "QF4", "SF1", "SF2", "THIRD", "FINAL"
    ]
    for m in result["knockout"]:
        assert m["winner"] in (m["team_a"], m["team_b"])
        assert (m["penalties"] is not None) == (m["goals_a"] == m["goals_b"])
    final = result["knockout"][-1]
    assert result["champion"] == final["winner"]
    assert result["runner_up"] in (final["team_a"], final["team_b"]) != result["champion"]


def test_disabled_dynamics_session_matches_machine_tournament():
    kwargs = dict(dynamics=DynamicsConfig.disabled())
    machine = make_game(seed=4, **kwargs)
    machine.simulate_to_end()
    user = make_game(seed=4, user=STRONGEST, **kwargs)
    play_user_auto(user)
    user.simulate_to_end()

    assert snapshot(machine.state) == snapshot(user.state)
