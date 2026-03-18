import pymysql

def create_database():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='0000'
        )
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS rims_db")
            print("Database 'rims_db' created or already exists.")
        connection.close()
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_database()
