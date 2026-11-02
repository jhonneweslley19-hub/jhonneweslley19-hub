#!/usr/bin/env python3
"""contribution_heatmap.py — gera um heatmap SVG estático (sempre colorido,
sem animação) a partir do calendário real de contribuições do GitHub, via
GraphQL. Pensado pra complementar a cobrinha (que só mostra cada quadrado
colorido por um instante, quando é "comido").

Uso:
    GH_TOKEN=... python3 scripts/contribution_heatmap.py --username <user> \
        --out-light assets/contribution-heatmap.svg \
        --out-dark assets/contribution-heatmap-dark.svg
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

CELL = 11
GAP = 3
PITCH = CELL + GAP
MARGIN = 2

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            color
            weekday
          }
        }
      }
    }
  }
}
"""

# Paleta padrão que o GitHub usa no tema claro — é o que a API devolve em
# `color`, então usamos pra descobrir o nível (0-4) de cada dia.
LIGHT_LEVELS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
DARK_LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def fetch_calendar(username: str, token: str, year: int):
    from_date = f"{year}-01-01T00:00:00Z"
    to_date = f"{year}-12-31T23:59:59Z"
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(
            {
                "query": QUERY,
                "variables": {"login": username, "from": from_date, "to": to_date},
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "contribution-heatmap-script",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"Erro na API do GitHub: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


def level_from_color(color: str) -> int:
    try:
        return LIGHT_LEVELS.index(color.lower())
    except ValueError:
        return 0


def build_svg(weeks, levels) -> str:
    cols = len(weeks)
    width = cols * PITCH + MARGIN * 2 - GAP
    height = 7 * PITCH + MARGIN * 2 - GAP

    cells = []
    for col, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = day["weekday"]
            level = level_from_color(day["color"])
            x = MARGIN + col * PITCH
            y = MARGIN + row * PITCH
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{levels[level]}"/>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'<desc>Heatmap real de contribuições</desc>'
        + "".join(cells)
        + "</svg>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--out-light", required=True)
    parser.add_argument("--out-dark", required=True)
    parser.add_argument(
        "--year", type=int, default=datetime.date.today().year,
        help="Ano civil a buscar (padrão: ano atual)",
    )
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Defina a variável de ambiente GH_TOKEN com um token de leitura.")

    weeks = fetch_calendar(args.username, token, args.year)

    for out_path in (args.out_light, args.out_dark):
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    with open(args.out_light, "w") as f:
        f.write(build_svg(weeks, LIGHT_LEVELS))
    with open(args.out_dark, "w") as f:
        f.write(build_svg(weeks, DARK_LEVELS))


if __name__ == "__main__":
    main()
