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
    cama=""
):
    casa = str(casa).strip()
    bloque = str(bloque).strip()
    cama = str(cama).strip()
    observaciones = str(observaciones).strip()

    if not casa or not bloque or not cama:
        raise ValueError(
            "Debes indicar casa, bloque y cama."
        )

    cantidad = int(cantidad)

    if cantidad < 0:
        raise ValueError(
            "La cantidad no puede ser negativa."
        )

    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO inventarios (
                finca_id,
                variedad_id,
                casa,
                bloque,
                cama,
                cantidad,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT (
                finca_id,
                variedad_id,
                casa,
                bloque,
                cama
            )
            DO UPDATE SET
                cantidad = excluded.cantidad,
                observaciones = excluded.observaciones,
                actualizado_en = CURRENT_TIMESTAMP
        """, (
            finca_id,
            variedad_id,
            casa,
            bloque,
            cama,
            cantidad,
            observaciones
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

