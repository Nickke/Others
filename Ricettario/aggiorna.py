#!/usr/bin/env python3
"""Rigenera INDICE.md e Ricettario.html a partire dai file in ricette/.

Uso:  python aggiorna.py

Nuova ricetta: copia ricette/_modello.md, rinominalo e compilalo.
Foto (facoltativa): salva immagini/<nome-del-file-ricetta>.jpg
   oppure scrivi  immagine: nome-file.jpg  nell'intestazione della ricetta.
"""
import html
import re
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
RICETTE = BASE / "ricette"
IMMAGINI = BASE / "immagini"

# Ordine di categorie e sottocategorie. Le nuove finiscono in fondo da sole.
STRUTTURA = {
    "Antipasti e salati": ["Torte salate e rustici", "Sfizi e stuzzichini"],
    "Primi": ["Pasta, gnocchi e passatelli", "Riso, farro e cereali", "Zuppe, vellutate e brodi"],
    "Secondi": ["Carne e pesce", "Uova e frittate", "Bowl, insalatone e piatti unici"],
    "Contorni": ["Verdure e legumi", "Patate e zucca"],
    "Dolci": ["Torte e dolci da forno", "Crostate, strudel e tarte", "Dolci al cucchiaio",
              "Biscotti e piccola pasticceria"],
    "Colazione e fit": ["Pancake e crêpes", "Piadine", "Granola, muesli e porridge",
                        "Dolci fit e merende", "Colazioni salate"],
    "Basi e impasti": ["Frolle e impasti", "Pane, pizza e lievitati", "Creme, farciture e glasse",
                       "Salse e marinature"],
    "Conserve e marmellate": ["Marmellate"],
    "Bevande e smoothie": ["Smoothie e frullati", "Cocktail e mocktail", "Altre bevande"],
    "Altro": ["Consigli e spuntini"],
}

# Un colore per categoria (tutti con testo bianco leggibile, contrasto > 4.5).
COLORI = {
    "Antipasti e salati": "#5e6b10",
    "Primi": "#b3261e",
    "Secondi": "#7a2e68",
    "Contorni": "#1e7a3c",
    "Dolci": "#b0225e",
    "Colazione e fit": "#1f5fa8",
    "Basi e impasti": "#7a5a12",
    "Conserve e marmellate": "#5b3fa0",
    "Bevande e smoothie": "#0b7480",
    "Altro": "#4b5560",
}
COLORI_EXTRA = ["#8a3d00", "#00695c", "#6a1b9a", "#37474f", "#9c2f2f", "#33691e"]

# Icone semplici (24x24, solo tratto).
ICONE = {
    "Antipasti e salati": '<path d="M4 20 20 4"/><circle cx="9" cy="15" r="2.4"/><circle cx="13" cy="11" r="2.4"/><circle cx="17" cy="7" r="2.4"/>',
    "Primi": '<path d="M3 11h18a9 9 0 0 1-18 0z"/><path d="M8 4c-1 1.5 1 2.5 0 4M12 4c-1 1.5 1 2.5 0 4M16 4c-1 1.5 1 2.5 0 4"/>',
    "Secondi": '<path d="M3 18h18M5 18a7 7 0 0 1 14 0M12 11V8"/><circle cx="12" cy="6.6" r="1.3"/>',
    "Contorni": '<path d="M5 19C5 10 10 5 19 5c0 9-5 14-14 14zM5 19 14 10"/>',
    "Dolci": '<path d="M6 11h12l-1.5 9h-9zM6 11a6 6 0 0 1 12 0"/><circle cx="12" cy="3.8" r="1.2"/>',
    "Colazione e fit": '<ellipse cx="12" cy="7" rx="8" ry="3"/><path d="M4 7v5c0 1.7 3.6 3 8 3s8-1.3 8-3V7M4 12v5c0 1.7 3.6 3 8 3s8-1.3 8-3v-5"/>',
    "Basi e impasti": '<rect x="6" y="9.5" width="12" height="5" rx="2.5"/><path d="M2 12h4M18 12h4"/>',
    "Conserve e marmellate": '<path d="M6 3h12v3H6zM7 6h10v14H7z"/><path d="M9 11h6v4H9z"/>',
    "Bevande e smoothie": '<path d="M6 5h12l-1.5 15h-9zM7 10h10M14 5l2-3"/>',
    "Altro": '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/>',
}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"


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
    meta["_id"] = slug(path.stem)
    meta["_sez"] = {k: re.sub(r"<!--.*?-->", "", "\n".join(v), flags=re.S).strip()
                    for k, v in sezioni.items()}
    meta.setdefault("nome", path.stem.replace("-", " ").capitalize())
    meta.setdefault("categoria", "Altro")
    meta.setdefault("sottocategoria", "Varie")
    img = meta.get("immagine", "")
    if not img:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            if (IMMAGINI / (path.stem + ext)).exists():
                img = path.stem + ext
                break
    meta["_img"] = img if img and (IMMAGINI / img).exists() else ""
    return meta


def righe(blocco):
    out = []
    for r in blocco.splitlines():
        r = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", r).strip()
        if r:
            out.append(r)
    return out


def da_completare(r):
    return r.get("stato", "").lower() in ("solo nome", "parziale")


def raggruppa(ricette):
    albero = {}
    for r in ricette:
        albero.setdefault(r["categoria"], {}).setdefault(r["sottocategoria"], []).append(r)
    cats = list(STRUTTURA)
    ordc = sorted(albero, key=lambda c: cats.index(c) if c in cats else len(cats))
    out = []
    for c in ordc:
        subs = STRUTTURA.get(c, [])
        ords = sorted(albero[c], key=lambda s: subs.index(s) if s in subs else len(subs))
        out.append((c, [(s, sorted(albero[c][s], key=lambda r: r["nome"].lower())) for s in ords]))
    return out


def colore(c, n_extra=[0]):
    if c not in COLORI:
        COLORI[c] = COLORI_EXTRA[n_extra[0] % len(COLORI_EXTRA)]
        n_extra[0] += 1
    return COLORI[c]


def scrivi_indice_md(albero, tot):
    md = ["# Ricettario", "", f"{tot} ricette in {len(albero)} categorie.", "",
          "Versione da sfogliare nel browser: **Ricettario.html**.", ""]
    for c, subs in albero:
        n = sum(len(x) for _, x in subs)
        md += ["", f"## {c} ({n})", ""]
        for s, rs in subs:
            md += [f"### {s} ({len(rs)})", ""]
            for r in rs:
                extra = " _(da completare)_" if da_completare(r) else ""
                md.append(f"- [{r['nome']}](ricette/{r['_file']}){extra}")
            md.append("")
    (BASE / "INDICE.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def etichetta_fonte(r):
    """Testo leggibile della fonte: ChatGPT, profilo Facebook, sito web... (con link se c'è un URL)."""
    e = html.escape
    f = r.get("fonte", "").strip()
    parti = []
    m = re.match(r"CHAT\s+\d+\s*-\s*(.*?)\s*\((\d{4})-(\d{2})-(\d{2})\)\s*$", f)
    if m:
        parti.append(f"ChatGPT, chat «{e(m.group(1))}» ({m.group(4)}/{m.group(3)}/{m.group(2)})")
    elif f.lower().startswith("facebook"):
        # formato:  Facebook - Nome profilo - https://...
        pezzi = [x.strip() for x in f.split(" - ")]
        nome = pezzi[1] if len(pezzi) > 1 and not pezzi[1].startswith("http") else ""
        url = next((x for x in pezzi if x.startswith("http")), "")
        et = "Facebook" + (f", profilo {e(nome)}" if nome else "")
        parti.append(f'<a href="{e(url)}" rel="noopener">{et}</a>' if url else et)
    elif f.startswith("http"):
        parti.append(f'<a href="{e(f)}" rel="noopener">{e(f)}</a>')
    elif f and f.lower() != "scritta a mano":
        parti.append(e(f))
    elif f:
        parti.append("scritta a mano")
    if "integrata da ricette di riferimento online" in r["_sez"].get("note", "").lower():
        parti.append("integrata con ricette di riferimento online (vedi Note)")
    return "Fonte: " + " + ".join(parti) if parti else ""


def scheda(r):
    s = r["_sez"]
    e = html.escape
    fonte = etichetta_fonte(r)
    ing = "".join(f"<li>{e(x)}</li>" for x in righe(s.get("ingredienti", "")))
    pro = "".join(f"<li>{e(x)}</li>" for x in righe(s.get("procedimento", "")))
    info = "".join(f"<span>{e(x)}</span>" for x in [r.get("porzioni", ""), r.get("tempo", "")]
                   if x and x.lower() != "null")
    nut = e(s.get("valori nutrizionali", "")).replace("\n", "<br>")
    note = e(s.get("note", "")).replace("\n", "<br>")
    badge = '<span class="badge">da completare</span>' if da_completare(r) else ""
    testo = " ".join([r["nome"], r["categoria"], r["sottocategoria"], s.get("ingredienti", "")]).lower()
    img = (f'<img class="foto" src="immagini/{e(r["_img"])}" alt="{e(r["nome"])}" loading="lazy">'
           if r["_img"] else "")
    extra = ""
    if nut:
        extra += f'<div class="extra"><h5>Valori nutrizionali</h5><p>{nut}</p></div>'
    if note:
        extra += f'<div class="extra"><h5>Note</h5><p>{note}</p></div>'
    return f"""<details class="ric" id="{r['_id']}" data-txt="{e(testo)}">
<summary><span class="t">{e(r['nome'])}</span>{badge}</summary>
<div class="corpo">
{img}
{f'<p class="info">{info}</p>' if info else ''}
<div class="due">
{f'<div class="ing"><h5>Ingredienti</h5><ul>{ing}</ul></div>' if ing else ''}
{f'<div class="pro"><h5>Procedimento</h5><ol>{pro}</ol></div>' if pro else ''}
</div>
{extra}
{f'<p class="fonte">{fonte}</p>' if fonte else ''}
<p class="su"><a href="#indice">Torna all'indice</a></p>
</div></details>"""


def scrivi_html(albero, tot):
    e = html.escape
    tiles, toc, corpo = [], [], []
    for c, subs in albero:
        col = colore(c)
        cid = "cat-" + slug(c)
        n = sum(len(x) for _, x in subs)
        ico = f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONE.get(c, ICONE["Altro"])}</svg>'
        taglia = "grande" if n >= 60 else "medio" if n >= 25 else "piccolo"
        elenco = ""
        if taglia != "piccolo":
            elenco = "<ul>" + "".join(f"<li>{e(s)}</li>" for s, _ in subs) + "</ul>"
        tiles.append(f'<a class="tile {taglia}" href="#toc-{cid}" style="--c:{col}">{ico}'
                     f'<span class="nome">{e(c)}</span><span class="num">{n} ricette</span>{elenco}</a>')
        t = [f'<section class="tocat" id="toc-{cid}" style="--c:{col}" data-cat="{cid}">'
             f'<h3><a href="#{cid}">{e(c)}</a><span class="n">{n}</span></h3>']
        b = [f'<section class="cat" id="{cid}" style="--c:{col}" data-cat="{cid}">'
             f'<h2>{ico}{e(c)}</h2>']
        for s, rs in subs:
            sid = f"sub-{slug(c)}-{slug(s)}"
            t.append(f'<div class="tosub"><h4><a href="#{sid}">{e(s)}</a><span class="n">{len(rs)}</span></h4><ul>')
            b.append(f'<section class="sub" id="{sid}"><h3>{e(s)}</h3>')
            for r in rs:
                mark = '<em>da completare</em>' if da_completare(r) else ""
                txt = " ".join([r["nome"], r["_sez"].get("ingredienti", "")]).lower()
                t.append(f'<li data-txt="{e(txt)}"><a href="#{r["_id"]}">{e(r["nome"])}</a>{mark}</li>')
                b.append(scheda(r))
            t.append("</ul></div>")
            b.append("</section>")
        t.append("</section>")
        b.append("</section>")
        toc.append("".join(t))
        corpo.append("".join(b))
    pagina = (PAGINA.replace("%%TOT%%", str(tot)).replace("%%NCAT%%", str(len(albero)))
              .replace("%%TILES%%", "".join(tiles)).replace("%%TOC%%", "".join(toc))
              .replace("%%CORPO%%", "".join(corpo)))
    (BASE / "Ricettario.html").write_text(pagina, encoding="utf-8")


PAGINA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ricettario</title>
<style>
@font-face{font-family:'Bricolage Grotesque';font-weight:200 800;font-display:swap;src:url(font/bricolage-grotesque.woff2) format('woff2')}
@font-face{font-family:'Source Serif 4';font-weight:200 900;font-style:normal;font-display:swap;src:url(font/source-serif-4.woff2) format('woff2')}
@font-face{font-family:'Source Serif 4';font-weight:200 900;font-style:italic;font-display:swap;src:url(font/source-serif-4-italic.woff2) format('woff2')}
:root{--bg:#f4f5f0;--ink:#17211b;--mut:#56635d;--line:#d6dbd3;--c:#1f5fa8;
  --disp:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;--body:'Source Serif 4',Georgia,serif}
*{box-sizing:border-box}
html{scroll-padding-top:84px}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.65 var(--body)}
a{color:inherit}
:focus-visible{outline:3px solid #1f5fa8;outline-offset:2px}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
svg{width:26px;height:26px;flex:none;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}

.cover{padding:56px 0 22px}
.cover h1{margin:0;font:800 clamp(3.4rem,13vw,8.4rem)/.86 var(--disp);letter-spacing:-.045em}
.cover p{max-width:34em;margin:18px 0 0;font-size:1.2rem;color:var(--mut)}

.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0}
.bar .wrap{display:flex;gap:14px;align-items:center}
#q{flex:1;min-width:0;height:48px;padding:0 16px;font:1rem var(--disp);color:var(--ink);background:#fff;border:2px solid var(--ink);border-radius:10px}
.bar a{flex:none;min-height:48px;display:flex;align-items:center;padding:0 6px;font:600 1rem var(--disp);text-decoration:none}
.bar a:hover{text-decoration:underline}
#esito{font:.9rem var(--disp);color:var(--mut);margin:8px 0 0;min-height:1.3em}

.tiles{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-flow:dense;gap:10px;margin:26px 0 8px}
.tile{display:flex;flex-direction:column;gap:2px;padding:16px;min-height:132px;color:#fff;background:var(--c);border-radius:12px;text-decoration:none}
.tile:hover{filter:brightness(1.1)}
.tile svg{width:30px;height:30px;margin-bottom:auto}
.tile .nome{font:800 1.25rem/1.1 var(--disp);letter-spacing:-.01em}
.tile .num{font:500 .95rem var(--disp);opacity:.92}
.tile ul{list-style:none;margin:10px 0 0;padding:0;font:.95rem/1.35 var(--disp);opacity:.95}
.tile.medio{grid-column:span 2}
.tile.grande{grid-column:span 2;grid-row:span 2}
.tile.grande .nome{font-size:clamp(2rem,5vw,3.2rem);line-height:.95}

h2.ind{margin:64px 0 0;font:800 clamp(2rem,6vw,3rem)/1 var(--disp);letter-spacing:-.03em}
.tocat{margin:34px 0 0;padding-left:18px;border-left:8px solid var(--c)}
.tocat h3{display:flex;align-items:baseline;gap:12px;margin:0 0 6px;font:800 1.7rem/1.1 var(--disp);letter-spacing:-.02em}
.tocat h3 a{color:var(--c);text-decoration:none}
.n{font:500 .9rem var(--disp);color:var(--mut);margin-left:8px}
.tocat h3 .n{margin-left:0}
.tosub{margin:14px 0 0}
.tosub h4{margin:0 0 2px;font:700 1.02rem var(--disp)}
.tosub h4 a{text-decoration:none}
.tosub h4 a:hover{text-decoration:underline}
.tosub ul{list-style:none;margin:0;padding:0;columns:2 280px;column-gap:32px}
.tosub li{break-inside:avoid;padding:3px 0;font-size:1rem;line-height:1.4}
.tosub li a{display:inline-block;padding:3px 0;text-decoration:underline;text-decoration-color:color-mix(in srgb,var(--c) 45%,transparent);text-underline-offset:3px}
.tosub li a:hover{text-decoration-color:var(--c)}
.tosub em{margin-left:6px;font:italic .85rem var(--body);color:var(--mut)}

.libro{margin-top:72px}
.cat{margin-top:64px}
.cat>h2{display:flex;align-items:center;gap:14px;margin:0;padding:22px 22px;background:var(--c);color:#fff;border-radius:12px;font:800 clamp(1.9rem,6vw,3.1rem)/1 var(--disp);letter-spacing:-.03em}
.cat>h2 svg{width:38px;height:38px}
.sub>h3{margin:36px 0 6px;font:800 1.4rem/1.2 var(--disp);color:var(--c);letter-spacing:-.01em}
.ric{border-bottom:1px solid var(--line)}
.ric>summary{list-style:none;cursor:pointer;min-height:48px;padding:10px 4px 10px 30px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:relative}
.ric>summary::-webkit-details-marker{display:none}
.ric>summary::before{content:"";position:absolute;left:6px;top:50%;width:9px;height:9px;margin-top:-6px;border-right:2.5px solid var(--c);border-bottom:2.5px solid var(--c);transform:rotate(-45deg)}
.ric[open]>summary::before{transform:rotate(45deg)}
.ric[open]{border-left:6px solid var(--c);padding-left:12px;margin-left:-18px;background:color-mix(in srgb,var(--c) 4%,var(--bg))}
.ric[open]>summary{padding-left:22px}
.ric[open]>summary::before{left:0}
.t{font:700 1.08rem/1.3 var(--disp)}
.badge{font:600 .75rem var(--disp);padding:2px 8px;border:1.5px solid var(--mut);border-radius:999px;color:var(--mut)}
.corpo{padding:4px 8px 22px 12px}
.foto{display:block;width:100%;max-width:560px;border-radius:8px;margin:6px 0 14px}
.info{display:flex;flex-wrap:wrap;gap:4px 22px;margin:0 0 14px;font:500 .95rem var(--disp);color:var(--mut)}
.due{display:grid;grid-template-columns:1fr;gap:22px}
@media (min-width:780px){.due{grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:36px}}
h5{margin:0 0 8px;font:800 1.05rem var(--disp);color:var(--c)}
.ing{padding:16px 18px;background:color-mix(in srgb,var(--c) 9%,#fff);border-radius:10px;align-self:start}
.ing ul{margin:0;padding:0;list-style:none}
.ing li{padding:5px 0 5px 16px;position:relative;border-bottom:1px solid color-mix(in srgb,var(--c) 14%,transparent)}
.ing li:last-child{border-bottom:0}
.ing li::before{content:"";position:absolute;left:0;top:.95em;width:6px;height:6px;border-radius:50%;background:var(--c)}
.pro ol{margin:0;padding:0;list-style:none;counter-reset:p}
.pro li{counter-increment:p;position:relative;padding:0 0 14px 44px}
.pro li::before{content:counter(p);position:absolute;left:0;top:-.1em;font:800 1.6rem/1 var(--disp);color:var(--c)}
.extra{margin-top:10px}
.extra p{margin:0;max-width:44em}
.fonte{margin:14px 0 0;padding-top:10px;border-top:1px solid var(--line);font:500 .9rem/1.4 var(--disp);color:var(--mut)}
.fonte a{color:var(--c);font-weight:600}
.su{margin:4px 0 0;font:500 .95rem var(--disp)}
.su a{color:var(--mut);display:inline-block;padding:10px 0}
.vuoto{display:none;max-width:30em;margin:40px 0;font-size:1.1rem;color:var(--mut)}
.piede{margin:80px 0 48px}
.piede a{font:600 1rem var(--disp)}

@media (max-width:760px){
  body{font-size:17px}
  .cover{padding-top:36px}
  .tiles{grid-template-columns:repeat(2,1fr)}
  .tile.medio{grid-column:span 2}
  .tile.grande{grid-column:span 2;grid-row:span 1}
  .ric[open]{margin-left:-8px;padding-left:8px}
}
@media print{
  body{background:#fff;font-size:11pt}
  .bar,.tiles,.su,.piede,.cover p,#esito{display:none}
  .cat{break-before:page;margin-top:0}
  .ric{break-inside:avoid;border-left:0!important;background:none!important;margin-left:0!important;padding-left:0!important}
  .cat>h2{background:none;color:var(--c);padding:0;border-bottom:3px solid var(--c);border-radius:0}
  .ing{background:none;border:1px solid var(--line)}
}
</style></head><body>
<header class="cover"><div class="wrap">
<h1>Ricettario</h1>
<p>%%TOT%% ricette dalle chat di ogni giorno, dai pancake fit al bonet, dalle frise ai cocktail. Scegli una categoria o cerca un ingrediente.</p>
</div></header>

<div class="bar"><div class="wrap">
<input id="q" type="search" placeholder="Cerca per nome o ingrediente" aria-label="Cerca una ricetta" autocomplete="off">
<a href="#indice">Indice</a>
</div></div>

<main class="wrap">
<p id="esito" role="status" aria-live="polite"></p>
<nav class="tiles" aria-label="Categorie">%%TILES%%</nav>

<section id="indice">
<h2 class="ind">Indice</h2>
%%TOC%%
</section>

<p class="vuoto" id="vuoto">Nessuna ricetta trovata. Prova con un ingrediente più semplice, per esempio «farro» o «zucca».</p>
<div class="libro">%%CORPO%%</div>
<p class="piede"><a href="#top">Torna in cima</a></p>
</main>
<script>
const q=document.getElementById('q'),esito=document.getElementById('esito');
const ric=[...document.querySelectorAll('.ric')];
const voci=[...document.querySelectorAll('.tosub li')];
function nascondiVuoti(){
  document.querySelectorAll('.tosub,.sub').forEach(s=>{
    const k=s.querySelectorAll(s.classList.contains('sub')?'.ric':'li');
    s.style.display=[...k].some(x=>x.style.display!=='none')?'':'none'});
  document.querySelectorAll('.tocat,.cat').forEach(c=>{
    const k=c.querySelectorAll(c.classList.contains('cat')?'.sub':'.tosub');
    c.style.display=[...k].some(x=>x.style.display!=='none')?'':'none'});
}
function aggiorna(){
  const t=q.value.trim().toLowerCase();let n=0;
  // durante la ricerca mostro solo i risultati: nascondo riquadri e indice
  document.querySelector('.tiles').style.display=t?'none':'';
  document.getElementById('indice').style.display=t?'none':'';
  document.querySelector('.libro').style.marginTop=t?'24px':'';
  ric.forEach(r=>{const ok=!t||r.dataset.txt.includes(t);r.style.display=ok?'':'none';
    if(ok)n++;if(t&&ok)r.open=n<=8;else if(!t)r.open=false});
  voci.forEach(v=>{v.style.display=(!t||v.dataset.txt.includes(t))?'':'none'});
  nascondiVuoti();
  document.getElementById('vuoto').style.display=n?'none':'block';
  esito.textContent=t?(n+(n===1?' ricetta trovata':' ricette trovate')):'';
}
q.addEventListener('input',aggiorna);
document.querySelector('.bar a').addEventListener('click',()=>{q.value='';aggiorna()});
function apriDaHash(){const el=document.getElementById(location.hash.slice(1));if(el&&el.tagName==='DETAILS')el.open=true}
window.addEventListener('hashchange',apriDaHash);apriDaHash();
window.addEventListener('beforeprint',()=>ric.forEach(r=>r.open=true));
</script></body></html>"""


def main():
    files = sorted(p for p in RICETTE.glob("*.md") if not p.name.startswith("_"))
    ricette = [leggi(p) for p in files]
    albero = raggruppa(ricette)
    scrivi_indice_md(albero, len(ricette))
    scrivi_html(albero, len(ricette))
    print(f"OK: {len(ricette)} ricette, {len(albero)} categorie -> INDICE.md, Ricettario.html")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
