#!/usr/bin/env python3
"""Rigenera INDICE.md e Ricettario.html a partire dai file in ricette/.

Uso:  python aggiorna.py
Per aggiungere una ricetta: copia _modello.md dentro ricette/, rinominalo e compilalo.
"""
import html
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
RICETTE = BASE / "ricette"
ORDINE = ["Antipasti e salati", "Primi", "Secondi", "Contorni", "Dolci",
          "Colazione e fit", "Basi e impasti", "Conserve e marmellate",
          "Bevande e smoothie", "Altro"]


def leggi(path):
    testo = path.read_text(encoding="utf-8").lstrip("﻿")
    meta, corpo = {}, testo
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", testo, re.S)
    if m:
        for riga in m.group(1).splitlines():
            if ":" in riga:
                k, v = riga.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        corpo = m.group(2)
    sezioni, cur = {}, None
    for riga in corpo.splitlines():
        h = re.match(r"##\s+(.*)", riga)
        if h:
            cur = h.group(1).strip().lower()
            sezioni[cur] = []
        elif cur is not None:
            sezioni[cur].append(riga)
    meta["_file"] = path.name
    meta["_sez"] = {k: "\n".join(v).strip() for k, v in sezioni.items()}
    meta.setdefault("nome", path.stem.replace("-", " ").capitalize())
    meta.setdefault("categoria", "Altro")
    return meta


def righe(blocco):
    out = []
    for r in blocco.splitlines():
        r = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", r).strip()
        if r:
            out.append(r)
    return out


def sort_key(r):
    cat = r["categoria"]
    return (ORDINE.index(cat) if cat in ORDINE else len(ORDINE), r["nome"].lower())


def main():
    files = sorted(p for p in RICETTE.glob("*.md") if not p.name.startswith("_"))
    ricette = sorted((leggi(p) for p in files), key=sort_key)

    # ---- INDICE.md
    md = ["# Ricettario – Indice", "", f"Totale ricette: **{len(ricette)}**", ""]
    cat = None
    for r in ricette:
        if r["categoria"] != cat:
            cat = r["categoria"]
            md += ["", f"## {cat}", ""]
        extra = " _(da completare)_" if r.get("stato", "").lower() in ("solo nome", "parziale") else ""
        md.append(f"- [{r['nome']}](ricette/{r['_file']}){extra}")
    (BASE / "INDICE.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---- Ricettario.html
    cats = []
    for r in ricette:
        if r["categoria"] not in cats:
            cats.append(r["categoria"])
    chips = "".join(f'<button class="chip" data-cat="{html.escape(c)}">{html.escape(c)}</button>' for c in cats)
    cards = []
    for r in ricette:
        s = r["_sez"]
        ing = "".join(f"<li>{html.escape(x)}</li>" for x in righe(s.get("ingredienti", "")))
        pro = "".join(f"<li>{html.escape(x)}</li>" for x in righe(s.get("procedimento", "")))
        info = " · ".join(html.escape(x) for x in
                          [r.get("porzioni", ""), r.get("tempo", "")] if x and x.lower() != "null")
        nut = html.escape(s.get("valori nutrizionali", "")).replace("\n", "<br>")
        note = html.escape(s.get("note", "")).replace("\n", "<br>")
        badge = ""
        if r.get("stato", "").lower() in ("solo nome", "parziale"):
            badge = f'<span class="badge">{html.escape(r["stato"])}</span>'
        testo = " ".join([r["nome"], r["categoria"], s.get("ingredienti", "")]).lower()
        cards.append(f"""<details class="card" data-cat="{html.escape(r['categoria'])}" data-txt="{html.escape(testo)}">
<summary><span class="t">{html.escape(r['nome'])}</span>{badge}<span class="c">{html.escape(r['categoria'])}</span></summary>
<div class="body">
{f'<p class="info">{info}</p>' if info else ''}
{f'<h4>Ingredienti</h4><ul>{ing}</ul>' if ing else ''}
{f'<h4>Procedimento</h4><ol>{pro}</ol>' if pro else ''}
{f'<h4>Valori nutrizionali</h4><p>{nut}</p>' if nut else ''}
{f'<h4>Note</h4><p>{note}</p>' if note else ''}
</div></details>""")

    pagina = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Il mio ricettario</title>
<style>
:root{{--bg:#faf6ef;--ink:#2b2622;--mut:#7a6f64;--acc:#b5532a;--card:#fff;--line:#e6dccd}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 Georgia,'Times New Roman',serif}}
header{{padding:28px 20px 12px;max-width:820px;margin:auto}}
h1{{margin:0 0 4px;font-size:2rem;letter-spacing:-.01em}}
.sub{{color:var(--mut);margin:0 0 16px;font-family:system-ui,sans-serif;font-size:.9rem}}
#q{{width:100%;padding:12px 14px;font-size:1rem;border:1px solid var(--line);border-radius:10px;background:#fff;font-family:system-ui,sans-serif}}
#q:focus,.chip:focus-visible,summary:focus-visible{{outline:2px solid var(--acc);outline-offset:2px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0}}
.chip{{font:600 .82rem system-ui,sans-serif;padding:7px 12px;border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:999px;cursor:pointer}}
.chip.on{{background:var(--acc);color:#fff;border-color:var(--acc)}}
main{{max-width:820px;margin:8px auto 60px;padding:0 20px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:10px 0}}
summary{{list-style:none;cursor:pointer;padding:14px 16px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}
summary::-webkit-details-marker{{display:none}}
.t{{font-size:1.12rem;font-weight:700}}
.c{{margin-left:auto;color:var(--mut);font:.78rem system-ui,sans-serif}}
.badge{{font:.7rem system-ui,sans-serif;background:#f3e2c4;color:#7a4b00;border-radius:6px;padding:2px 7px}}
.body{{padding:0 18px 16px;border-top:1px solid var(--line)}}
.body h4{{margin:16px 0 4px;font:700 .8rem system-ui,sans-serif;color:var(--acc);text-transform:none}}
.body ul,.body ol{{margin:0;padding-left:22px}} .body li{{margin:3px 0}}
.info{{color:var(--mut);font:.88rem system-ui,sans-serif;margin:12px 0 0}}
.vuoto{{color:var(--mut);text-align:center;padding:30px;display:none;font-family:system-ui,sans-serif}}
@media print{{header .chips,#q{{display:none}} .card{{break-inside:avoid;border:0}} details>.body{{display:block}}}}
</style></head><body>
<header>
<h1>Il mio ricettario</h1>
<p class="sub">{len(ricette)} ricette · cerca per nome o ingrediente</p>
<input id="q" type="search" placeholder="Cerca: bonet, farro, pomodorini…" autocomplete="off">
<div class="chips"><button class="chip on" data-cat="">Tutte</button>{chips}</div>
</header>
<main>
{''.join(cards)}
<p class="vuoto" id="vuoto">Nessuna ricetta trovata.</p>
</main>
<script>
const cards=[...document.querySelectorAll('.card')],q=document.getElementById('q');
let cat='';
function filtra(){{
  const t=q.value.trim().toLowerCase();let n=0;
  cards.forEach(c=>{{
    const ok=(!cat||c.dataset.cat===cat)&&(!t||c.dataset.txt.includes(t));
    c.style.display=ok?'':'none';if(ok)n++;
    if(t&&ok&&n<=3)c.open=true;else if(!t)c.open=false;
  }});
  document.getElementById('vuoto').style.display=n?'none':'block';
}}
q.addEventListener('input',filtra);
document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');cat=b.dataset.cat;filtra();
}}));
</script></body></html>"""
    (BASE / "Ricettario.html").write_text(pagina, encoding="utf-8")
    print(f"OK: {len(ricette)} ricette -> INDICE.md, Ricettario.html")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
