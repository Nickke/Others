# Il mio ricettario

302 ricette raccolte dalle chat con ChatGPT, anche le più semplici.

## Come si guarda
- **Ricettario.html**: si apre nel browser (anche da telefono, anche offline). In cima c'è l'indice per categorie e sottocategorie, con i link a ogni ricetta. C'è una ricerca per nome o ingrediente. Stampato (o salvato in PDF dal browser) ogni categoria parte su una pagina nuova.
- **INDICE.md**: lo stesso indice in formato testo, con i link ai file.
- **ricette/**: una ricetta = un file di testo `.md`.
- **immagini/**: le foto delle ricette.

## Come aggiungere una ricetta
1. Copia `ricette/_modello.md`, rinominalo (es. `lasagne.md`) e compilalo. Nel modello trovi l'elenco delle categorie e sottocategorie.
2. (Facoltativo) salva la foto in `immagini/` con lo stesso nome del file: `immagini/lasagne.jpg`.
3. Esegui `python aggiorna.py`: ricostruisce INDICE.md e Ricettario.html.

## Come modificarne una
Apri il file in `ricette/`, cambia il testo, poi esegui `python aggiorna.py`.

## Ricette "da completare"
Quelle con stato `parziale` o `solo nome` hanno l'etichetta "da completare": nelle chat c'era solo il nome o mancavano dosi e passaggi. Quando le riscrivi per intero, metti `stato: completa`.

## Varianti
Se una ricetta compare in più versioni (piadina, granola, pancake…) trovi "variante 1, 2, 3": sono versioni diverse per ingredienti o dosi.
