"""Particiones anuales de consulta de actas de NIRP International.

Implementacion manual en SQLite. Las tablas originales siguen siendo la fuente
oficial y NO se modifican. Las particiones son copias fisicas sincronizables.
"""

from datetime import date
import re

from database import conectar

CAMPOS_DETALLE = (
    "id", "acta_id", "variedad_id", "variedad_nombre", "casa",
    "bloque", "cama", "cantidad", "fecha_siembra", "propagador",
    "numero_camas", "densidad_cama", "fecha_primera_cosecha",
)


def _anio_fecha(valor):
    texto = str(valor or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        raise ValueError(f"Fecha de corte no valida: {texto!r}.")
    try:
        return date.fromisoformat(texto).year
    except ValueError as error:
        raise ValueError(f"Fecha de corte no valida: {texto!r}.") from error


def _nombre_tablas(anio):
    if isinstance(anio, bool) or not isinstance(anio, int) or not 1 <= anio <= 9999:
        raise ValueError("El anio seleccionado no es valido.")
    # Las partes dinamicas de los nombres de tablas solo contienen cuatro digitos.
    sufijo = f"{anio:04d}"
    return f"actas_part_{sufijo}", f"actas_detalle_part_{sufijo}"


def _anios_existentes(conexion):
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name LIKE 'actas_part_%'"
    ).fetchall()
    anios = set()
    for fila in filas:
        coincidencia = re.fullmatch(r"actas_part_(\d{4})", fila["name"])
        if coincidencia:
            anios.add(int(coincidencia.group(1)))
    return anios


def _existe_tabla(conexion, nombre):
    return conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (nombre,),
    ).fetchone() is not None


def _crear_tablas_anuales(conexion, anio):
    actas, detalles = _nombre_tablas(anio)
    conexion.execute(f"""
        CREATE TABLE IF NOT EXISTS {actas} (
            id INTEGER PRIMARY KEY,
            finca_id INTEGER NOT NULL,
            responsable_id INTEGER NOT NULL,
            fecha_corte TEXT NOT NULL,
            observaciones TEXT NOT NULL DEFAULT '',
            creada_en TEXT NOT NULL
        )
    """)
    conexion.execute(f"""
        CREATE TABLE IF NOT EXISTS {detalles} (
            id INTEGER PRIMARY KEY,
            acta_id INTEGER NOT NULL,
            variedad_id INTEGER,
            variedad_nombre TEXT NOT NULL,
            casa TEXT NOT NULL,
            bloque TEXT NOT NULL,
            cama TEXT NOT NULL,
            cantidad INTEGER NOT NULL CHECK(cantidad >= 0),
            fecha_siembra TEXT,
            propagador TEXT,
            numero_camas INTEGER,
            densidad_cama REAL,
            fecha_primera_cosecha TEXT,
            FOREIGN KEY(acta_id) REFERENCES {actas}(id) ON DELETE CASCADE
        )
    """)
    conexion.execute(
        f"CREATE INDEX IF NOT EXISTS idx_actas_det_{anio:04d}_acta "
        f"ON {detalles}(acta_id)"
    )


def sincronizar_particiones_actas():
    """Reconstruye particiones fisicas sin tocar las tablas oficiales.

    Todo ocurre en una transaccion. Si hay una fecha invalida o error SQL,
    SQLite revierte la sincronizacion y no altera las actas originales.
    """
    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")
        fechas = conexion.execute(
            "SELECT id, fecha_corte FROM actas_inventario ORDER BY id"
        ).fetchall()
        actuales = {_anio_fecha(fila["fecha_corte"]) for fila in fechas}
        anteriores = _anios_existentes(conexion)
        anios = sorted(actuales | anteriores)
        columnas_origen = {
            fila["name"] for fila in conexion.execute(
                "PRAGMA table_info(actas_inventario_detalle)"
            ).fetchall()
        }
        basicos = set(CAMPOS_DETALLE[:8])
        if not basicos.issubset(columnas_origen):
            raise RuntimeError("La tabla de detalle de actas no tiene los campos basicos.")

        seleccion_detalle = ", ".join(
            f"d.{campo}" if campo in columnas_origen else "NULL"
            for campo in CAMPOS_DETALLE
        )
        columnas_insertar = ", ".join(CAMPOS_DETALLE)

        for anio in anios:
            tabla, detalle = _nombre_tablas(anio)
            _crear_tablas_anuales(conexion, anio)
            conexion.execute(f"DELETE FROM {detalle}")
            conexion.execute(f"DELETE FROM {tabla}")
            if anio not in actuales:
                continue
            sufijo = f"{anio:04d}"
            conexion.execute(f"""
                INSERT INTO {tabla}
                    (id, finca_id, responsable_id, fecha_corte, observaciones, creada_en)
                SELECT id, finca_id, responsable_id, fecha_corte,
                       observaciones, creada_en
                FROM actas_inventario
                WHERE substr(fecha_corte, 1, 4) = ?
            """, (sufijo,))
            conexion.execute(f"""
                INSERT INTO {detalle} ({columnas_insertar})
                SELECT {seleccion_detalle}
                FROM actas_inventario_detalle AS d
                JOIN actas_inventario AS a ON a.id = d.acta_id
                WHERE substr(a.fecha_corte, 1, 4) = ?
            """, (sufijo,))

            origen = conexion.execute(
                "SELECT COUNT(*) AS n FROM actas_inventario "
                "WHERE substr(fecha_corte,1,4) = ?", (sufijo,),
            ).fetchone()["n"]
            copias = conexion.execute(
                f"SELECT COUNT(*) AS n FROM {tabla}"
            ).fetchone()["n"]
            if origen != copias:
                raise RuntimeError("No coincide la cantidad de actas copiadas.")

        return {"anios": len(actuales), "actas": len(fechas)}


def obtener_resumen_particiones_actas():
    """Informacion para la pantalla de administracion y control de sincronizacion."""
    with conectar() as conexion:
        fechas = conexion.execute(
            "SELECT fecha_corte FROM actas_inventario"
        ).fetchall()
        actuales = {_anio_fecha(fila["fecha_corte"]) for fila in fechas}
        anios = sorted(actuales | _anios_existentes(conexion), reverse=True)
        salida = []
        for anio in anios:
            sufijo = f"{anio:04d}"
            tabla, detalle = _nombre_tablas(anio)
            existe = _existe_tabla(conexion, tabla) and _existe_tabla(conexion, detalle)
            origen = conexion.execute("""
                SELECT COUNT(DISTINCT a.id) AS actas,
                       COUNT(d.id) AS registros,
                       COALESCE(SUM(d.cantidad), 0) AS plantas
                FROM actas_inventario AS a
                LEFT JOIN actas_inventario_detalle AS d ON d.acta_id = a.id
                WHERE substr(a.fecha_corte,1,4) = ?
            """, (sufijo,)).fetchone()
            if existe:
                copia = conexion.execute(f"""
                    SELECT COUNT(DISTINCT a.id) AS actas,
                           COUNT(d.id) AS registros,
                           COALESCE(SUM(d.cantidad), 0) AS plantas
                    FROM {tabla} AS a
                    LEFT JOIN {detalle} AS d ON d.acta_id = a.id
                """).fetchone()
            else:
                copia = {"actas": 0, "registros": 0, "plantas": 0}
            igual = existe and all(
                int(origen[campo]) == int(copia[campo])
                for campo in ("actas", "registros", "plantas")
            )
            salida.append({
                "anio": anio,
                "tabla": tabla,
                "detalle": detalle,
                "actas_origen": origen["actas"],
                "actas_particion": copia["actas"],
                "registros_origen": origen["registros"],
                "registros_particion": copia["registros"],
                "plantas_origen": origen["plantas"],
                "plantas_particion": copia["plantas"],
                "sincronizada": igual,
            })
        return salida


def consultar_actas_particionadas(anio):
    """Lee una tabla fisica anual; NO consulta el historial original."""
    tabla, detalle = _nombre_tablas(anio)
    with conectar() as conexion:
        if not (_existe_tabla(conexion, tabla) and _existe_tabla(conexion, detalle)):
            return []
        filas = conexion.execute(f"""
            SELECT a.id, a.fecha_corte,
                   COALESCE(f.nombre, '[Finca no disponible]') AS finca_nombre,
                   COALESCE(u.nombre, '[Usuario no disponible]') AS responsable_nombre,
                   COUNT(d.id) AS total_registros,
                   COALESCE(SUM(d.cantidad), 0) AS total_plantas
            FROM {tabla} AS a
            LEFT JOIN {detalle} AS d ON d.acta_id = a.id
            LEFT JOIN fincas AS f ON f.id = a.finca_id
            LEFT JOIN usuarios AS u ON u.id = a.responsable_id
            GROUP BY a.id, a.fecha_corte, f.nombre, u.nombre
            ORDER BY a.fecha_corte DESC, a.id DESC
        """).fetchall()
        return [dict(fila) for fila in filas]
