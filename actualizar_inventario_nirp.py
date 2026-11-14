"""Actualiza SOLO el inventario tecnico del database.py existente de NIRP.

Uso (en el directorio del proyecto):
    .\\.venv\\Scripts\\python.exe actualizar_inventario_nirp.py

No sustituye database.py por una version antigua. Crea respaldos y conserva filas.
"""

from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import sys

BASE = Path(__file__).resolve().parent
ARCHIVO = BASE / "database.py"

NUEVO_GUARDAR = '''def guardar_inventario(
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
'''

AGREGAR_COLUMNAS = '''# ==========================================
# CAMPOS HISTORICOS DEL CULTIVO - NIRP
# ==========================================

def agregar_campos_tecnicos_inventario():
    """Migracion repetible: agrega columnas sin borrar inventarios."""
    campos = {
        "fecha_siembra": "TEXT",
        "propagador": "TEXT",
        "numero_camas": "INTEGER",
        "densidad_cama": "REAL",
        "fecha_primera_cosecha": "TEXT",
    }
    with conectar() as conexion:
        columnas = {
            fila[1] for fila in conexion.execute("PRAGMA table_info(inventarios)")
        }
        if not columnas:
            raise RuntimeError("No existe la tabla inventarios.")
        for nombre, tipo in campos.items():
            if nombre not in columnas:
                conexion.execute(f"ALTER TABLE inventarios ADD COLUMN {nombre} {tipo}")
'''

NOMBRES_COLUMNAS = (
    "fecha_siembra", "propagador", "numero_camas", "densidad_cama",
    "fecha_primera_cosecha",
)


def funciones_de(codigo):
    arbol = ast.parse(codigo)
    return {
        nodo.name: nodo for nodo in arbol.body if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def reemplazar_funcion(lineas, nodo, reemplazo):
    # Solo se editan lineas de la funcion elegida, no el resto del archivo.
    lineas[nodo.lineno - 1:nodo.end_lineno] = [reemplazo.rstrip() + "\n"]


def preparar_codigo(codigo):
    funciones = funciones_de(codigo)
    requeridas = ("conectar", "crear_tabla_inventario", "obtener_inventarios", "guardar_inventario")
    faltan = [n for n in requeridas if n not in funciones]
    if faltan:
        raise RuntimeError("El database.py tiene funciones diferentes: falta " + ", ".join(faltan))

    lineas = codigo.splitlines(keepends=True)
    cambios = []

    n = funciones["guardar_inventario"]
    viejo = "".join(lineas[n.lineno - 1:n.end_lineno])
    if all(c in viejo for c in NOMBRES_COLUMNAS):
        print("[OK] guardar_inventario ya incluye los datos tecnicos.")
    elif any(c in viejo for c in NOMBRES_COLUMNAS):
        raise RuntimeError("guardar_inventario tiene cambios parciales; no se modificara automaticamente.")
    else:
        if "ON CONFLICT" not in viejo or "INSERT INTO inventarios" not in viejo:
            raise RuntimeError("La funcion guardar_inventario es diferente a la esperada; se detuvo sin cambios.")
        cambios.append((n, NUEVO_GUARDAR))
        print("[OK] Preparada la funcion guardar_inventario con fechas.")

    n = funciones["obtener_inventarios"]
    viejo = "".join(lineas[n.lineno - 1:n.end_lineno])
    if all(("i." + c) in viejo for c in NOMBRES_COLUMNAS):
        print("[OK] obtener_inventarios ya devuelve los datos tecnicos.")
    elif any(("i." + c) in viejo for c in NOMBRES_COLUMNAS):
        raise RuntimeError("obtener_inventarios tiene cambios parciales; no se modificara automaticamente.")
    elif "i.actualizado_en," in viejo:
        sangria = next((s for s in viejo.splitlines() if "i.actualizado_en," in s), None)
        prefix = sangria[:len(sangria) - len(sangria.lstrip())]
        extras = "".join(prefix + "i." + c + ",\n" for c in NOMBRES_COLUMNAS)
        nuevo = viejo.replace("i.actualizado_en,\n", "i.actualizado_en,\n" + extras, 1)
        if nuevo == viejo: 
            raise RuntimeError("No se pudo modificar obtener_inventarios.")
        cambios.append((n, nuevo))
        print("[OK] Preparada la consulta obtener_inventarios con columnas historicas.")
    else:
        raise RuntimeError("No se reconocio la consulta de obtener_inventarios; sin cambios.")

    n = funciones["crear_tabla_inventario"]
    viejo = "".join(lineas[n.lineno - 1:n.end_lineno])
    if "agregar_campos_tecnicos_inventario()" not in viejo:
        nuevo = viejo.rstrip() + "\n\n    agregar_campos_tecnicos_inventario()\n"
        cambios.append((n, nuevo))
        print("[OK] Preparada la migracion para bases nuevas.")

    # Reemplazar de abajo hacia arriba evita desplazar indices de las otras funciones.
    for nodo, nuevo in sorted(cambios, key=lambda x: x[0].lineno, reverse=True):
        reemplazar_funcion(lineas, nodo, nuevo)
    actualizado = "".join(lineas)
    if "def agregar_campos_tecnicos_inventario():" not in actualizado:
        actualizado = actualizado.rstrip() + "\n\n\n" + AGREGAR_COLUMNAS + "\n"
    compile(actualizado, str(ARCHIVO), "exec")
    return actualizado


def main():
    if not ARCHIVO.is_file():
        raise RuntimeError("Pon este archivo junto a app.py y database.py en tu proyecto NIRP.")

    contenido = ARCHIVO.read_text(encoding="utf-8-sig")
    actualizado = preparar_codigo(contenido)

    # El proyecto conocido usa 'nirp.db'. Comprobar antes de hacer cambios.
    bd = BASE / "nirp.db"
    if not bd.is_file():
        raise RuntimeError(
            "No se encontro nirp.db junto a database.py. "
            "Para proteger tus datos, no se crea ni modifica una base nueva."
        )

    with sqlite3.connect(str(bd)) as origen:
        columnas = {fila[1] for fila in origen.execute("PRAGMA table_info(inventarios)")}
        if not columnas:
            raise RuntimeError("La base actual no tiene la tabla inventarios.")
        filas_antes = origen.execute("SELECT COUNT(*) FROM inventarios").fetchone()[0]
        plantas_antes = origen.execute("SELECT COALESCE(SUM(cantidad), 0) FROM inventarios").fetchone()[0]

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    respaldo_codigo = BASE / f"database_respaldo_{marca}.py"
    respaldo_bd = BASE / f"nirp_respaldo_{marca}.db"
    if respaldo_codigo.exists() or respaldo_bd.exists():
        raise RuntimeError("El respaldo ya existe. Ejecuta nuevamente.")

    shutil.copy2(ARCHIVO, respaldo_codigo)
    with sqlite3.connect(str(bd)) as fuente, sqlite3.connect(str(respaldo_bd)) as copia:
        fuente.backup(copia)
    print("[OK] Respaldos creados:")
    print("     ", respaldo_codigo.name)
    print("     ", respaldo_bd.name)

    try:
        ARCHIVO.write_text(actualizado, encoding="utf-8")
        # Evita importar otros modulos del proyecto. La migracion se ejecuta
        # directamente en la misma BD, en una sola transaccion.
        with sqlite3.connect(str(bd)) as conexion:
            columnas = {fila[1] for fila in conexion.execute("PRAGMA table_info(inventarios)")}
            tipos = {
                "fecha_siembra": "TEXT",
                "propagador": "TEXT",
                "numero_camas": "INTEGER",
                "densidad_cama": "REAL",
                "fecha_primera_cosecha": "TEXT",
            }
            for nombre, tipo in tipos.items():
                if nombre not in columnas:
                    conexion.execute(f"ALTER TABLE inventarios ADD COLUMN {nombre} {tipo}")
            filas_despues = conexion.execute("SELECT COUNT(*) FROM inventarios").fetchone()[0]
            plantas_despues = conexion.execute("SELECT COALESCE(SUM(cantidad), 0) FROM inventarios").fetchone()[0]
            if (filas_antes, plantas_antes) != (filas_despues, plantas_despues):
                raise RuntimeError("Cambios inesperados en filas o cantidades; se cancela.")
    except Exception:
        shutil.copy2(respaldo_codigo, ARCHIVO)
        raise

    print("\nActualizacion completada.")
    print(f"Inventarios: {filas_antes} antes y {filas_despues} despues")
    print(f"Plantas: {plantas_antes} antes y {plantas_despues} despues")
    print("Fechas historicas y datos tecnicos disponibles en database.py.")
    print("Siguiente paso: conectar los campos del formulario inventario_admin.html.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\nNO SE COMPLETO LA ACTUALIZACION:", exc, file=sys.stderr)
        sys.exit(1)
