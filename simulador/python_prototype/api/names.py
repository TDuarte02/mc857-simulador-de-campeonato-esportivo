"""Nomes de exibição (PT-BR), bandeira e confederação das 16 nações do motor."""

NATIONS: dict[str, tuple[str, str, str]] = {
    "Argentina": ("Argentina", "🇦🇷", "CONMEBOL"),
    "Canada": ("Canadá", "🇨🇦", "CONCACAF"),
    "Peru": ("Peru", "🇵🇪", "CONMEBOL"),
    "Chile": ("Chile", "🇨🇱", "CONMEBOL"),
    "Mexico": ("México", "🇲🇽", "CONCACAF"),
    "Ecuador": ("Equador", "🇪🇨", "CONMEBOL"),
    "Venezuela": ("Venezuela", "🇻🇪", "CONMEBOL"),
    "Jamaica": ("Jamaica", "🇯🇲", "CONCACAF"),
    "United States": ("Estados Unidos", "🇺🇸", "CONCACAF"),
    "Uruguay": ("Uruguai", "🇺🇾", "CONMEBOL"),
    "Panama": ("Panamá", "🇵🇦", "CONCACAF"),
    "Bolivia": ("Bolívia", "🇧🇴", "CONMEBOL"),
    "Brazil": ("Brasil", "🇧🇷", "CONMEBOL"),
    "Colombia": ("Colômbia", "🇨🇴", "CONMEBOL"),
    "Paraguay": ("Paraguai", "🇵🇾", "CONMEBOL"),
    "Costa Rica": ("Costa Rica", "🇨🇷", "CONCACAF"),
}


def slug(name: str) -> str:
    return name.lower().replace(" ", "_")
