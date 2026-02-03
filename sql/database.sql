-- Script SQL: creazione database (SQLite)
-- Vincoli: PRIMARY KEY, FOREIGN KEY, CHECK, UNIQUE, NOT NULL

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS spese;
DROP TABLE IF EXISTS budget;
DROP TABLE IF EXISTS categorie;

CREATE TABLE categorie (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL UNIQUE,
    creato_il       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE spese (
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

CREATE TABLE budget (
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
