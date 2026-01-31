import sqlite3
from datetime import datetime

import os
from pathlib import Path

# Use a default path for local development, will be overridden by the app
DB_NAME = 'medications.db'

def set_db_path(data_path):
    global DB_NAME
    if data_path:
        DB_NAME = os.path.join(data_path, 'medications.db')
        print(f"DEBUG: Database path set to: {DB_NAME}")


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        pieces_per_box INTEGER NOT NULL,
        current_boxes INTEGER NOT NULL DEFAULT 0,
        current_pieces INTEGER NOT NULL DEFAULT 0,
        inventory_date TEXT
    )''')
    
    # Check if inventory_date column exists (for existing databases)
    c.execute("PRAGMA table_info(medications)")
    columns = [col[1] for col in c.fetchall()]
    if 'inventory_date' not in columns:
        c.execute("ALTER TABLE medications ADD COLUMN inventory_date TEXT")

    c.execute('''CREATE TABLE IF NOT EXISTS dosages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        med_id INTEGER NOT NULL,
        dosage_per_day INTEGER NOT NULL,
        FOREIGN KEY (med_id) REFERENCES medications(id)
    )''')
    conn.commit()
    conn.close()

def add_medication(name, med_type, pieces_per_box, current_boxes=0, current_pieces=0, dosage=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    inv_date = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO medications (name, type, pieces_per_box, current_boxes, current_pieces, inventory_date) VALUES (?, ?, ?, ?, ?, ?)",
              (name, med_type, pieces_per_box, current_boxes, current_pieces, inv_date))
    med_id = c.lastrowid
    c.execute("INSERT INTO dosages (med_id, dosage_per_day) VALUES (?, ?)", (med_id, dosage))
    conn.commit()
    conn.close()
    return med_id

def get_all_medications():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT m.id, m.name, m.type, m.pieces_per_box, m.current_boxes, m.current_pieces, d.dosage_per_day, m.inventory_date
        FROM medications m
        LEFT JOIN dosages d ON m.id = d.med_id
    """)
    meds = c.fetchall()
    conn.close()
    return meds

def update_medication(med_id, name, med_type, pieces_per_box, current_boxes, current_pieces, dosage=0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    inv_date = datetime.now().strftime("%Y-%m-%d")
    c.execute("UPDATE medications SET name=?, type=?, pieces_per_box=?, current_boxes=?, current_pieces=?, inventory_date=? WHERE id=?",
              (name, med_type, pieces_per_box, current_boxes, current_pieces, inv_date, med_id))
    
    c.execute("SELECT id FROM dosages WHERE med_id = ?", (med_id,))
    if c.fetchone():
        c.execute("UPDATE dosages SET dosage_per_day = ? WHERE med_id = ?", (dosage, med_id))
    else:
        c.execute("INSERT INTO dosages (med_id, dosage_per_day) VALUES (?, ?)", (med_id, dosage))
    
    conn.commit()
    conn.close()

def delete_medication(med_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM medications WHERE id=?", (med_id,))
    c.execute("DELETE FROM dosages WHERE med_id=?", (med_id,))
    conn.commit()
    conn.close()

def update_stock(med_id, boxes, pieces):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    inv_date = datetime.now().strftime("%Y-%m-%d")
    c.execute("UPDATE medications SET current_boxes = ?, current_pieces = ?, inventory_date = ? WHERE id = ?", (boxes, pieces, inv_date, med_id))
    conn.commit()
    conn.close()

def export_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT m.name, m.type, m.pieces_per_box, m.current_boxes, m.current_pieces, d.dosage_per_day
        FROM medications m
        LEFT JOIN dosages d ON m.id = d.med_id
    """)
    rows = c.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'name': row[0],
            'type': row[1],
            'pieces_per_box': row[2],
            'current_boxes': row[3],
            'current_pieces': row[4],
            'dosage_per_day': row[5]
        })
    return data

def import_data(data_list, inventory_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Clear existing data
    c.execute("DELETE FROM medications")
    c.execute("DELETE FROM dosages")
    c.execute("DELETE FROM sqlite_sequence WHERE name IN ('medications', 'dosages')")
    
    for item in data_list:
        c.execute("INSERT INTO medications (name, type, pieces_per_box, current_boxes, current_pieces, inventory_date) VALUES (?, ?, ?, ?, ?, ?)",
                  (item['name'], item['type'], item['pieces_per_box'], item['current_boxes'], item['current_pieces'], inventory_date))
        med_id = c.lastrowid
        c.execute("INSERT INTO dosages (med_id, dosage_per_day) VALUES (?, ?)", (med_id, item['dosage_per_day']))
    
    conn.commit()
    conn.close()
