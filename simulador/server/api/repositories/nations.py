"""The 16 nations of the cup, pinned: squad id, name in the dataset, display name, flag and federation.

Squad ids are the API's (the app keeps them), so they stay as they were: `usa`,
not `united_states`. Canada replaces Haiti, which is not in the 2024 Copa
América. `dataset_name` is the `nationality_name` the data pipeline writes.
"""

from dataclasses import dataclass

from api.domain.models import Federation

_CONMEBOL, _CONCACAF = Federation.CONMEBOL, Federation.CONCACAF


@dataclass(frozen=True)
class Nation:
    id: str
    dataset_name: str
    name: str  # display name, in Portuguese
    iso: str  # ISO 3166 code, for the flag
    federation: Federation

    @property
    def flag(self) -> str:
        return f"https://flagcdn.com/w320/{self.iso}.png"


NATIONS: tuple[Nation, ...] = (
    Nation("argentina", "Argentina", "Argentina", "ar", _CONMEBOL),
    Nation("bolivia", "Bolivia", "Bolívia", "bo", _CONMEBOL),
    Nation("brazil", "Brazil", "Brasil", "br", _CONMEBOL),
    Nation("colombia", "Colombia", "Colômbia", "co", _CONMEBOL),
    Nation("chile", "Chile", "Chile", "cl", _CONMEBOL),
    Nation("ecuador", "Ecuador", "Equador", "ec", _CONMEBOL),
    Nation("paraguay", "Paraguay", "Paraguai", "py", _CONMEBOL),
    Nation("venezuela", "Venezuela", "Venezuela", "ve", _CONMEBOL),
    Nation("uruguay", "Uruguay", "Uruguai", "uy", _CONMEBOL),
    Nation("usa", "United States", "Estados Unidos", "us", _CONCACAF),
    Nation("mexico", "Mexico", "México", "mx", _CONCACAF),
    Nation("costa_rica", "Costa Rica", "Costa Rica", "cr", _CONCACAF),
    Nation("panama", "Panama", "Panamá", "pa", _CONCACAF),
    Nation("canada", "Canada", "Canadá", "ca", _CONCACAF),
    Nation("jamaica", "Jamaica", "Jamaica", "jm", _CONCACAF),
    Nation("peru", "Peru", "Peru", "pe", _CONMEBOL),
)

BY_ID: dict[str, Nation] = {nation.id: nation for nation in NATIONS}
BY_DATASET_NAME: dict[str, Nation] = {nation.dataset_name: nation for nation in NATIONS}
