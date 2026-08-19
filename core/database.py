import psycopg2
from psycopg2 import pool
from config.settings import settings


class DatabaseError(RuntimeError):
    """Falla al obtener una conexion utilizable contra la base de datos."""


class DatabaseManager:
    _pool = None

    def _get_pool(self):
        """Devuelve el pool, creandolo en el primer uso.

        La inicializacion es perezosa a proposito: importar este modulo no
        debe exigir una base de datos accesible, porque de eso depende poder
        correr tests y herramientas de evaluacion sin infraestructura viva.
        """
        if DatabaseManager._pool is None:
            self._initialize_pool()
        return DatabaseManager._pool

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
            raise DatabaseError(f"No se pudo inicializar el pool de conexiones: {e}") from e

    def _reset_pool(self):
        """Descarta el pool actual y crea uno nuevo, cerrando el anterior."""
        if DatabaseManager._pool is not None:
            try:
                DatabaseManager._pool.closeall()
            except Exception as e:
                print(f"⚠️ No se pudo cerrar el pool anterior: {e}")
            DatabaseManager._pool = None
        self._initialize_pool()

    def get_connection(self):
        """Obtiene una conexión viva del pool con validación de estado y reintento."""
        conn = None
        for attempt in range(2):
            try:
                conn = self._get_pool().getconn()
                # Validación proactiva mediante una consulta rápida
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return conn
            except Exception as e:
                print(f"⚠️ Reintento {attempt+1}: Conexión dañada ({e}). Re-inicializando...")
                if conn:
                    try:
                        DatabaseManager._pool.putconn(conn, close=True)
                    except Exception:
                        pass
                self._reset_pool()

        conn = self._get_pool().getconn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn

    def release_connection(self, conn):
        """Devuelve la conexión al pool."""
        if DatabaseManager._pool:
            DatabaseManager._pool.putconn(conn)

    def close_all(self):
        """Cierre limpio de todas las conexiones."""
        if DatabaseManager._pool:
            DatabaseManager._pool.closeall()
            DatabaseManager._pool = None
            print("🔌 Todas las conexiones de la DB han sido cerradas.")


# Instancia única para toda la aplicación
db_manager = DatabaseManager()
