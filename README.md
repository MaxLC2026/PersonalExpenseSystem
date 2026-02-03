# PersonalExpenseSystem – Sistema gestione spese e budget (console + SQL)

Programma eseguito dal prompt dei comandi che consente ad un singolo utente di gestire:
• Registrare le spese giornaliere
• Organizzare le spese per categoria
• Definire limiti di spesa mensili (budget)
• Visualizzare report riepilogativi sul comportamento di spesa

## Struttura del repository (come da linee guida)

PersonalExpenseSystem/
 ├─ src/
 │   └─ main.py
 ├─ sql/
 │   └─ database.sql
 ├─ demo/
 │   └─ demo_video.mp4
 └─ README.md

## Requisiti
- Python 3.x
- Moduli usati: solo standard library (sqlite3, datetime, csv, pathlib, os, sys)

## Avvio del programma
Da terminale nella cartella principale:

python src/main.py

## Nota sul database SQLite
Lo script SQL richiesto dal progetto si trova nel file sql/database.sql.
Il database SQLite viene creato automaticamente dal programma durante l’esecuzione.
