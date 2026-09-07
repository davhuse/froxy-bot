import os
import psycopg2

db_url = "postgresql://lisansarena_postgres_user:e48wgkqL8FKVv8XjrxJOpLDm89VpCFgw@dpg-d9uv1orm8hqs73dnet0g-a/lisansarena_postgres"
try:
    conn = psycopg2.connect(db_url, connect_timeout=5)
    print("Database is ALIVE!")
    conn.close()
except Exception as e:
    print("Database error:", e)
