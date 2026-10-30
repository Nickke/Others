# Il mio ricettario

Raccolta di tutte le ricette trovate nelle chat con ChatGPT (anche le più semplici).

## Come si guarda
- **Ricettario.html**: doppio clic, si apre nel browser. Ricerca per nome o ingrediente, filtro per categoria, stampabile. Funziona offline, anche da telefono.
- **INDICE.md**: elenco di tutte le ricette per categoria, con link ai singoli file.
- **ricette/**: una ricetta = un file di testo `.md`, leggibile con qualsiasi editor.

## Come aggiungere una ricetta
1. Copia `ricette/_modello.md`, rinominalo (es. `lasagne.md`) e compilalo.
2. Esegui `python aggiorna.py` (ricostruisce INDICE.md e Ricettario.html).

## Come modificarne una
Apri il file in `ricette/`, cambia il testo, poi esegui `python aggiorna.py`.

## Ricette "da completare"
Quelle con stato `parziale` o `solo nome` mostrano un'etichetta nel ricettario: nelle chat c'era solo il nome o mancavano dosi e passaggi. Quando le riscrivi per intero, metti `stato: completa`.

## Varianti
Se una ricetta compare in più versioni (es. piadina, granola, pancake) trovi "variante 1, 2, 3": sono versioni davvero diverse tra loro, per ingredienti o dosi.
