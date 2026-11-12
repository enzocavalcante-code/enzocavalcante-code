"""Gera o gráfico de atividade do perfil (assets/activity-dark.svg e activity-light.svg).

Roda dentro do GitHub Actions: busca as contribuições dos últimos 31 dias pela
API do GitHub e desenha um gráfico de linha no estilo do README.

Variáveis de ambiente:
  GITHUB_TOKEN  token do Actions (já vem pronto no workflow)
  GH_USER       usuário do GitHub (o workflow usa o dono do repositório)
"""
import json
import os
import sys
import urllib.request
from datetime import date
from html import escape

DAYS = 31

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

THEMES = {
    "dark": {"bg": "#0A0A0A", "title": "#FFFFFF", "text": "#8A8A8A", "grid": "#262626",
             "line": "#FFFFFF", "point": "#FFFFFF"},
    "light": {"bg": "#FFFFFF", "title": "#000000", "text": "#555555", "grid": "#E5E5E5",
              "line": "#000000", "point": "#000000"},
}


def fetch_days(user, token):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "activity-graph-action"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"Erro da API do GitHub: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    days.sort()
    return days[-DAYS:]


def nice_max(value):
    """Arredonda o topo do eixo para um número 'bonito' com 5 divisões."""
    if value <= 5:
        return 5
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if value <= step * 5:
            return step * 5
    return value


def render(user, days, theme):
    c = THEMES[theme]
    W, H = 1200, 420
    left, right, top, bottom = 80, 40, 70, 70
    pw, ph = W - left - right, H - top - bottom
    counts = [n for _, n in days]
    ymax = nice_max(max(counts) if counts else 0)
    n = len(days)

    def x(i):
        return left + (pw * i / (n - 1) if n > 1 else pw / 2)

    def y(v):
        return top + ph - ph * v / ymax

    font = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif\""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" rx="6" fill="{c["bg"]}"/>',
           f'<text x="{W/2}" y="38" text-anchor="middle" {font} font-size="20" font-weight="600" '
           f'fill="{c["title"]}">{escape(user)}\'s Contribution Graph</text>']

    # grade e eixo Y
    for k in range(6):
        v = ymax * k / 5
        yy = y(v)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{W-right}" y2="{yy:.1f}" stroke="{c["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{left-12}" y="{yy+4:.1f}" text-anchor="end" {font} font-size="12" fill="{c["text"]}">{v:g}</text>')
    for i in range(n):
        xx = x(i)
        out.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top+ph}" stroke="{c["grid"]}" stroke-width="1" opacity="0.5"/>')
        day = date.fromisoformat(days[i][0]).day
        out.append(f'<text x="{xx:.1f}" y="{top+ph+22}" text-anchor="middle" {font} font-size="12" fill="{c["text"]}">{day}</text>')

    out.append(f'<text x="{W/2}" y="{H-14}" text-anchor="middle" {font} font-size="13" fill="{c["text"]}">Days</text>')
    out.append(f'<text transform="translate(24 {top+ph/2}) rotate(-90)" text-anchor="middle" {font} font-size="13" fill="{c["text"]}">Contributions</text>')

    # área, linha e pontos
    pts = [(x(i), y(v)) for i, v in enumerate(counts)]
    if pts:
        line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        area = f"{pts[0][0]:.1f},{top+ph} {line} {pts[-1][0]:.1f},{top+ph}"
        out.append('<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
                   f'<stop offset="0" stop-color="{c["line"]}" stop-opacity="0.35"/>'
                   f'<stop offset="1" stop-color="{c["line"]}" stop-opacity="0"/></linearGradient></defs>')
        out.append(f'<polygon points="{area}" fill="url(#g)"/>')
        out.append(f'<polyline points="{line}" fill="none" stroke="{c["line"]}" stroke-width="2.5" stroke-linejoin="round"/>')
        for (px, py), (d, v) in zip(pts, days):
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{c["point"]}"><title>{d}: {v}</title></circle>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    user = os.environ.get("GH_USER")
    token = os.environ.get("GITHUB_TOKEN")
    out_dir = os.environ.get("OUT_DIR", "assets")
    if os.environ.get("SAMPLE"):                      # só para testes locais
        days = json.loads(os.environ["SAMPLE"])
    else:
        if not user or not token:
            sys.exit("Defina GH_USER e GITHUB_TOKEN.")
        days = fetch_days(user, token)
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"activity-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(user or "user", days, theme))
    print(f"Gráfico gerado com {len(days)} dias.")


if __name__ == "__main__":
    main()
