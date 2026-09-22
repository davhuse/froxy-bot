import sqlite3

conn = sqlite3.connect('runtime_claims.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('Tables:', c.fetchall())

try:
    for row in c.execute("SELECT * FROM runtime_claims LIMIT 20;"):
        print(row)
except Exception as e:
    print('runtime_claims err:', e)
