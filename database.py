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
# ACTUALIZAR VARIEDAD
# ==========================================

def actualizar_variedad(id, rosa):

    with conectar() as conexion:

        cursor = conexion.execute("""
            UPDATE variedades
            SET
                nombre = ?,
                denominacion = ?,
                codigo_vbn = ?,
                color = ?,
                tipo = ?,
                petalos = ?,
                tallo = ?,
                vida_florero = ?,
                imagen = ?
            WHERE id = ?
        """, (
            rosa["nombre"],
            rosa["denominacion"],
            rosa["codigo_vbn"],
            rosa["color"],
            rosa["tipo"],
            rosa["petalos"],
            rosa["tallo"],
            rosa["vida_florero"],
            rosa["imagen"],
            id
        ))

        return cursor.rowcount > 0
    
# ==========================================
# ELIMINAR VARIEDAD
# ==========================================

def eliminar_variedad(id):

    with conectar() as conexion:

        cursor = conexion.execute(
            "DELETE FROM variedades WHERE id = ?",
            (id,)
        )

        return cursor.rowcount > 0




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


# ==========================================
# FASE: CLIENTE PUBLICO - CAMPOS PERMITIDOS
# ==========================================

def obtener_variedades_publicas():
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT id, nombre, imagen
            FROM variedades
            ORDER BY nombre COLLATE NOCASE
        """).fetchall()
        return [dict(fila) for fila in filas]



# ==========================================
# OBTENER DETALLE PUBLICO DE UNA VARIEDAD
# ==========================================

def obtener_variedad_publica(variedad_id):

    with conectar() as conexion:

        fila = conexion.execute("""
            SELECT
                id,
                nombre,
                denominacion,
                codigo_vbn,
                color,
                tipo,
                petalos,
                tallo,
                vida_florero,
                imagen
            FROM variedades
            WHERE id = ?
        """, (variedad_id,)).fetchone()

        return dict(fila) if fila else None


def obtener_ubicaciones_publicas():
    # No publicar telefono, direccion, datos de empresa, ni observaciones.
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT id, nombre, departamento, municipio, latitud, longitud
            FROM fincas
            ORDER BY nombre COLLATE NOCASE
        """).fetchall()
        return [dict(fila) for fila in filas]


# ==========================================
# INVENTARIOS: SOLO CONSUMIR DESDE RUTAS ADMIN
# ==========================================

# ==========================================
# CREAR Y ACTUALIZAR TABLA DE INVENTARIO
# ==========================================


def crear_tabla_inventario():

    with conectar() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS inventarios (
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

                UNIQUE (
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

        columnas = {
            fila["name"]
            for fila in conexion.execute(
                "PRAGMA table_info(inventarios)"
            ).fetchall()
        }

        nuevas_columnas = {
            "casa": "TEXT NOT NULL DEFAULT ''",
            "bloque": "TEXT NOT NULL DEFAULT ''",
            "cama": "TEXT NOT NULL DEFAULT ''"
        }

        for nombre, tipo in nuevas_columnas.items():

            if nombre not in columnas:

                conexion.execute(
                    f"ALTER TABLE inventarios "
                    f"ADD COLUMN {nombre} {tipo}"
                )

    agregar_campos_tecnicos_inventario()
    revisar_y_migrar_unicidad_inventario()



# ==========================================
# COMPATIBILIDAD CON BASES DE DATOS ANTIGUAS
# ==========================================

def revisar_y_migrar_unicidad_inventario():
    """
    En versiones anteriores, un indice UNIQUE sobre (finca_id,
    variedad_id) impedia registrar distintas camas de la misma variedad.
    Si detecta ese esquema, crea un respaldo antes de reconstruir la tabla.
    Conserva todos los ids y registros. No borra ni combina inventarios.
    """
    from datetime import datetime
    from uuid import uuid4

    indice_correcto = [
        "finca_id", "variedad_id", "casa", "bloque", "cama"
    ]
    indice_antiguo = ["finca_id", "variedad_id"]
    columnas_esperadas = {
        "id", "finca_id", "variedad_id", "casa", "bloque",
        "cama", "cantidad", "observaciones", "actualizado_en",
        "fecha_siembra", "propagador", "numero_camas",
        "densidad_cama", "fecha_primera_cosecha"
    }

    conexion = conectar()
    try:
        indices = []
        for indice in conexion.execute(
            "PRAGMA index_list(inventarios)"
        ).fetchall():
            if not indice["unique"]:
                continue
            nombre = indice["name"]
            # name proviene exclusivamente de SQLite, no del usuario.
            nombres = [
                columna["name"]
                for columna in conexion.execute(
                    f'PRAGMA index_info("{nombre}")'
                ).fetchall()
            ]
            indices.append(nombres)

        if indice_correcto in indices and indice_antiguo not in indices:
            return

        if indice_antiguo not in indices:
            raise RuntimeError(
                "El inventario no tiene la restriccion UNIQUE esperada. "
                "No se modificaron sus registros. Revisa la estructura "
                "antes de continuar."
            )

        columnas_actuales = {
            fila["name"] for fila in conexion.execute(
                "PRAGMA table_info(inventarios)"
            ).fetchall()
        }
        if columnas_actuales != columnas_esperadas:
            raise RuntimeError(
                "La tabla inventarios tiene campos diferentes a los "
                "previstos. Por seguridad, no se ha migrado."
            )

        # No reconstruir si existen relaciones, indices o triggers
        # adicionales que podrian verse afectados.
        tablas = conexion.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for tabla in tablas:
            nombre_tabla = tabla["name"]
            nombre_escapado = nombre_tabla.replace('"', '""')
            for relacion in conexion.execute(
                f'PRAGMA foreign_key_list("{nombre_escapado}")'
            ).fetchall():
                if relacion["table"] == "inventarios":
                    raise RuntimeError(
                        "Otra tabla depende de inventarios. "
                        "La migracion automatica se detuvo por seguridad."
                    )

        personalizaciones = conexion.execute(
            "SELECT name FROM sqlite_master "
            "WHERE tbl_name='inventarios' "
            "AND type IN ('index','trigger') AND sql IS NOT NULL"
        ).fetchall()
        if personalizaciones:
            raise RuntimeError(
                "Hay indices o disparadores personalizados en "
                "inventarios. La migracion requiere revision manual."
            )

        repetidos = conexion.execute(
            "SELECT 1 FROM inventarios "
            "GROUP BY finca_id, variedad_id, casa, bloque, cama "
            "HAVING COUNT(*) > 1 LIMIT 1"
        ).fetchone()
        if repetidos:
            raise RuntimeError(
                "Hay ubicaciones duplicadas en inventarios. "
                "No se migro para evitar perdida de registros."
            )

        # Respaldo consistente de SQLite, con nombre unico.
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        copia = DATABASE.with_name(
            f"nirp_antes_de_migrar_{fecha}_{uuid4().hex[:6]}.db"
        )
        destino = sqlite3.connect(copia)
        try:
            conexion.backup(destino)
        finally:
            destino.close()

        try:
            conexion.execute("BEGIN IMMEDIATE")
            conexion.execute("""
                CREATE TABLE inventarios_esquema_nuevo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finca_id INTEGER NOT NULL,
                    variedad_id INTEGER NOT NULL,
                    casa TEXT NOT NULL DEFAULT '',
                    bloque TEXT NOT NULL DEFAULT '',
                    cama TEXT NOT NULL DEFAULT '',
                    cantidad INTEGER NOT NULL DEFAULT 0
                        CHECK (cantidad >= 0),
                    observaciones TEXT NOT NULL DEFAULT '',
                    actualizado_en TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    fecha_siembra TEXT,
                    propagador TEXT,
                    numero_camas INTEGER,
                    densidad_cama REAL,
                    fecha_primera_cosecha TEXT,
                    UNIQUE (finca_id, variedad_id, casa, bloque, cama),
                    FOREIGN KEY (finca_id) REFERENCES fincas(id)
                        ON DELETE RESTRICT,
                    FOREIGN KEY (variedad_id) REFERENCES variedades(id)
                        ON DELETE RESTRICT
                )
            """)
            conexion.execute("""
                INSERT INTO inventarios_esquema_nuevo (
                    id, finca_id, variedad_id, casa, bloque, cama,
                    cantidad, observaciones, actualizado_en, fecha_siembra,
                    propagador, numero_camas, densidad_cama,
                    fecha_primera_cosecha
                )
                SELECT
                    id, finca_id, variedad_id, casa, bloque, cama,
                    cantidad, observaciones, actualizado_en, fecha_siembra,
                    propagador, numero_camas, densidad_cama,
                    fecha_primera_cosecha
                FROM inventarios
            """)
            antes = conexion.execute(
                "SELECT COUNT(*), COALESCE(SUM(cantidad), 0) "
                "FROM inventarios"
            ).fetchone()
            despues = conexion.execute(
                "SELECT COUNT(*), COALESCE(SUM(cantidad), 0) "
                "FROM inventarios_esquema_nuevo"
            ).fetchone()
            if tuple(antes) != tuple(despues):
                raise RuntimeError(
                    "No coincide la cantidad de inventarios. "
                    "La migracion ha sido cancelada."
                )
            conexion.execute("DROP TABLE inventarios")
            conexion.execute(
                "ALTER TABLE inventarios_esquema_nuevo "
                "RENAME TO inventarios"
            )
            errores_fk = conexion.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if errores_fk:
                raise RuntimeError(
                    "Se encontraron referencias invalidas. "
                    "La migracion ha sido cancelada."
                )
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise

        print(
            "NIRP: inventarios migrados al formato por cama. "
            f"Respaldo: {copia.name}"
        )
    finally:
        conexion.close()


# ==========================================
# OBTENER INVENTARIOS REGISTRADOS
# ==========================================

def obtener_inventarios():
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT
                i.id,
                i.finca_id,
                i.variedad_id,
                i.casa,
                i.bloque,
                i.cama,
                i.cantidad,
                i.observaciones,
                i.actualizado_en,
                i.fecha_siembra,
                i.propagador,
                i.numero_camas,
                i.densidad_cama,
                i.fecha_primera_cosecha,
                f.nombre AS finca_nombre,
                v.nombre AS variedad_nombre
            FROM inventarios AS i
            JOIN fincas AS f
                ON f.id = i.finca_id
            JOIN variedades AS v
                ON v.id = i.variedad_id
            ORDER BY
                f.nombre COLLATE NOCASE,
                i.casa,
                i.bloque,
                i.cama
        """).fetchall()

        return [dict(fila) for fila in filas]
    
# ==========================================
# AGREGAR DATOS TECNICOS AL INVENTARIO
# ==========================================

def agregar_campos_tecnicos_inventario():

    campos = {
        "fecha_siembra": "TEXT",
        "propagador": "TEXT",
        "numero_camas": "INTEGER",
        "densidad_cama": "REAL",
        "fecha_primera_cosecha": "TEXT"
    }

    with conectar() as conexion:

        columnas = {
            fila[1]
            for fila in conexion.execute(
                "PRAGMA table_info(inventarios)"
            ).fetchall()
        }

        if not columnas:
            raise RuntimeError(
                "No existe la tabla inventarios."
            )

        for nombre, tipo in campos.items():

            if nombre not in columnas:

                conexion.execute(
                    f"ALTER TABLE inventarios "
                    f"ADD COLUMN {nombre} {tipo}"
                )




# ==========================================
# GUARDAR INVENTARIO POR UBICACION
# ==========================================

def guardar_inventario(
    finca_id,
    variedad_id,
    cantidad,
    observaciones="",
    casa="",
    bloque="",
    cama="",
    fecha_siembra=None,
    propagador="",
    numero_camas=None,
    densidad_cama=None,
    fecha_primera_cosecha=None
):
    """Guarda inventario y datos tecnicos sin borrar campos historicos vacios."""
    from datetime import date
    import math

    casa = str(casa or "").strip()
    bloque = str(bloque or "").strip()
    cama = str(cama or "").strip()
    observaciones = str(observaciones or "").strip()
    propagador = str(propagador or "").strip()

    if not casa or not bloque or not cama:
        raise ValueError("Debes indicar casa, bloque y cama.")

    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError) as error:
        raise ValueError("Debes indicar una cantidad entera valida.") from error
    if cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa.")

    def fecha_opcional(valor, nombre):
        valor = str(valor or "").strip()
        if not valor:
            return None
        try:
            fecha = date.fromisoformat(valor)
        except ValueError as error:
            raise ValueError(f"{nombre} no es una fecha valida (AAAA-MM-DD).") from error
        if fecha > date.today():
            raise ValueError(f"{nombre} no puede ser futura.")
        return fecha.isoformat()

    fecha_siembra = fecha_opcional(fecha_siembra, "La fecha de siembra")
    fecha_primera_cosecha = fecha_opcional(
        fecha_primera_cosecha, "La fecha de primera cosecha"
    )
    if fecha_siembra and fecha_primera_cosecha and fecha_primera_cosecha < fecha_siembra:
        raise ValueError("La primera cosecha no puede ser anterior a la siembra.")

    if numero_camas is None or str(numero_camas).strip() == "":
        numero_camas = None
    else:
        try:
            numero_camas = int(numero_camas)
        except (TypeError, ValueError) as error:
            raise ValueError("El numero de camas debe ser un entero.") from error
        if numero_camas <= 0:
            raise ValueError("El numero de camas debe ser mayor que cero.")

    if densidad_cama is None or str(densidad_cama).strip() == "":
        densidad_cama = None
    else:
        try:
            densidad_cama = float(str(densidad_cama).replace(",", "."))
        except (TypeError, ValueError) as error:
            raise ValueError("La densidad debe ser numerica.") from error
        if not math.isfinite(densidad_cama) or densidad_cama <= 0:
            raise ValueError("La densidad debe ser mayor que cero.")

    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO inventarios (
                finca_id, variedad_id, casa, bloque, cama, cantidad,
                observaciones, fecha_siembra, propagador, numero_camas,
                densidad_cama, fecha_primera_cosecha
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (finca_id, variedad_id, casa, bloque, cama)
            DO UPDATE SET
                cantidad = excluded.cantidad,
                observaciones = excluded.observaciones,
                fecha_siembra = COALESCE(excluded.fecha_siembra, inventarios.fecha_siembra),
                propagador = COALESCE(NULLIF(excluded.propagador, ''), inventarios.propagador),
                numero_camas = COALESCE(excluded.numero_camas, inventarios.numero_camas),
                densidad_cama = COALESCE(excluded.densidad_cama, inventarios.densidad_cama),
                fecha_primera_cosecha = COALESCE(
                    excluded.fecha_primera_cosecha, inventarios.fecha_primera_cosecha
                ),
                actualizado_en = CURRENT_TIMESTAMP
        """, (
            finca_id, variedad_id, casa, bloque, cama, cantidad,
            observaciones, fecha_siembra, propagador, numero_camas,
            densidad_cama, fecha_primera_cosecha
        ))



def eliminar_inventario(inventario_id):
    with conectar() as conexion:
        cursor = conexion.execute(
            "DELETE FROM inventarios WHERE id = ?", (inventario_id,)
        )
        return cursor.rowcount > 0
    
# ==========================================
# CREAR TABLAS DE ACTAS DE INVENTARIO
# ==========================================

def crear_tablas_actas():
    with conectar() as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS actas_inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finca_id INTEGER NOT NULL,
                responsable_id INTEGER NOT NULL,
                fecha_corte TEXT NOT NULL,
                observaciones TEXT NOT NULL DEFAULT '',
                creada_en TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (finca_id)
                    REFERENCES fincas(id)
                    ON DELETE RESTRICT,

                FOREIGN KEY (responsable_id)
                    REFERENCES usuarios(id)
                    ON DELETE RESTRICT
            )
        """)

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS actas_inventario_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acta_id INTEGER NOT NULL,
                variedad_id INTEGER,
                variedad_nombre TEXT NOT NULL,
                casa TEXT NOT NULL,
                bloque TEXT NOT NULL,
                cama TEXT NOT NULL,
                cantidad INTEGER NOT NULL
                    CHECK(cantidad >= 0),

                FOREIGN KEY (acta_id)
                    REFERENCES actas_inventario(id)
                    ON DELETE RESTRICT
            )
        """)


# ==========================================
# OBTENER ACTAS REGISTRADAS
# ==========================================

def obtener_actas_inventario():
    with conectar() as conexion:

        filas = conexion.execute("""
            SELECT
                a.id,
                a.finca_id,
                a.responsable_id,
                a.fecha_corte,
                a.observaciones,
                a.creada_en,
                f.nombre AS finca_nombre,
                u.nombre AS responsable_nombre,

                (
                    SELECT COUNT(*)
                    FROM actas_inventario_detalle AS d
                    WHERE d.acta_id = a.id
                ) AS total_registros,

                (
                    SELECT COALESCE(SUM(d.cantidad), 0)
                    FROM actas_inventario_detalle AS d
                    WHERE d.acta_id = a.id
                ) AS total_cantidad

            FROM actas_inventario AS a

            JOIN fincas AS f
                ON f.id = a.finca_id

            JOIN usuarios AS u
                ON u.id = a.responsable_id

            ORDER BY a.id DESC
        """).fetchall()

        return [dict(fila) for fila in filas]


# ==========================================
# GENERAR ACTA DE INVENTARIO
# ==========================================

def generar_acta_inventario(
    finca_id,
    responsable_id,
    fecha_corte,
    observaciones=""
):
    fecha_corte = str(fecha_corte).strip()
    observaciones = str(observaciones).strip()

    if not fecha_corte:
        raise ValueError(
            "Debes seleccionar una fecha de corte."
        )

    if len(observaciones) > 500:
        raise ValueError(
            "Las observaciones no pueden superar "
            "500 caracteres."
        )

    with conectar() as conexion:

        # Verificar finca
        finca = conexion.execute("""
            SELECT id
            FROM fincas
            WHERE id = ?
        """, (finca_id,)).fetchone()

        if finca is None:
            raise ValueError(
                "La finca seleccionada no existe."
            )

        # Verificar administrador
        responsable = conexion.execute("""
            SELECT id
            FROM usuarios
            WHERE id = ? AND rol = 'admin'
        """, (responsable_id,)).fetchone()

        if responsable is None:
            raise ValueError(
                "El responsable debe ser administrador."
            )

        # Consultar inventario actual de esa finca
        inventarios = conexion.execute("""
            SELECT
                i.variedad_id,
                v.nombre AS variedad_nombre,
                i.casa,
                i.bloque,
                i.cama,
                i.cantidad

            FROM inventarios AS i

            JOIN variedades AS v
                ON v.id = i.variedad_id

            WHERE i.finca_id = ?

            ORDER BY
                v.nombre COLLATE NOCASE,
                i.casa,
                i.bloque,
                i.cama
        """, (finca_id,)).fetchall()

        if not inventarios:
            raise ValueError(
                "La finca no tiene inventarios registrados."
            )

        # Crear encabezado del acta
        cursor = conexion.execute("""
            INSERT INTO actas_inventario (
                finca_id,
                responsable_id,
                fecha_corte,
                observaciones
            )
            VALUES (?, ?, ?, ?)
        """, (
            finca_id,
            responsable_id,
            fecha_corte,
            observaciones
        ))

        acta_id = cursor.lastrowid

        # Guardar copia historic11a de cada registro
        for item in inventarios:

            conexion.execute("""
                INSERT INTO actas_inventario_detalle (
                    acta_id,
                    variedad_id,
                    variedad_nombre,
                    casa,
                    bloque,
                    cama,
                    cantidad
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                acta_id,
                item["variedad_id"],
                item["variedad_nombre"],
                item["casa"],
                item["bloque"],
                item["cama"],
                item["cantidad"]
            ))

        return acta_id
    
# ==========================================
# FASE 8 - REPORTES Y ESTADISTICAS
# ==========================================

def obtener_reporte_inventario():

    with conectar() as conexion:

        # RESUMEN GENERAL
        resumen = conexion.execute("""
            SELECT
                COUNT(*) AS total_registros,
                COALESCE(SUM(cantidad), 0) AS total_rosas,
                COUNT(DISTINCT finca_id)
                    AS fincas_con_inventario,
                COUNT(DISTINCT variedad_id)
                    AS variedades_con_inventario
            FROM inventarios
        """).fetchone()

        # INVENTARIO POR FINCA
        fincas = conexion.execute("""
            SELECT
                f.id,
                f.nombre,
                COUNT(i.id) AS total_registros,
                COALESCE(SUM(i.cantidad), 0) AS total_rosas
            FROM fincas AS f
            LEFT JOIN inventarios AS i
                ON i.finca_id = f.id
            GROUP BY f.id, f.nombre
            ORDER BY total_rosas DESC, f.nombre
        """).fetchall()

        # INVENTARIO POR VARIEDAD
        variedades = conexion.execute("""
            SELECT
                v.id,
                v.nombre,
                COUNT(i.id) AS total_registros,
                COALESCE(SUM(i.cantidad), 0) AS total_rosas
            FROM variedades AS v
            LEFT JOIN inventarios AS i
                ON i.variedad_id = v.id
            GROUP BY v.id, v.nombre
            ORDER BY total_rosas DESC, v.nombre
        """).fetchall()

        return {
            "resumen": dict(resumen),
            "fincas": [dict(fila) for fila in fincas],
            "variedades": [dict(fila) for fila in variedades]
        }

# ==========================================
# FASE 9 - BUSQUEDA DE INVENTARIOS
# ==========================================

def buscar_inventarios(
    finca_id=None,
    variedad="",
    casa="",
    bloque="",
    cama=""
):

    consulta = """
        SELECT
            i.id,
            i.finca_id,
            i.variedad_id,
            i.casa,
            i.bloque,
            i.cama,
            i.cantidad,
            i.observaciones,
            i.actualizado_en,

            f.nombre AS finca_nombre,
            v.nombre AS variedad_nombre

        FROM inventarios AS i

        JOIN fincas AS f
            ON f.id = i.finca_id

        JOIN variedades AS v
            ON v.id = i.variedad_id

        WHERE 1 = 1
    """

    parametros = []

    # Filtrar por finca
    if finca_id not in (None, ""):
        consulta += " AND i.finca_id = ?"
        parametros.append(int(finca_id))

    # Buscar variedad por nombre
    if variedad and variedad.strip():
        consulta += """
            AND LOWER(v.nombre) LIKE ?
        """
        parametros.append(
            "%" + variedad.strip().lower() + "%"
        )

    # Filtrar por casa
    if casa and casa.strip():
        consulta += " AND i.casa = ?"
        parametros.append(casa.strip())

    # Filtrar por bloque
    if bloque and bloque.strip():
        consulta += " AND i.bloque = ?"
        parametros.append(bloque.strip())

    # Filtrar por cama
    if cama and cama.strip():
        consulta += " AND i.cama = ?"
        parametros.append(cama.strip())

    consulta += """
        ORDER BY
            f.nombre COLLATE NOCASE,
            v.nombre COLLATE NOCASE,
            i.casa,
            i.bloque,
            i.cama
    """

    with conectar() as conexion:

        filas = conexion.execute(
            consulta,
            parametros
        ).fetchall()

        return [dict(fila) for fila in filas]

# ==========================================
# FASE 10 - OBTENER DETALLE DE ACTA
# ==========================================

def obtener_detalle_acta(acta_id):

    with conectar() as conexion:

        # Consultar encabezado del acta
        acta = conexion.execute("""
            SELECT
                a.id,
                a.finca_id,
                a.responsable_id,
                a.fecha_corte,
                a.observaciones,
                a.creada_en,
                
                f.nombre AS finca_nombre,
                f.empresa AS finca_empresa,
                f.departamento AS departamento,
                f.municipio AS municipio,
                u.nombre AS responsable_nombre



            FROM actas_inventario AS a

            JOIN fincas AS f
                ON f.id = a.finca_id

            JOIN usuarios AS u
                ON u.id = a.responsable_id

            WHERE a.id = ?
        """, (acta_id,)).fetchone()

        if acta is None:
            return None

        # Consultar copia historica de las variedades
        detalles = conexion.execute("""
            SELECT
                variedad_nombre,
                casa,
                bloque,
                cama,
                cantidad

            FROM actas_inventario_detalle

            WHERE acta_id = ?

            ORDER BY
                variedad_nombre COLLATE NOCASE,
                casa,
                bloque,
                cama
        """, (acta_id,)).fetchall()

        detalles = [dict(fila) for fila in detalles]

        return {
            "acta": dict(acta),
            "detalles": detalles,
            "total_registros": len(detalles),
            "total_cantidad": sum(
                item["cantidad"] for item in detalles
            )
        }

