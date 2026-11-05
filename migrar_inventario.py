
import sqlite3
from database import conectar


def migrar_inventario():

    with conectar() as conexion:

        # Comprobar que la tabla existe
        tabla = conexion.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'inventarios'
        """).fetchone()

        if tabla is None:
            print("No existe la tabla inventarios.")
            return

        # Evitar repetir la migracion
        version = conexion.execute(
            "PRAGMA user_version"
        ).fetchone()[0]

        if version >= 2:
            print("Migracion ya registrada.")
            return

        # Verificar que no haya inventarios existentes
        cantidad = conexion.execute(
            "SELECT COUNT(*) FROM inventarios"
        ).fetchone()[0]

        if cantidad != 0:
            print(
                "Migracion detenida: existen "
                "inventarios que deben conservarse."
            )
            return

        # Crear la nueva tabla
        conexion.execute("""
            CREATE TABLE inventarios_nuevo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finca_id INTEGER NOT NULL,
                variedad_id INTEGER NOT NULL,
                casa TEXT NOT NULL DEFAULT '',
                bloque TEXT NOT NULL DEFAULT '',
                cama TEXT NOT NULL DEFAULT '',
                cantidad INTEGER NOT NULL DEFAULT 0
                    CHECK(cantidad >= 0),
                observaciones TEXT NOT NULL DEFAULT '',
                actualizado_en TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(
                    finca_id,
                    variedad_id,
                    casa,
                    bloque,
                    cama
                ),

                FOREIGN KEY (finca_id)
                    REFERENCES fincas(id)
                    ON DELETE RESTRICT,

                FOREIGN KEY (variedad_id)
                    REFERENCES variedades(id)
                    ON DELETE RESTRICT
            )
        """)

        # Sustituir solamente la tabla vacia
        conexion.execute("DROP TABLE inventarios")

        conexion.execute("""
            ALTER TABLE inventarios_nuevo
            RENAME TO inventarios
        """)

        conexion.execute("PRAGMA user_version = 2")

        print(
            "Migracion completada correctamente."
        )


if __name__ == "__main__":
    try:
        migrar_inventario()
    except sqlite3.Error as error:
        print("Error durante la migracion:", error)
        raise
