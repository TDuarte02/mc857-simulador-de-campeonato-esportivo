"""Dataset carregado uma vez: pool por nação, seleções-base e validação do elenco."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from python_prototype.collective_attributes import SECTORS
from python_prototype.tournament import (
    DatasetReport,
    NationalTeam,
    SetupError,
    SquadMember,
    TournamentConfig,
    _rank,
    _unique_names,
    build_national_team,
    read_players_csv,
)

from .errors import ApiError
from .names import NATIONS, slug

# Mínimos entre os jogadores de linha para suportar as 4 formações do app
# (máximos: 4 DEF, 5 MID, 3 FW). CRITÉRIO A CONFIRMAR (ver Issue #41).
MIN_DEFENDERS, MIN_MIDFIELDERS, MIN_FORWARDS = 4, 5, 3


def covers_sectors(outfield: Sequence[SquadMember]) -> bool:
    """Existe atribuição de jogadores a vagas de setor (4 DEF, 5 MID, 3 FW), um por vaga?"""
    slots = ["DEF"] * MIN_DEFENDERS + ["MID"] * MIN_MIDFIELDERS + ["FW"] * MIN_FORWARDS
    owner: dict[int, int] = {}

    def assign(slot: int, seen: set[int]) -> bool:
        for p, member in enumerate(outfield):
            if slots[slot] in member.sectors and p not in seen:
                seen.add(p)
                if p not in owner or assign(owner[p], seen):
                    owner[p] = slot
                    return True
        return False

    return all(assign(s, set()) for s in range(len(slots)))


@dataclass
class Catalog:
    config: TournamentConfig
    pools: dict[str, tuple[SquadMember, ...]]
    base_teams: dict[str, NationalTeam]
    report: DatasetReport | None = None

    @classmethod
    def from_csv(cls, path: str) -> "Catalog":
        config = TournamentConfig(dataset_path=path)
        members, report = read_players_csv(config.dataset_path, config.nations)
        return cls.from_members(members, config, report)

    @classmethod
    def from_members(
        cls,
        members: Mapping[str, Sequence[SquadMember]],
        config: TournamentConfig | None = None,
        report: DatasetReport | None = None,
    ) -> "Catalog":
        config = config or TournamentConfig()
        pools = {
            n: tuple(_unique_names(sorted(members[n], key=_rank))) for n in config.nations
        }
        base = {n: build_national_team(n, members[n], config) for n in config.nations}
        return cls(config, pools, base, report)

    # ------------------------------------------------------------------

    def resolve_nation(self, key: str) -> str:
        for nation in self.config.nations:
            if key == nation or key == slug(nation):
                return nation
        raise ApiError(404, "nation_not_found", f"Seleção desconhecida: {key!r}.")

    def nations(self) -> list[dict]:
        out = []
        for nation in self.config.nations:
            display, flag, conf = NATIONS.get(nation, (nation, "", ""))
            out.append({"id": slug(nation), "name": nation, "display_name": display,
                        "flag": flag, "confederation": conf})
        return out

    def rules(self) -> dict:
        c = self.config
        return {
            "size": c.squad_size, "goalkeepers": c.squad_goalkeepers,
            "outfield": c.squad_size - c.squad_goalkeepers,
            "min_defenders": MIN_DEFENDERS, "min_midfielders": MIN_MIDFIELDERS,
            "min_forwards": MIN_FORWARDS,
        }

    def player_out(self, member: SquadMember) -> dict:
        p = member.player
        return {
            "name": p.name,
            "positions": list(member.positions),
            "sectors": [s for s in SECTORS if s in member.sectors],
            "overall": p.overall,
            "is_goalkeeper": member.is_goalkeeper,
            "attributes": {
                k: getattr(p, k)
                for k in ("pace", "shooting", "passing", "dribbling", "defending",
                          "physic", "goalkeeping_reflexes")
            },
        }

    def build_user_team(
        self, nation: str, names: Sequence[str], config: TournamentConfig
    ) -> NationalTeam:
        def bad(msg: str) -> ApiError:
            return ApiError(422, "invalid_squad", msg)

        if len(names) != config.squad_size:
            raise bad(f"O elenco deve ter exatamente {config.squad_size} jogadores; recebido: {len(names)}.")
        if len(set(names)) != len(names):
            raise bad("O elenco não pode ter jogadores repetidos.")
        pool = {m.player.name: m for m in self.pools[nation]}
        unknown = [n for n in names if n not in pool]
        if unknown:
            raise bad(f"Jogadores fora do pool de {nation}: {unknown}.")
        selected = [pool[n] for n in names]
        keepers = sum(m.is_goalkeeper for m in selected)
        if keepers != config.squad_goalkeepers:
            raise bad(f"O elenco deve ter {config.squad_goalkeepers} goleiros; recebido: {keepers}.")
        if not covers_sectors([m for m in selected if not m.is_goalkeeper]):
            raise bad(
                f"Setores insuficientes: são necessários ao menos {MIN_DEFENDERS} defensores, "
                f"{MIN_MIDFIELDERS} meio-campistas e {MIN_FORWARDS} atacantes entre os de linha."
            )
        try:
            return build_national_team(nation, selected, config)
        except SetupError as exc:
            raise bad(str(exc)) from exc
