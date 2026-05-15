import psycopg2
from psycopg2 import pool
from config.settings import settings
import sys

class DatabaseManager:
    _pool = None

    def __init__(self):
        if DatabaseManager._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        try:
            # Añadimos parámetros de keepalives para evitar que Neon cierre la conexión por inactividad
            # Estos parámetros mantienen el 'latido' de la conexión SSL
            DatabaseManager._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=settings.DATABASE_URL,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            print("✅ Pool de conexiones (Neon) inicializado con Keep-Alive.")
        except Exception as e:
            print(f"❌ Error crítico inicializando DB: {e}")
            sys.exit(1)

    def get_connection(self):
        """Obtiene una conexión viva del pool con validación de estado y reintento."""
        for attempt in range(2):
            try:
                conn = DatabaseManager._pool.getconn()
                # Validación proactiva: si la conexión está cerrada o dañada, la reponemos
                if conn.closed != 0:
                    print(f"🔄 Reintento {attempt+1}: Detectada conexión cerrada, reponiendo...")
                    DatabaseManager._pool.putconn(conn, close=True)
                    continue
                return conn
            except Exception as e:
                print(f"⚠️ Reintento {attempt+1}: Error obteniendo conexión ({e}). Reiniciando pool...")
                self._initialize_pool()
        
        # Si fallan los reintentos, lanzamos excepción
        return DatabaseManager._pool.getconn()

    def release_connection(self, conn):
        """Devuelve la conexión al pool."""
        if DatabaseManager._pool:
            DatabaseManager._pool.putconn(conn)

    def close_all(self):
        """Cierre limpio de todas las conexiones."""
        if DatabaseManager._pool:
            DatabaseManager._pool.closeall()
            print("🔌 Todas las conexiones de la DB han sido cerradas.")

# Instancia única para toda la aplicación
db_manager = DatabaseManager()
