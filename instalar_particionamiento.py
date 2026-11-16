"""Instala la pantalla de particionamiento sin reemplazar app.py ni database.py."""

from datetime import datetime
from pathlib import Path
import shutil

from jinja2 import Environment

RAIZ = Path(__file__).resolve().parent
APP = RAIZ / "app.py"
ACTAS_HTML = RAIZ / "templates" / "actas_inventario.html"
MODULO = RAIZ / "particiones_actas.py"
VISTA = RAIZ / "templates" / "particionamiento_actas.html"

RUTAS = '''
# ==========================================
# PARTICIONAMIENTO MANUAL ANUAL DE ACTAS
# ==========================================

@app.route("/admin/particionamiento-actas", methods=["GET"])
@administrador_requerido
def particionamiento_actas_admin():
    from particiones_actas import (
        obtener_resumen_particiones_actas,
        consultar_actas_particionadas,
    )
    anio_texto = request.args.get("anio", "").strip()
    if anio_texto and (len(anio_texto) != 4 or not anio_texto.isdecimal()):
        abort(400, description="Anio no valido.")
    anio = int(anio_texto) if anio_texto else None
    resumen = obtener_resumen_particiones_actas()
    actas_anio = consultar_actas_particionadas(anio) if anio else []
    return render_template(
        "particionamiento_actas.html",
        resumen=resumen,
        anio_seleccionado=anio,
        actas_anio=actas_anio,
    )


@app.route("/admin/particionamiento-actas/sincronizar", methods=["POST"])
@administrador_requerido
def sincronizar_particionamiento_actas_admin():
    from particiones_actas import sincronizar_particiones_actas
    validar_csrf()
    try:
        resultado = sincronizar_particiones_actas()
    except (ValueError, RuntimeError, sqlite3.DatabaseError) as error:
        flash(f"No se pudieron sincronizar las particiones: {error}", "error")
    else:
        flash(
            f"Sincronizacion completada: {resultado['actas']} actas "
            f"en {resultado['anios']} anios.", "success"
        )
    return redirect(url_for("particionamiento_actas_admin"))

'''

BOTON = '''<h2>Historial de actas</h2>
            <p>
                <a href="{{ url_for('particionamiento_actas_admin') }}" class="actas-boton">
                    Ver particionamiento por año
                </a>
            </p>'''


def main():
    faltantes = [str(x) for x in (APP, ACTAS_HTML, MODULO, VISTA) if not x.exists()]
    if faltantes:
        raise SystemExit("Faltan archivos. Descomprime el ZIP en la carpeta que contiene app.py: "
                         + ", ".join(faltantes))

    original_app = APP.read_text(encoding="utf-8")
    original_html = ACTAS_HTML.read_text(encoding="utf-8")
    if "def particionamiento_actas_admin():" in original_app:
        nuevo_app = original_app
    else:
        marcador = '\nif __name__ == "__main__":'
        if marcador not in original_app:
            raise SystemExit("No encontro el punto de insercion en app.py. No se modifico nada.")
        nuevo_app = original_app.replace(marcador, '\n' + RUTAS + marcador, 1)

    if "url_for('particionamiento_actas_admin')" in original_html:
        nuevo_html = original_html
    else:
        marcador_html = "<h2>Historial de actas</h2>"
        if marcador_html not in original_html:
            raise SystemExit("No encontro 'Historial de actas' en la plantilla. No se modifico nada.")
        nuevo_html = original_html.replace(marcador_html, BOTON, 1)

    # Validar ANTES de guardar los cambios.
    compile(nuevo_app, str(APP), "exec")
    compile(MODULO.read_text(encoding="utf-8"), str(MODULO), "exec")
    env = Environment(autoescape=True)
    env.parse(nuevo_html)
    env.parse(VISTA.read_text(encoding="utf-8"))

    modificados = []
    if original_app != nuevo_app:
        modificados.append((APP, nuevo_app))
    if original_html != nuevo_html:
        modificados.append((ACTAS_HTML, nuevo_html))

    if not modificados:
        print("El particionamiento ya esta instalado. No se modificaron archivos.")
        return

    carpeta_respaldo = RAIZ / "respaldos_particionamiento" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    carpeta_respaldo.mkdir(parents=True, exist_ok=False)
    for archivo, nuevo_contenido in modificados:
        shutil.copy2(archivo, carpeta_respaldo / archivo.name)
        temporal = archivo.with_name(archivo.name + ".temporal_particiones")
        temporal.write_text(nuevo_contenido, encoding="utf-8")
        temporal.replace(archivo)

    print("Instalacion terminada. Archivos modificados:")
    for archivo, _ in modificados:
        print(" -", archivo.relative_to(RAIZ))
    print("Respaldo automatico:", carpeta_respaldo)
    print("No se ha modificado nirp.db.")
    print("Inicia Flask y entra a /admin/actas; abre Particionamiento por anio.")


if __name__ == "__main__":
    main()
