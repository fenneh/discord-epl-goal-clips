"""Competition registry. Each competition drives a parallel pipeline:
team matching, ESPN fixture polling, deduplication scope, Discord embed branding."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    id: str
    name: str
    espn_league: str
    color: int
    logo: str
    schedule_title: str


EPL = Competition(
    id="epl",
    name="Premier League",
    espn_league="epl",
    color=0x37003C,
    logo="https://resources.premierleague.com/premierleague/competitions/competition_1_small.png",
    schedule_title="Premier League",
)

WORLD_CUP_2026 = Competition(
    id="world_cup_2026",
    name="FIFA World Cup 2026",
    espn_league="world_cup",
    color=0xE53935,
    logo="https://a.espncdn.com/i/leaguelogos/soccer/500/4.png",
    schedule_title="World Cup",
)


_REGISTRY: dict[str, Competition] = {
    EPL.id: EPL,
    WORLD_CUP_2026.id: WORLD_CUP_2026,
}


def list_competitions() -> list[Competition]:
    return list(_REGISTRY.values())


def get_competition(comp_id: str) -> Competition:
    return _REGISTRY[comp_id]
