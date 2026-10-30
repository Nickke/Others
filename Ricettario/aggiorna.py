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
from pathlib import Path

BASE = Path(__file__).resolve().parent
RICETTE = BASE / "ricette"
IMMAGINI = BASE / "immagini"

# Ordine delle categorie e delle sottocategorie nell'indice.
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

# Icone semplici (24x24, solo tratto) per le categorie.
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
ICONA_DEFAULT = ICONE["Altro"]


def slug(s):
    import unicodedata
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
    corpo_sez = {}
    for k, v in sezioni.items():
        t = "\n".join(v).strip()
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S).strip()
        corpo_sez[k] = t
    meta["_sez"] = corpo_sez
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


def ordina_cat(c):
    cats = list(STRUTTURA)
    return cats.index(c) if c in cats else len(cats)


def ordina_sub(c, s):
    subs = STRUTTURA.get(c, [])
    return subs.index(s) if s in subs else len(subs)


def da_completare(r):
    return r.get("stato", "").lower() in ("solo nome", "parziale")


def raggruppa(ricette):
    albero = {}
    for r in ricette:
        albero.setdefault(r["categoria"], {}).setdefault(r["sottocategoria"], []).append(r)
    cats = sorted(albero, key=ordina_cat)
    out = []
    for c in cats:
        subs = sorted(albero[c], key=lambda s: ordina_sub(c, s))
        out.append((c, [(s, sorted(albero[c][s], key=lambda r: r["nome"].lower())) for s in subs]))
    return out


def scrivi_indice_md(albero, tot):
    md = ["# Il mio ricettario", "", f"{tot} ricette in {len(albero)} categorie.", "",
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


def scheda(r):
    s = r["_sez"]
    e = html.escape
    ing = "".join(f"<li>{e(x)}</li>" for x in righe(s.get("ingredienti", "")))
    pro = "".join(f"<li>{e(x)}</li>" for x in righe(s.get("procedimento", "")))
    info = " · ".join(e(x) for x in [r.get("porzioni", ""), r.get("tempo", "")] if x and x.lower() != "null")
    nut = e(s.get("valori nutrizionali", "")).replace("\n", "<br>")
    note = e(s.get("note", "")).replace("\n", "<br>")
    badge = f'<span class="badge">da completare</span>' if da_completare(r) else ""
    testo = " ".join([r["nome"], r["categoria"], r["sottocategoria"], s.get("ingredienti", "")]).lower()
    img = (f'<img class="foto" src="immagini/{html.escape(r["_img"])}" alt="{e(r["nome"])}" loading="lazy">'
           if r["_img"] else "")
    return f"""<details class="ric" id="{r['_id']}" data-txt="{e(testo)}">
<summary><span class="t">{e(r['nome'])}</span>{badge}</summary>
<div class="corpo">
{img}
{f'<p class="info">{info}</p>' if info else ''}
{f'<div class="col"><h5>Ingredienti</h5><ul>{ing}</ul></div>' if ing else ''}
{f'<div class="col"><h5>Procedimento</h5><ol>{pro}</ol></div>' if pro else ''}
{f'<h5>Valori nutrizionali</h5><p>{nut}</p>' if nut else ''}
{f'<h5>Note</h5><p>{note}</p>' if note else ''}
<p class="su"><a href="#indice">Torna all'indice</a></p>
</div></details>"""


def scrivi_html(albero, tot):
    e = html.escape
    # ---- indice
    salti, toc, corpo = [], [], []
    for c, subs in albero:
        cid = "cat-" + slug(c)
        n = sum(len(x) for _, x in subs)
        ico = f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONE.get(c, ICONA_DEFAULT)}</svg>'
        salti.append(f'<a href="#{cid}" class="salto">{ico}<span>{e(c)}</span><b>{n}</b></a>')
        t = [f'<section class="tocat" data-cat="{cid}"><h3><a href="#{cid}">{ico}{e(c)}</a><span class="n">{n}</span></h3>']
        b = [f'<section class="cat" id="{cid}" data-cat="{cid}"><h2>{ico}{e(c)}</h2>']
        for s, rs in subs:
            sid = f"sub-{slug(c)}-{slug(s)}"
            t.append(f'<div class="tosub" data-sub="{sid}"><h4><a href="#{sid}">{e(s)}</a> <span class="n">{len(rs)}</span></h4><ul>')
            b.append(f'<section class="sub" id="{sid}" data-sub="{sid}"><h3>{e(s)}</h3>')
            for r in rs:
                mark = " <em>(da completare)</em>" if da_completare(r) else ""
                txt = " ".join([r["nome"], r["_sez"].get("ingredienti", "")]).lower()
                t.append(f'<li data-ref="{r["_id"]}" data-txt="{e(txt)}"><a href="#{r["_id"]}">{e(r["nome"])}</a>{mark}</li>')
                b.append(scheda(r))
            t.append("</ul></div>")
            b.append("</section>")
        t.append("</section>")
        b.append("</section>")
        toc.append("".join(t))
        corpo.append("".join(b))

    pagina = PAGINA.replace("%%TOT%%", str(tot)).replace("%%NCAT%%", str(len(albero)))
    pagina = pagina.replace("%%SALTI%%", "".join(salti)).replace("%%TOC%%", "".join(toc))
    pagina = pagina.replace("%%CORPO%%", "".join(corpo))
    (BASE / "Ricettario.html").write_text(pagina, encoding="utf-8")


PAGINA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Il mio ricettario</title>
<style>
:root{--bg:#fbfbf9;--ink:#1f2a2e;--mut:#65757a;--acc:#1f5c4d;--acc2:#d9a21b;--line:#dfe4e2;--card:#fff}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:14px}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Georgia,'Palatino Linotype',serif}
a{color:inherit}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.wrap{max-width:900px;margin:0 auto;padding:0 20px}
.copertina{padding:64px 0 28px;border-bottom:3px double var(--ink)}
.copertina h1{font:700 clamp(2.4rem,7vw,4rem)/1.02 Georgia,serif;margin:0;letter-spacing:-.02em}
.copertina p{margin:12px 0 0;color:var(--mut);font:italic 1.1rem Georgia,serif}
.cerca{margin:26px 0 0}
#q{width:100%;padding:13px 15px;font:1rem system-ui,sans-serif;border:1px solid var(--ink);border-radius:4px;background:#fff}
.salti{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin:26px 0 0}
.salto{display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card);text-decoration:none;font:600 .92rem system-ui,sans-serif}
.salto:hover{border-color:var(--acc)}
.salto b{margin-left:auto;font-weight:600;color:var(--mut)}
svg{width:22px;height:22px;flex:none;fill:none;stroke:var(--acc);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
h2.ind{font:700 1.9rem Georgia,serif;margin:44px 0 6px}
.tocat{margin:30px 0 0}
.tocat h3{display:flex;align-items:center;gap:10px;margin:0;padding-bottom:6px;border-bottom:1px solid var(--ink);font:700 1.35rem Georgia,serif}
.tocat h3 a{display:flex;align-items:center;gap:10px;text-decoration:none}
.n{margin-left:auto;font:.8rem system-ui,sans-serif;color:var(--mut);font-weight:400}
.tosub h4{margin:16px 0 4px;font:700 .8rem system-ui,sans-serif;letter-spacing:.02em;color:var(--acc)}
.tosub h4 a{text-decoration:none}
.tosub h4 .n{margin-left:6px}
.tosub ul{list-style:none;margin:0;padding:0;columns:2 260px;column-gap:28px}
.tosub li{break-inside:avoid;padding:2px 0;font-size:.97rem;line-height:1.35}
.tosub li a{text-decoration:none;border-bottom:1px dotted var(--mut)}
.tosub li a:hover{color:var(--acc);border-bottom-color:var(--acc)}
.tosub em{color:var(--mut);font-size:.8em}
.libro{margin-top:60px}
.cat{margin-top:56px}
.cat>h2{display:flex;align-items:center;gap:12px;margin:0 0 4px;padding:10px 0;border-top:3px double var(--ink);border-bottom:1px solid var(--ink);font:700 1.9rem Georgia,serif}
.cat>h2 svg{width:30px;height:30px}
.sub>h3{margin:28px 0 8px;font:italic 400 1.3rem Georgia,serif;color:var(--acc)}
.ric{border-bottom:1px solid var(--line)}
.ric summary{list-style:none;cursor:pointer;padding:11px 2px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.ric summary::-webkit-details-marker{display:none}
.ric summary::before{content:"+";font:600 1rem system-ui,sans-serif;color:var(--acc);width:1em}
.ric[open] summary::before{content:"\\2212"}
.t{font-weight:700;font-size:1.05rem}
.badge{font:.7rem system-ui,sans-serif;background:#f4e6bf;color:#6b4a00;border-radius:4px;padding:2px 7px}
.corpo{padding:2px 4px 18px 22px}
.foto{display:block;width:100%;max-width:520px;border-radius:4px;margin:4px 0 12px}
.info{margin:0 0 6px;color:var(--mut);font:.88rem system-ui,sans-serif}
.corpo h5{margin:14px 0 4px;font:700 .8rem system-ui,sans-serif;color:var(--acc);letter-spacing:.02em}
.corpo ul,.corpo ol{margin:0;padding-left:22px}
.corpo li{margin:3px 0}
.corpo p{margin:4px 0}
.su{margin-top:12px!important;font:.8rem system-ui,sans-serif}
.su a{color:var(--mut)}
.vuoto{display:none;text-align:center;color:var(--mut);padding:36px;font-family:system-ui,sans-serif}
.piede{margin:70px 0 40px;color:var(--mut);font:.8rem system-ui,sans-serif;text-align:center}
@media (max-width:560px){body{font-size:16px}.copertina{padding-top:40px}}
@media print{
  body{font-size:11pt;background:#fff}
  .cerca,.salti,.su,.piede{display:none}
  .cat{break-before:page;margin-top:0}
  .ric{break-inside:avoid}
  .corpo{display:block}
  a{text-decoration:none}
}
</style></head><body>
<div class="wrap">
<header class="copertina" id="inizio">
<h1>Il mio ricettario</h1>
<p>%%TOT%% ricette in %%NCAT%% categorie, raccolte dalle chat di ogni giorno.</p>
<div class="cerca"><input id="q" type="search" placeholder="Cerca una ricetta o un ingrediente: bonet, farro, pomodorini" aria-label="Cerca" autocomplete="off"></div>
<nav class="salti" aria-label="Categorie">%%SALTI%%</nav>
</header>

<main>
<section id="indice">
<h2 class="ind">Indice</h2>
%%TOC%%
</section>
<p class="vuoto" id="vuoto">Nessuna ricetta trovata.</p>
<div class="libro">%%CORPO%%</div>
</main>
<p class="piede"><a href="#inizio">Torna in cima</a></p>
</div>
<script>
const q=document.getElementById('q');
const ric=[...document.querySelectorAll('.ric')];
const voci=[...document.querySelectorAll('.tosub li')];
function aggiorna(){
  const t=q.value.trim().toLowerCase();let n=0;
  ric.forEach(r=>{const ok=!t||r.dataset.txt.includes(t);r.style.display=ok?'':'none';if(ok)n++;
    if(t&&ok){r.open=n<=3}else if(!t){r.open=false}});
  voci.forEach(v=>{v.style.display=(!t||v.dataset.txt.includes(t))?'':'none'});
  document.querySelectorAll('.tosub,.sub').forEach(s=>{
    const k=s.querySelectorAll(s.classList.contains('sub')?'.ric':'li');
    s.style.display=[...k].some(x=>x.style.display!=='none')?'':'none'});
  document.querySelectorAll('.tocat,.cat').forEach(c=>{
    const k=c.querySelectorAll(c.classList.contains('cat')?'.sub':'.tosub');
    c.style.display=[...k].some(x=>x.style.display!=='none')?'':'none'});
  document.getElementById('vuoto').style.display=n?'none':'block';
}
q.addEventListener('input',aggiorna);
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
