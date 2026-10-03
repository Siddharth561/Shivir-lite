import psycopg

conn = psycopg.connect(
    dbname='postgres', user='postgres', password='7499',
    host='localhost', port='5432', autocommit=True
)
cur = conn.cursor()
cur.execute("""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'shivir_lite' AND pid <> pg_backend_pid()
""")
cur.execute("DROP DATABASE IF EXISTS shivir_lite")
cur.execute("CREATE DATABASE shivir_lite")
print("Database recreated successfully")
conn.close()
