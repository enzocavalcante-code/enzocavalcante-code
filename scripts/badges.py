"""Gera os botões das redes sociais (assets/badge-*.svg).

Cada botão é uma caixinha escura com o símbolo do aplicativo em branco à
esquerda e o nome em letras maiúsculas espaçadas. Os símbolos vêm da biblioteca
Simple Icons (versão 11, que ainda inclui o LinkedIn).
"""
import os
import re
import sys
import urllib.request

ICONS_URL = "https://cdn.jsdelivr.net/npm/simple-icons@11/icons/{slug}.svg"

# (arquivo, símbolo na Simple Icons, texto do botão)
BADGES = [
    ("github", "github", "GITHUB"),
    ("linkedin", "linkedin", "LINKEDIN"),
    ("gmail", "gmail", "GMAIL"),
]

H = 30            # altura do botão
ICON = 14         # tamanho do símbolo
PAD = 12          # margem lateral
GAP = 9           # espaço entre símbolo e texto
CHAR = 8.4        # largura média por letra (10px negrito + espaçamento)


def icon_path(slug):
    if os.environ.get("SAMPLE_ICON"):                 # só para testes locais
        return os.environ["SAMPLE_ICON"]
    req = urllib.request.Request(ICONS_URL.format(slug=slug), headers={"User-Agent": "badges-action"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        svg = resp.read().decode()
    m = re.search(r'<path[^>]*\sd="([^"]+)"', svg)
    if not m:
        sys.exit(f"Não encontrei o símbolo de {slug}.")
    return m.group(1)


def badge(label, path_d):
    text_w = round(len(label) * CHAR)
    tx = PAD + ICON + GAP
    W = tx + text_w + PAD
    s = ICON / 24                                     # os símbolos têm 24x24
    iy = (H - ICON) / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="4" fill="#0A0A0A" stroke="#2A2A2A"/>'
        f'<path transform="translate({PAD} {iy}) scale({s})" d="{path_d}" fill="#FFFFFF"/>'
        f'<text x="{tx}" y="{H/2 + 3.6}" textLength="{text_w}" lengthAdjust="spacing" '
        f'font-family="Verdana, \'DejaVu Sans\', Geneva, sans-serif" font-size="10" font-weight="700" '
        f'fill="#FFFFFF">{label}</text>'
        f'</svg>'
    )


def main():
    out_dir = os.environ.get("OUT_DIR", "assets")
    os.makedirs(out_dir, exist_ok=True)
    for name, slug, label in BADGES:
        with open(os.path.join(out_dir, f"badge-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(badge(label, icon_path(slug)))
    print("Botões gerados.")


if __name__ == "__main__":
    main()
