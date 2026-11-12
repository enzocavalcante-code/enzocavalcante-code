"""Gera os cartões de estatísticas do perfil (assets/stats.svg e assets/langs.svg).

Roda no GitHub Actions e busca os dados pela API do GitHub, então não depende de
nenhum serviço externo. Cartões em preto e branco.

Variáveis de ambiente:
  GITHUB_TOKEN  token do Actions (já vem pronto no workflow)
  GH_USER       usuário do GitHub (o workflow usa o dono do repositório)
"""
import json
import os
import sys
import urllib.request
from html import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

FONT = "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif\""
BG, BORDER, WHITE, GREY, DIM = "#0A0A0A", "#2A2A2A", "#FFFFFF", "#8A8A8A", "#262626"
W, H = 440, 190


def fetch(user, token):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "stats-cards-action"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"Erro da API do GitHub: {data['errors']}")
    return data["data"]["user"]


def card(title, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="6" fill="{BG}" stroke="{BORDER}"/>'
            f'<text x="24" y="38" {FONT} font-size="17" font-weight="600" fill="{WHITE}">{escape(title)}</text>'
            f'{inner}</svg>')


def stats_svg(u):
    cc = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [
        ("Total Stars Earned", stars),
        ("Total Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Total PRs", u["pullRequests"]["totalCount"]),
        ("Total Issues", u["issues"]["totalCount"]),
        ("Contributed to (last year)", u["repositoriesContributedTo"]["totalCount"]),
    ]
    out = []
    for i, (label, value) in enumerate(rows):
        y = 72 + i * 25
        out.append(f'<circle cx="28" cy="{y-4}" r="3" fill="{WHITE}"/>')
        out.append(f'<text x="40" y="{y}" {FONT} font-size="13" font-weight="600" fill="{GREY}">{label}:</text>')
        out.append(f'<text x="230" y="{y}" {FONT} font-size="13" font-weight="700" fill="{WHITE}">{value}</text>')
    total = cc["contributionCalendar"]["totalContributions"]
    cx, cy, r = 360, 108, 44
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{DIM}" stroke-width="7"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{WHITE}" stroke-width="7"/>')
    out.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" {FONT} font-size="22" font-weight="700" fill="{WHITE}">{total}</text>')
    out.append(f'<text x="{cx}" y="{cy+r+22}" text-anchor="middle" {FONT} font-size="11" fill="{GREY}">contributions</text>')
    name = u.get("name") or u["login"]
    return card(f"{name}'s GitHub Stats", "".join(out))


def langs_svg(u):
    sizes = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:8]
    total = sum(v for _, v in top) or 1
    shades = ["#FFFFFF", "#D4D4D4", "#A8A8A8", "#7C7C7C", "#5A5A5A", "#444444", "#333333", "#262626"]
    out = []
    x0, bw, by = 24, W - 48, 58
    out.append(f'<clipPath id="bar"><rect x="{x0}" y="{by}" width="{bw}" height="10" rx="5"/></clipPath>')
    out.append(f'<rect x="{x0}" y="{by}" width="{bw}" height="10" rx="5" fill="{DIM}"/><g clip-path="url(#bar)">')
    x = x0
    for i, (_, v) in enumerate(top):
        w = bw * v / total
        out.append(f'<rect x="{x:.2f}" y="{by}" width="{w+0.5:.2f}" height="10" fill="{shades[i]}"/>')
        x += w
    out.append("</g>")
    for i, (name, v) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 24 + col * 200, 98 + row * 24
        out.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{shades[i]}" stroke="{BORDER}"/>')
        out.append(f'<text x="{lx+16}" y="{ly}" {FONT} font-size="12" fill="{GREY}">'
                   f'<tspan fill="{WHITE}" font-weight="600">{escape(name)}</tspan> {100*v/total:.1f}%</text>')
    if not top:
        out.append(f'<text x="24" y="104" {FONT} font-size="12" fill="{GREY}">Nenhuma linguagem encontrada ainda.</text>')
    return card("Most Used Languages", "".join(out))


def main():
    user = os.environ.get("GH_USER")
    token = os.environ.get("GITHUB_TOKEN")
    out_dir = os.environ.get("OUT_DIR", "assets")
    if os.environ.get("SAMPLE"):                      # só para testes locais
        data = json.loads(os.environ["SAMPLE"])
    else:
        if not user or not token:
            sys.exit("Defina GH_USER e GITHUB_TOKEN.")
        data = fetch(user, token)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open(os.path.join(out_dir, "langs.svg"), "w", encoding="utf-8") as f:
        f.write(langs_svg(data))
    print("Cartões gerados.")


if __name__ == "__main__":
    main()
