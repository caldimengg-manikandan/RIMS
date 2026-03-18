import pyodbc

servers = [
    "localhost",
    "DESKTOP-N08RTTR",
    "(local)",
    "(localdb)\\MSSQLLocalDB"
]


for server in servers:
    try:
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=RIMS_DB;Trusted_Connection=yes;"
        print(f"Trying to connect to {server}...")
        conn = pyodbc.connect(conn_str, timeout=3)
        print(f"SUCCESS! Connected to {server}")
        conn.close()
        break
    except Exception as e:
        print(f"Failed to connect to {server}: {str(e)}")
