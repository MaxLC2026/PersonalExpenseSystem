#!/usr/bin/env python3
# ============================================================
# SISTEMA DI GESTIONE SPESE PERSONALI E BUDGET (SQL + Prompt comandi)
# ============================================================
# Funzionalità extra aggiunte rispetto ai requisiti minimi:
# 1) Messaggi di errore evidenziati in rosso (se supportato dal terminale)
# 2) Eliminazione categoria consentita solo se non esistono spese collegate
# 3) Pulizia schermo al ritorno nel menu principale
# 4) Inserimento date in formato italiano GG-MM-AAAA con conversione automatica per il database
# 5) Esportazione CSV compatibile Excel:
#    - separatore ;
#    - intestazioni in maiuscolo
#    - data in formato GG-MM-AAAA
#    - nome file automatico Report_Spese_DATA.csv
# ============================================================



import os
import sys
import sqlite3
from sqlite3 import Connection
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import csv

# ------------------------------------------------------------
# Percorso del database: cartella sql/ del progetto
# ------------------------------------------------------------
PERCORSO_DB = Path(__file__).resolve().parents[1] / "sql" / "expenses.db"
PERCORSO_DB.parent.mkdir(parents=True, exist_ok=True)


# ==========================================
# SEZIONE 0 - UTILITA' CONSOLE (COLORI/CLEAR)
# ==========================================
def abilita_colori_windows() -> None:
    # Su Windows, alcuni terminali richiedono di abilitare la "Virtual Terminal Processing"
    # per mostrare correttamente i colori ANSI.
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return


def stampa_errore(messaggio: str) -> None:
    # Rosso ANSI se siamo su terminale interattivo
    if sys.stdout.isatty():
        print(f"\033[31m{messaggio}\033[0m")
    else:
        print(messaggio)


def stampa_ok(messaggio: str) -> None:
    # Verde ANSI (opzionale)
    if sys.stdout.isatty():
        print(f"\033[32m{messaggio}\033[0m")
    else:
        print(messaggio)

def conferma_testo(etichetta: str, valore: str) -> bool:
    # Mostra ciò che l'utente ha inserito e chiede conferma per evitare errori di battitura
    risposta = input(f"Hai inserito {etichetta}: '{valore}'. Confermi? (s/N): ").strip().lower()
    return risposta == "s"


def stampa_esito(ok: bool, messaggio: str) -> None:
    if ok:
        stampa_ok(messaggio)
    else:
        stampa_errore(messaggio)


def pulisci_schermo() -> None:
    comando = "cls" if os.name == "nt" else "clear"
    os.system(comando)


# =========================
# SEZIONE 1 - DATABASE (DB)
# =========================
def ottieni_connessione() -> Connection:
    conn = sqlite3.connect(PERCORSO_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def inizializza_database(conn: Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categorie (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL UNIQUE,
            creato_il       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS spese (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            data_spesa      TEXT NOT NULL
                            CHECK (data_spesa GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
            importo         REAL NOT NULL CHECK (importo > 0),
            id_categoria    INTEGER NOT NULL,
            descrizione     TEXT,
            creato_il       TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (id_categoria) REFERENCES categorie(id)
                ON UPDATE CASCADE
                ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS budget (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            mese            TEXT NOT NULL
                            CHECK (mese GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
            id_categoria    INTEGER NOT NULL,
            importo         REAL NOT NULL CHECK (importo > 0),
            creato_il       TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (mese, id_categoria),
            FOREIGN KEY (id_categoria) REFERENCES categorie(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        );
        """
    )
    conn.commit()


# ======================================
# SEZIONE 2 - VALIDAZIONE INPUT (CONSOLE)
# ======================================
def leggi_non_vuoto(messaggio: str) -> str:
    while True:
        testo = input(messaggio).strip()
        if testo:
            return testo
        stampa_errore("Errore: valore vuoto. Riprovare.")


def leggi_float_positivo(messaggio: str) -> float:
    while True:
        grezzo = input(messaggio).strip().replace(",", ".")
        try:
            valore = float(grezzo)
        except ValueError:
            stampa_errore("Errore: inserisci un numero valido.")
            continue
        if valore <= 0:
            stampa_errore("Errore: l’importo deve essere maggiore di zero.")
            continue
        return valore


def leggo_data_gg_mm_aaaa(messaggio: str) -> str:
    # Utente: GG-MM-AAAA -> DB: AAAA-MM-GG
    while True:
        testo = input(messaggio).strip()
        try:
            data = datetime.strptime(testo, "%d-%m-%Y")
            return data.strftime("%Y-%m-%d")
        except ValueError:
            stampa_errore("Errore: usa il formato GG-MM-AAAA (es. 20-01-2026).")


def leggi_mese_aaaa_mm(messaggio: str) -> str:
    while True:
        testo = input(messaggio).strip()
        try:
            datetime.strptime(testo + "-01", "%Y-%m-%d")
            return testo
        except ValueError:
            stampa_errore("Errore: mese non valido. Usa YYYY-MM (es. 2025-01).")


def leggi_intero_positivo(messaggio: str) -> Optional[int]:
    testo = leggi_non_vuoto(messaggio)
    if not testo.isdigit():
        return None
    valore = int(testo)
    return valore if valore > 0 else None


# ======================================
# SEZIONE 3 - FUNZIONI DB (DAO / QUERY)
# ======================================
def ottieni_id_categoria(conn: Connection, nome_categoria: str) -> Optional[int]:
    riga = conn.execute("SELECT id FROM categorie WHERE nome = ?;", (nome_categoria,)).fetchone()
    return int(riga["id"]) if riga else None


def inserisci_categoria(conn: Connection, nome_categoria: str) -> Tuple[bool, str]:
    nome_categoria = nome_categoria.strip()
    if not nome_categoria:
        return False, "Errore: il nome categoria non può essere vuoto."
    if ottieni_id_categoria(conn, nome_categoria) is not None:
        return False, "Errore: la categoria esiste già."
    try:
        conn.execute("INSERT INTO categorie(nome) VALUES (?);", (nome_categoria,))
        conn.commit()
        return True, "Categoria inserita correttamente."
    except sqlite3.IntegrityError as errore:
        return False, f"Errore DB: {errore}"


def categoria_ha_spese(conn: Connection, id_categoria: int) -> bool:
    riga = conn.execute("SELECT 1 FROM spese WHERE id_categoria = ? LIMIT 1;", (id_categoria,)).fetchone()
    return riga is not None


def elimina_categoria(conn: Connection, nome_categoria: str) -> Tuple[bool, str]:
    # Non si elimina se ci sono spese collegate (FK + regola applicativa).
    id_categoria = ottieni_id_categoria(conn, nome_categoria)
    if id_categoria is None:
        return False, "Errore: la categoria non esiste."
    if categoria_ha_spese(conn, id_categoria):
        return False, "Errore: impossibile eliminare. Esistono spese associate a questa categoria."
    conn.execute("DELETE FROM categorie WHERE id = ?;", (id_categoria,))
    conn.commit()
    return True, "Categoria eliminata correttamente."


def inserisci_spesa(conn: Connection, data_spesa: str, importo: float, nome_categoria: str, descrizione: str) -> Tuple[bool, str]:
    if importo <= 0:
        return False, "Errore: l’importo deve essere maggiore di zero."
    id_categoria = ottieni_id_categoria(conn, nome_categoria)
    if id_categoria is None:
        return False, "Errore: la categoria non esiste."
    try:
        conn.execute(
            "INSERT INTO spese(data_spesa, importo, id_categoria, descrizione) VALUES (?, ?, ?, ?);",
            (data_spesa, importo, id_categoria, descrizione if descrizione.strip() else None),
        )
        conn.commit()
        return True, "Spesa inserita correttamente."
    except sqlite3.IntegrityError as errore:
        return False, f"Errore DB: {errore}"


def aggiorna_spesa(conn: Connection, id_spesa: int, data_spesa: str, importo: float, nome_categoria: str, descrizione: str) -> Tuple[bool, str]:
    if importo <= 0:
        return False, "Errore: l’importo deve essere maggiore di zero."
    id_categoria = ottieni_id_categoria(conn, nome_categoria)
    if id_categoria is None:
        return False, "Errore: la categoria non esiste."
    if not conn.execute("SELECT id FROM spese WHERE id = ?;", (id_spesa,)).fetchone():
        return False, "Errore: ID spesa non trovato."
    try:
        conn.execute(
            """
            UPDATE spese
            SET data_spesa = ?, importo = ?, id_categoria = ?, descrizione = ?
            WHERE id = ?;
            """,
            (data_spesa, importo, id_categoria, descrizione if descrizione.strip() else None, id_spesa),
        )
        conn.commit()
        return True, "Spesa aggiornata correttamente."
    except sqlite3.IntegrityError as errore:
        return False, f"Errore DB: {errore}"


def elimina_spesa(conn: Connection, id_spesa: int) -> Tuple[bool, str]:
    if not conn.execute("SELECT id FROM spese WHERE id = ?;", (id_spesa,)).fetchone():
        return False, "Errore: ID spesa non trovato."
    conn.execute("DELETE FROM spese WHERE id = ?;", (id_spesa,))
    conn.commit()
    return True, "Spesa eliminata correttamente."


def salva_budget(conn: Connection, mese: str, nome_categoria: str, importo: float) -> Tuple[bool, str]:
    if importo <= 0:
        return False, "Errore: il budget deve essere maggiore di zero."
    id_categoria = ottieni_id_categoria(conn, nome_categoria)
    if id_categoria is None:
        return False, "Errore: la categoria non esiste."
    try:
        conn.execute(
            """
            INSERT INTO budget(mese, id_categoria, importo)
            VALUES (?, ?, ?)
            ON CONFLICT(mese, id_categoria) DO UPDATE SET importo = excluded.importo;
            """,
            (mese, id_categoria, importo),
        )
        conn.commit()
        return True, "Budget mensile salvato correttamente."
    except sqlite3.IntegrityError as errore:
        return False, f"Errore DB: {errore}"


def esporta_spese_csv(conn: Connection, percorso_file: str) -> Tuple[bool, str]:
    righe = conn.execute(
        """
        SELECT s.id, s.data_spesa, c.nome AS categoria,
               s.importo, COALESCE(s.descrizione, '') AS descrizione
        FROM spese s
        JOIN categorie c ON c.id = s.id_categoria
        ORDER BY s.data_spesa ASC, s.id ASC;
        """
    ).fetchall()

    if not righe:
        return False, "Errore: nessuna spesa da esportare."

    with open(percorso_file, "w", newline="", encoding="utf-8") as f:
        # separatore corretto per Excel italiano
        scrittore = csv.writer(f, delimiter=';')

        # intestazioni in MAIUSCOLO
        scrittore.writerow(["ID", "DATA", "CATEGORIA", "IMPORTO", "DESCRIZIONE"])

        for r in righe:
            # conversione data da AAAA-MM-GG a GG-MM-AAAA
            data_formattata = datetime.strptime(r["data_spesa"], "%Y-%m-%d").strftime("%d-%m-%Y")

            scrittore.writerow([
                r["id"],
                data_formattata,
                r["categoria"],
                f"{float(r['importo']):.2f}",
                r["descrizione"]
            ])

    return True, f"Esportazione completata: {percorso_file}"

# ======================================
# SEZIONE 4 - REPORT (SELECT + STAMPA)
# ======================================
def elenco_categorie(conn: Connection) -> None:
    righe = conn.execute("SELECT id, nome FROM categorie ORDER BY nome ASC;").fetchall()
    if not righe:
        print("\nNessuna categoria presente.\n")
        return
    print("\nCategorie disponibili:")
    for r in righe:
        print(f"- {r['nome']} (id={r['id']})")
    print()


def elenco_spese_con_id(conn: Connection) -> None:
    righe = conn.execute(
        """
        SELECT s.id, s.data_spesa AS data, c.nome AS categoria, s.importo AS importo, COALESCE(s.descrizione, '') AS descrizione
        FROM spese s
        JOIN categorie c ON c.id = s.id_categoria
        ORDER BY s.data_spesa ASC, s.id ASC;
        """
    ).fetchall()
    if not righe:
        print("\nNessuna spesa presente.\n")
        return
    print("\nID  Data        Categoria           Importo    Descrizione")
    print("-" * 70)
    for r in righe:
        print(f"{r['id']:<3} {r['data']}  {r['categoria']:<18}  {r['importo']:>8.2f}  {r['descrizione']}")
    print()


def report_totale_per_categoria(conn: Connection) -> None:
    righe = conn.execute(
        """
        SELECT c.nome AS categoria, ROUND(COALESCE(SUM(s.importo), 0), 2) AS totale_speso
        FROM categorie c
        LEFT JOIN spese s ON s.id_categoria = c.id
        GROUP BY c.id
        ORDER BY totale_speso DESC, categoria ASC;
        """
    ).fetchall()
    print("\nCategoria..................Totale Speso")
    for r in righe:
        print(f"{r['categoria']:<26}{r['totale_speso']:>10.2f}")
    print()


def report_spese_vs_budget(conn: Connection) -> None:
    righe = conn.execute(
        """
        WITH speso AS (
            SELECT substr(data_spesa, 1, 7) AS mese, id_categoria, SUM(importo) AS speso
            FROM spese
            GROUP BY mese, id_categoria
        )
        SELECT b.mese, c.nome AS categoria, b.importo AS budget, COALESCE(s.speso, 0) AS speso
        FROM budget b
        JOIN categorie c ON c.id = b.id_categoria
        LEFT JOIN speso s ON s.mese = b.mese AND s.id_categoria = b.id_categoria
        ORDER BY b.mese DESC, categoria ASC;
        """
    ).fetchall()
    if not righe:
        print("\nNessun budget definito.\n")
        return
    for r in righe:
        stato = "OK"
        if r["speso"] > r["budget"]:
            stato = "SUPERAMENTO BUDGET"
        elif r["speso"] == r["budget"]:
            stato = "BUDGET RAGGIUNTO"
        print("\nMese:", r["mese"])
        print("Categoria:", r["categoria"])
        print("Budget:", round(float(r["budget"]), 2))
        print("Speso:", round(float(r["speso"]), 2))
        print("Stato:", stato)
    print()


def report_elenco_spese(conn: Connection) -> None:
    righe = conn.execute(
        """
        SELECT s.data_spesa AS data, c.nome AS categoria, s.importo AS importo, COALESCE(s.descrizione, '') AS descrizione
        FROM spese s
        JOIN categorie c ON c.id = s.id_categoria
        ORDER BY s.data_spesa ASC, s.id ASC;
        """
    ).fetchall()
    print("\nData        Categoria           Importo    Descrizione")
    print("-" * 62)
    for r in righe:
        print(f"{r['data']}  {r['categoria']:<18}  {r['importo']:>8.2f}  {r['descrizione']}")
    print()


def menu_report(conn: Connection) -> None:
    while True:
        print("\n--- MENU REPORT ---")
        print("1. Totale spese per categoria")
        print("2. Spese mensili vs budget")
        print("3. Elenco completo delle spese ordinate per data")
        print("4. Ritorna al menu principale")
        scelta = input("Inserisci la tua scelta: ").strip()
        if scelta == "1":
            report_totale_per_categoria(conn)
        elif scelta == "2":
            report_spese_vs_budget(conn)
        elif scelta == "3":
            report_elenco_spese(conn)
        elif scelta == "4":
            return
        else:
            stampa_errore("Errore: scelta non valida. Riprovare.")


# ======================================
# SEZIONE 5 - MODULI CLI (INPUT/OUTPUT)
# ======================================
def modulo_gestisci_categorie(conn: Connection) -> None:
    while True:
        print("\n--- Gestione Categorie ---")
        print("1. Inserisci categoria")
        print("2. Elenca categorie")
        print("3. Elimina categoria")
        print("4. Ritorna al menu principale")
        scelta = input("Inserisci la tua scelta: ").strip()

        if scelta == "1":
            nome_categoria = leggi_non_vuoto("Nome della categoria: ")
            if not conferma_testo("la categoria", nome_categoria):
                print("Operazione annullata.")
                continue
            ok, messaggio = inserisci_categoria(conn, nome_categoria)
            stampa_esito(ok, messaggio)
        elif scelta == "2":
            elenco_categorie(conn)
        elif scelta == "3":
            elenco_categorie(conn)
            nome_categoria = leggi_non_vuoto("Nome della categoria da eliminare: ")
            if not conferma_testo("la categoria da eliminare", nome_categoria):
                print("Operazione annullata.")
                continue
            ok, messaggio = elimina_categoria(conn, nome_categoria)
            stampa_esito(ok, messaggio)
        elif scelta == "4":
            return
        else:
            stampa_errore("Errore: scelta non valida. Riprovare.")


def modulo_inserisci_spesa(conn: Connection) -> None:
    print("\n--- Inserisci Spesa ---")
    data_spesa = leggo_data_gg_mm_aaaa("Data (GG-MM-AAAA): ")
    importo = leggi_float_positivo("Importo: ")
    elenco_categorie(conn)
    nome_categoria = leggi_non_vuoto("Nome della categoria: ")
    descrizione = input("Descrizione (facoltativa): ").strip()
    ok, messaggio = inserisci_spesa(conn, data_spesa, importo, nome_categoria, descrizione)
    stampa_esito(ok, messaggio)


def modulo_modifica_spesa(conn: Connection) -> None:
    print("\n--- Modifica Spesa ---")
    elenco_spese_con_id(conn)
    id_spesa = leggi_intero_positivo("Inserisci ID della spesa da modificare: ")
    if id_spesa is None:
        stampa_errore("Errore: l'ID deve essere un intero positivo.")
        return
    nuova_data = leggo_data_gg_mm_aaaa("Nuova data (GG-MM-AAAA): ")
    nuovo_importo = leggi_float_positivo("Nuovo importo: ")
    elenco_categorie(conn)
    nuova_categoria = leggi_non_vuoto("Nuova categoria: ")
    nuova_descrizione = input("Nuova descrizione (facoltativa): ").strip()
    ok, messaggio = aggiorna_spesa(conn, id_spesa, nuova_data, nuovo_importo, nuova_categoria, nuova_descrizione)
    stampa_esito(ok, messaggio)


def modulo_elimina_spesa(conn: Connection) -> None:
    print("\n--- Elimina Spesa ---")
    elenco_spese_con_id(conn)
    id_spesa = leggi_intero_positivo("Inserisci ID della spesa da eliminare: ")
    if id_spesa is None:
        stampa_errore("Errore: l'ID deve essere un intero positivo.")
        return
    conferma = input("Confermi eliminazione? (s/N): ").strip().lower()
    if conferma != "s":
        print("Operazione annullata.")
        return
    ok, messaggio = elimina_spesa(conn, id_spesa)
    stampa_esito(ok, messaggio)


def modulo_definisci_budget(conn: Connection) -> None:
    print("\n--- Definisci Budget Mensile ---")
    mese = leggi_mese_aaaa_mm("Mese (YYYY-MM): ")
    elenco_categorie(conn)
    nome_categoria = leggi_non_vuoto("Nome della categoria: ")
    importo = leggi_float_positivo("Importo del budget: ")
    ok, messaggio = salva_budget(conn, mese, nome_categoria, importo)
    stampa_esito(ok, messaggio)


def modulo_esporta_csv(conn: Connection) -> None:
    print("\n--- Esporta Spese in CSV ---")

    nome_file = input("Nome file (INVIO per automatico): ").strip()

    # Se l'utente non scrive nulla, genero il nome automatico
    if not nome_file:
        data_oggi = datetime.now().strftime("%d-%m-%Y")
        nome_file = f"Report_Spese_{data_oggi}.csv"
        print(f"Nome file automatico: {nome_file}")
    # inserisco il percorso nella cartella principale
    percorso_output = Path(__file__).resolve().parents[1] / nome_file

    ok, messaggio = esporta_spese_csv(conn, str(percorso_output))
    stampa_esito(ok, messaggio)

# ======================================
# SEZIONE 6 - MENU PRINCIPALE (LOOP)
# ======================================
def main() -> None:
    abilita_colori_windows()

    with ottieni_connessione() as conn:
        inizializza_database(conn)

        while True:
            # Pulizia schermo PRIMA di ristampare il menu principale
            pulisci_schermo()
  
            print("-------------------------")
            print("SISTEMA SPESE PERSONALI")
            print("-------------------------")

            print("\n1. Gestione Categorie")
            print("2. Inserisci Spesa")
            print("3. Modifica Spesa")
            print("4. Elimina Spesa")
            print("5. Definisci Budget Mensile")
            print("6. Visualizza Report")
            print("7. Esporta CSV")
            print("8. Esci")
            scelta = input("Inserisci la tua scelta: ").strip()

            if scelta == "1":
                modulo_gestisci_categorie(conn)
            elif scelta == "2":
                modulo_inserisci_spesa(conn)
            elif scelta == "3":
                modulo_modifica_spesa(conn)
            elif scelta == "4":
                modulo_elimina_spesa(conn)
            elif scelta == "5":
                modulo_definisci_budget(conn)
            elif scelta == "6":
                menu_report(conn)
            elif scelta == "7":
                modulo_esporta_csv(conn)
            elif scelta == "8":
                print("Uscita. Arrivederci!")
                break
            else:
                stampa_errore("Errore: scelta non valida. Riprovare.")


if __name__ == "__main__":
    main()
