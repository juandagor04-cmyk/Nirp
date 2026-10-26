
import sqlite3
from pathlib import Path


# ==========================================
# BASE DE DATOS NIRP INTERNATIONAL
# ==========================================

DATABASE = Path(__file__).resolve().parent / "nirp.db"


# ==========================================
# CONEXION A SQLITE
# ==========================================

def conectar():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


# ==========================================
# CREAR TABLA DE VARIEDADES
# ==========================================

def crear_tablas():
    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS variedades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                denominacion TEXT,
                codigo_vbn TEXT,
                color TEXT NOT NULL,
                tipo TEXT,
                petalos INTEGER,
                tallo TEXT,
                vida_florero TEXT,
                imagen TEXT
            )
        """)


# ==========================================
# REGISTRAR NUEVA VARIEDAD
# ==========================================

def guardar_variedad(rosa):
    with conectar() as conexion:
        cursor = conexion.execute("""
            INSERT INTO variedades (
                nombre,
                denominacion,
                codigo_vbn,
                color,
                tipo,
                petalos,
                tallo,
                vida_florero,
                imagen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rosa["nombre"],
            rosa["denominacion"],
            rosa["codigo_vbn"],
            rosa["color"],
            rosa["tipo"],
            rosa["petalos"],
            rosa["tallo"],
            rosa["vida_florero"],
            rosa["imagen"]
        ))

        return cursor.lastrowid


# ==========================================
# OBTENER TODAS LAS VARIEDADES
# ==========================================

def obtener_variedades():
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT * FROM variedades ORDER BY id"
        ).fetchall()

        return [dict(fila) for fila in filas]


# ==========================================
# BUSCAR VARIEDAD POR ID
# ==========================================

def obtener_variedad(id):
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT * FROM variedades WHERE id = ?",
            (id,)
        ).fetchone()

        return dict(fila) if fila else None


# ==========================================
# CREAR TABLA DE USUARIOS
# ==========================================

def crear_tabla_usuarios():
    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'cliente'
                    CHECK (rol IN ('admin', 'cliente'))
            )
        """)


# ==========================================
# BUSCAR USUARIO POR CORREO
# ==========================================

def obtener_usuario_correo(correo):
    with conectar() as conexion:
        fila = conexion.execute("""
            SELECT * FROM usuarios
            WHERE correo = ?
        """, (correo.strip().lower(),)).fetchone()

        return dict(fila) if fila else None


# ==========================================
# BUSCAR USUARIO POR ID
# ==========================================

def obtener_usuario_id(usuario_id):
    with conectar() as conexion:
        fila = conexion.execute("""
            SELECT * FROM usuarios
            WHERE id = ?
        """, (usuario_id,)).fetchone()

        return dict(fila) if fila else None


# ==========================================
# GUARDAR USUARIO
# ==========================================

def guardar_usuario(
    nombre,
    correo,
    password_hash,
    rol="cliente"
):
    if rol not in ("admin", "cliente"):
        raise ValueError("Rol no permitido")

    with conectar() as conexion:
        cursor = conexion.execute("""
            INSERT INTO usuarios (
                nombre,
                correo,
                password_hash,
                rol
            )
            VALUES (?, ?, ?, ?)
        """, (
            nombre.strip(),
            correo.strip().lower(),
            password_hash,
            rol
        ))

        return cursor.lastrowid


# ==========================================
# CREAR TABLA DE PERFILES
# ==========================================

def crear_tabla_perfiles():
    with conectar() as conexion:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS perfiles (
                usuario_id INTEGER PRIMARY KEY,
                telefono TEXT NOT NULL,
                empresa_finca TEXT,
                cargo TEXT,
                motivo TEXT,
                solicita_admin INTEGER NOT NULL DEFAULT 0,
                estado TEXT NOT NULL DEFAULT 'no_aplica'
                    CHECK (
                        estado IN (
                            'no_aplica',
                            'pendiente',
                            'aprobada',
                            'rechazada'
                        )
                    ),
                FOREIGN KEY (usuario_id)
                    REFERENCES usuarios(id)
                    ON DELETE CASCADE
            )
        """)


# ==========================================
# GUARDAR PERFIL
# ==========================================

def guardar_perfil(
    usuario_id,
    telefono="",
    empresa_finca="",
    cargo="",
    motivo="",
    solicita_admin=False
):
    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO perfiles (
                usuario_id,
                telefono,
                empresa_finca,
                cargo,
                motivo,
                solicita_admin,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario_id,
            telefono.strip(),
            empresa_finca.strip(),
            cargo.strip(),
            motivo.strip(),
            1 if solicita_admin else 0,
            "pendiente" if solicita_admin else "no_aplica"
        ))


# ==========================================
# REGISTRAR USUARIO Y PERFIL JUNTOS
# ==========================================

def registrar_usuario_con_perfil(
    nombre,
    correo,
    password_hash,
    telefono,
    empresa_finca="",
    cargo="",
    motivo="",
    solicita_admin=False
):
    # El usuario siempre se registra como cliente.
    # Si solicita ser administrador, debe ser aprobado.

    with conectar() as conexion:
        cursor = conexion.execute("""
            INSERT INTO usuarios (
                nombre,
                correo,
                password_hash,
                rol
            )
            VALUES (?, ?, ?, 'cliente')
        """, (
            nombre.strip(),
            correo.strip().lower(),
            password_hash
        ))

        usuario_id = cursor.lastrowid

        conexion.execute("""
            INSERT INTO perfiles (
                usuario_id,
                telefono,
                empresa_finca,
                cargo,
                motivo,
                solicita_admin,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario_id,
            telefono.strip(),
            empresa_finca.strip(),
            cargo.strip(),
            motivo.strip(),
            1 if solicita_admin else 0,
            "pendiente" if solicita_admin else "no_aplica"
        ))

        return usuario_id


# ==========================================
# CONSULTAR SOLICITUDES ADMINISTRATIVAS
# ==========================================

def obtener_solicitudes_admin():
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT
                u.id,
                u.nombre,
                u.correo,
                p.telefono,
                p.empresa_finca,
                p.cargo,
                p.motivo,
                p.estado
            FROM usuarios AS u
            INNER JOIN perfiles AS p
                ON p.usuario_id = u.id
            WHERE u.rol = 'cliente'
              AND p.solicita_admin = 1
              AND p.estado = 'pendiente'
            ORDER BY u.id
        """).fetchall()

        return [dict(fila) for fila in filas]


# ==========================================
# APROBAR SOLICITUD DE ADMINISTRADOR
# ==========================================

def aprobar_solicitud_admin(usuario_id):
    with conectar() as conexion:

        cursor = conexion.execute("""
            UPDATE usuarios
            SET rol = 'admin'
            WHERE id = ?
              AND rol = 'cliente'
              AND EXISTS (
                  SELECT 1
                  FROM perfiles
                  WHERE perfiles.usuario_id = usuarios.id
                    AND solicita_admin = 1
                    AND estado = 'pendiente'
              )
        """, (usuario_id,))

        if cursor.rowcount != 1:
            return False

        conexion.execute("""
            UPDATE perfiles
            SET estado = 'aprobada'
            WHERE usuario_id = ?
        """, (usuario_id,))

        return True


# ==========================================
# CREAR TABLA DE FINCAS
# ==========================================

def crear_tabla_fincas():
    with conectar() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS fincas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                empresa TEXT,
                departamento TEXT NOT NULL,
                municipio TEXT NOT NULL,
                vereda TEXT,
                direccion TEXT,
                telefono TEXT,
                ubicacion_cultivo TEXT,
                variedades_otras_casas TEXT,
                latitud REAL,
                longitud REAL,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Revisar la estructura de la tabla existente.
        columnas = {
            fila["name"]
            for fila in conexion.execute(
                "PRAGMA table_info(fincas)"
            ).fetchall()
        }

        # Agregar campos nuevos sin borrar las fincas.
        columnas_nuevas = {
            "telefono": "TEXT",
            "ubicacion_cultivo": "TEXT",
            "variedades_otras_casas": "TEXT"
        }

        for nombre, tipo in columnas_nuevas.items():
            if nombre not in columnas:
                conexion.execute(
                    f"ALTER TABLE fincas ADD COLUMN {nombre} {tipo}"
                )


# ==========================================
# GUARDAR FINCA
# ==========================================

def guardar_finca(datos):
    with conectar() as conexion:

        cursor = conexion.execute("""
            INSERT INTO fincas (
                nombre,
                empresa,
                departamento,
                municipio,
                vereda,
                direccion,
                telefono,
                ubicacion_cultivo,
                variedades_otras_casas,
                latitud,
                longitud,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datos["nombre"],
            datos.get("empresa", ""),
            datos["departamento"],
            datos["municipio"],
            datos.get("vereda", ""),
            datos.get("direccion", ""),
            datos.get("telefono", ""),
            datos.get("ubicacion_cultivo", ""),
            datos.get("variedades_otras_casas", ""),
            datos.get("latitud"),
            datos.get("longitud"),
            datos.get("observaciones", "")
        ))

        return cursor.lastrowid


# ==========================================
# OBTENER TODAS LAS FINCAS
# ==========================================

def obtener_fincas():
    with conectar() as conexion:

        filas = conexion.execute("""
            SELECT *
            FROM fincas
            ORDER BY id DESC
        """).fetchall()

        return [dict(fila) for fila in filas]


# ==========================================
# BUSCAR FINCA POR ID
# ==========================================

def obtener_finca(finca_id):
    with conectar() as conexion:

        fila = conexion.execute("""
            SELECT *
            FROM fincas
            WHERE id = ?
        """, (finca_id,)).fetchone()

        return dict(fila) if fila else None


# ==========================================
# PREPARAR BASE DE DATOS
# ==========================================

if __name__ == "__main__":

    crear_tablas()
    crear_tabla_usuarios()
    crear_tabla_perfiles()
    crear_tabla_fincas()

    print("====================================")
    print("NIRP INTERNATIONAL")
    print("Base de datos preparada correctamente.")
    print("Tablas:")
    print("- variedades")
    print("- usuarios")
    print("- perfiles")
    print("- fincas")
    print("====================================")
