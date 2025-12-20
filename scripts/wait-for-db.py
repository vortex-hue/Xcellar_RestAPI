import time
import sys
import os

try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError:
    print("Warning: psycopg2 not installed. Database check skipped.")
    sys.exit(0)

def wait_for_db():
    """Wait for PostgreSQL to be ready"""
    max_attempts = 30
    attempt = 0
    
    db_config = {
        'host': os.environ.get('DB_HOST', 'postgres'),
        'port': os.environ.get('DB_PORT', '5432'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'postgres'),
        'database': os.environ.get('DB_NAME', 'postgres')
    }
    
    ssl_mode = os.environ.get('DB_SSLMODE', os.environ.get('DB_SSL_MODE', 'prefer'))
    if ssl_mode and ssl_mode != 'disable':
        db_config['sslmode'] = ssl_mode
    
    while attempt < max_attempts:
        try:
            conn = psycopg2.connect(**db_config)
            conn.close()
            print("Database is ready!")
            return True
        except OperationalError as e:
            attempt += 1
            if attempt < max_attempts:
                print(f"Waiting for database... ({attempt}/{max_attempts})")
                time.sleep(2)
            else:
                print(f"Database connection failed after {max_attempts} attempts! Error: {e}")
                sys.exit(1)

if __name__ == '__main__':
    wait_for_db()

