#!/usr/bin/env python3
"""Импорт базы aioke/barcodes (1.8 млн штрихкодов рос. рынка, без еды/одежды/лекарств)
из barcodes_csv.zip в products.db. Даёт покрытие по не-еде (косметика, бытовое и пр.).
OFF-записи не перезаписывает (INSERT OR IGNORE).
"""
import csv
import io
import sqlite3
import sys
import zipfile

DB = "products.db"
ZIP = sys.argv[1] if len(sys.argv) > 1 else "barcodes_csv.zip"


def main():
    db = sqlite3.connect(DB, timeout=180)
    from off_import import SCHEMA
    db.executescript(SCHEMA)
    with zipfile.ZipFile(ZIP) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text, delimiter=";")
            print("Колонки:", reader.fieldnames)
            batch, n = [], 0
            for row in reader:
                bc = (row.get("Barcode") or row.get("barcode") or "").strip()
                if not bc.isdigit() or len(bc) < 8:
                    continue
                nm = (row.get("Name") or row.get("name") or "").strip()
                vendor = (row.get("Vendor") or row.get("vendor") or "").strip() or None
                cat = (row.get("Category") or row.get("category") or "").strip() or None
                batch.append((bc, nm, vendor, cat))
                if len(batch) >= 50000:
                    n += insert(db, batch)
                    batch = []
                    print(n)
            n += insert(db, batch)
    db.commit()
    print("Добавлено:", n)


def insert(db, batch):
    c = db.executemany(
        """INSERT OR IGNORE INTO products (barcode, name, brand, categories, source)
           VALUES (?,?,?,?, 'aioke')""", batch)
    db.commit()
    return c.rowcount


if __name__ == "__main__":
    main()
