import sqlite3
import os

for db in ['runtime_claims.db', 'orders.db', 'sales.db']:
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cur.fetchall()
            print(f"=== {db} ===")
            for t in tables:
                tname = t[0]
                cur.execute(f"SELECT count(*) FROM {tname}")
                print(f"  Table {tname}: {cur.fetchone()[0]} rows")
                cur.execute(f"SELECT * FROM {tname} LIMIT 3")
                print(f"    Sample: {cur.fetchall()}")
            conn.close()
        except Exception as e:
            print(f"Error {db}: {e}")
