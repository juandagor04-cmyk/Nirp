from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file
)

from pathlib import Path
from uuid import uuid4
from datetime import timedelta
from functools import wraps

import os
import secrets
import sqlite3
import math

from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

# ==========================================
# BASE DE DATOS
# ==========================================

from database import (
    crear_tablas,
    crear_tabla_usuarios,
    crear_tabla_perfiles,
    guardar_variedad,
    obtener_variedades,
    obtener_variedad,
    obtener_usuario_correo,
    obtener_usuario_id,
    registrar_usuario_con_perfil,
    obtener_solicitudes_admin,
    aprobar_solicitud_admin,
    crear_tabla_fincas,
    guardar_finca,
    obtener_fincas,
    actualizar_variedad,
    eliminar_variedad,
    obtener_variedades_publicas,
    obtener_variedad_publica,
    obtener_ubicaciones_publicas,
    crear_tabla_inventario,
    obtener_inventarios,
    guardar_inventario,
    eliminar_inventario,
    crear_tablas_actas,
    obtener_actas_inventario,
    generar_acta_inventario,
    obtener_reporte_inventario,
    buscar_inventarios,
    obtener_detalle_acta
)


# ==========================================
# CONFIGURACION GENERAL
# ==========================================

app = Flask(__name__)

app.secret_key = (
    os.environ.get("NIRP_SECRET_KEY")
    or secrets.token_hex(32)
)

app.config.update(
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

CARPETA_FOTOS = (
    Path(app.static_folder)
    / "imagenes"
    / "variedades"
)

CARPETA_FOTOS.mkdir(
    parents=True,
    exist_ok=True
)

Image.MAX_IMAGE_PIXELS = 20_000_000


# ==========================================
# INICIALIZAR BASE DE DATOS
# ==========================================

crear_tablas()
crear_tabla_usuarios()
crear_tabla_perfiles()
crear_tabla_fincas()
crear_tabla_inventario()
crear_tablas_actas()


# ==========================================
# SEGURIDAD DE FORMULARIOS
# ==========================================

def csrf_token():

    if "csrf_token" not in session:
        session["csrf_token"] = (
            secrets.token_urlsafe(32)
        )

    return session["csrf_token"]


@app.context_processor
def funciones_plantilla():

    return {
        "csrf_token": csrf_token
    }


def validar_csrf():

    recibido = request.form.get(
        "csrf_token", ""
    )

    esperado = session.get(
        "csrf_token", ""
    )

    if not recibido or not esperado:
        abort(400)

    if not secrets.compare_digest(
        recibido,
        esperado
    ):
        abort(400)


# ==========================================
# PROTECCION DE ADMINISTRADORES
# ==========================================

def administrador_requerido(funcion):

    @wraps(funcion)
    def protegida(*args, **kwargs):

        usuario_id = session.get("usuario_id")

        if not usuario_id:

            flash(
                "Primero debes iniciar sesión.",
                "warning"
            )

            return redirect(url_for("login"))

        usuario = obtener_usuario_id(usuario_id)

        if not usuario:

            session.clear()

            return redirect(url_for("login"))

        if usuario["rol"] != "admin":
            abort(403)

        return funcion(*args, **kwargs)

    return protegida


# ==========================================
# PAGINA PRINCIPAL
# ==========================================

@app.route("/")
def inicio():

    return render_template(
        "index.html",
        variedades=obtener_variedades_publicas()
    )


# ==========================================
# CATALOGO DE ROSAS
# ==========================================

@app.route("/variedades")
def catalogo():

    usuario = obtener_usuario_id(session["usuario_id"]) if session.get("usuario_id") else None
    if usuario and usuario["rol"] == "admin":
        return render_template("catalogo.html", variedades=obtener_variedades())
    return render_template("catalogo_cliente.html", variedades=obtener_variedades_publicas())


# ==========================================
# REGISTRAR USUARIOS
# ==========================================

@app.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "GET":

        tipo = request.args.get(
            "tipo",
            "cliente"
        )

        if tipo not in ("cliente", "admin"):
            tipo = "cliente"

        return render_template(
            "registro.html",
            tipo=tipo
        )

    validar_csrf()

    tipo = request.form.get(
        "tipo", "cliente"
    )

    nombre = request.form.get(
        "nombre", ""
    ).strip()

    correo = request.form.get(
        "correo", ""
    ).strip().lower()

    telefono = request.form.get(
        "telefono", ""
    ).strip()

    password = request.form.get(
        "password", ""
    )

    confirmar = request.form.get(
        "confirmar", ""
    )

    empresa_finca = request.form.get(
        "empresa_finca", ""
    ).strip()

    cargo = request.form.get(
        "cargo", ""
    ).strip()

    motivo = request.form.get(
        "motivo", ""
    ).strip()

    if tipo not in ("cliente", "admin"):
        abort(400)

    if not nombre or not correo or not telefono:

        flash(
            "Nombre, correo y teléfono son obligatorios.",
            "error"
        )

        return redirect(
            url_for("registro", tipo=tipo)
        )

    if len(password) < 12:

        flash(
            "La contraseña debe tener mínimo 12 caracteres.",
            "error"
        )

        return redirect(
            url_for("registro", tipo=tipo)
        )

    if password != confirmar:

        flash(
            "Las contraseñas no coinciden.",
            "error"
        )

        return redirect(
            url_for("registro", tipo=tipo)
        )

    if tipo == "admin":

        if not empresa_finca or not cargo or not motivo:

            flash(
                "Completa la información administrativa.",
                "error"
            )

            return redirect(
                url_for("registro", tipo="admin")
            )

    try:

        registrar_usuario_con_perfil(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(
                password
            ),
            telefono=telefono,
            empresa_finca=empresa_finca,
            cargo=cargo,
            motivo=motivo,
            solicita_admin=(tipo == "admin")
        )

    except sqlite3.IntegrityError:

        flash(
            "El correo ya está registrado. Inicia sesión.",
            "error"
        )

        return redirect(
            url_for("registro", tipo=tipo)
        )

    if tipo == "admin":

        flash(
            "Cuenta creada. Tu solicitud administrativa "
            "está pendiente de aprobación.",
            "success"
        )

    else:

        flash(
            "¡Registro exitoso! Ya puedes iniciar sesión.",
            "success"
        )

    return redirect(url_for("login"))


# ==========================================
# INICIAR SESION
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    validar_csrf()

    correo = request.form.get(
        "correo", ""
    ).strip().lower()

    password = request.form.get(
        "password", ""
    )

    usuario = obtener_usuario_correo(correo)

    if (
        not usuario
        or not check_password_hash(
            usuario["password_hash"],
            password
        )
    ):

        flash(
            "Correo o contraseña incorrectos.",
            "error"
        )

        return redirect(url_for("login"))

    session.clear()
    session.permanent = True

    session["usuario_id"] = usuario["id"]
    session["nombre"] = usuario["nombre"]
    session["rol"] = usuario["rol"]
    session["csrf_token"] = (
        secrets.token_urlsafe(32)
    )

    flash(
        f"¡Bienvenido a NIRP International, "
        f"{usuario['nombre']}!",
        "success"
    )

    if usuario["rol"] == "admin":
        return redirect(url_for("panel_admin"))

    return redirect(url_for("inicio"))


# ==========================================
# CERRAR SESION
# ==========================================

@app.route("/logout", methods=["POST"])
def logout():

    validar_csrf()

    session.clear()

    flash(
        "Sesión cerrada correctamente.",
        "success"
    )

    return redirect(url_for("login"))


# ==========================================
# PANEL ADMINISTRATIVO
# ==========================================

@app.route("/admin")
@administrador_requerido
def panel_admin():

    variedades = obtener_variedades()
    fincas = obtener_fincas()
    solicitudes = obtener_solicitudes_admin()

    return render_template(
        "panel_admin.html",
        variedades=variedades,
        fincas=fincas,
        solicitudes=solicitudes
    )


# ==========================================
# SOLICITUDES ADMINISTRATIVAS
# ==========================================

@app.route("/admin/solicitudes")
@administrador_requerido
def solicitudes_admin():

    solicitudes = obtener_solicitudes_admin()

    return render_template(
        "solicitudes_admin.html",
        solicitudes=solicitudes
    )


@app.route(
    "/admin/solicitudes/<int:usuario_id>/aprobar",
    methods=["POST"]
)
@administrador_requerido
def aprobar_admin(usuario_id):

    validar_csrf()

    if usuario_id == session.get("usuario_id"):
        abort(400)

    if aprobar_solicitud_admin(usuario_id):

        flash(
            "Solicitud aprobada correctamente.",
            "success"
        )

    else:

        flash(
            "Esa solicitud ya no está pendiente.",
            "warning"
        )

    return redirect(
        url_for("solicitudes_admin")
    )


# ==========================================
# DETALLE DE VARIEDAD
# ==========================================

@app.route("/variedad/<int:id>")
def detalle_variedad(id):

    usuario = (
        obtener_usuario_id(session["usuario_id"])
        if session.get("usuario_id")
        else None
    )

    # VISTA DEL ADMINISTRADOR
    if usuario and usuario["rol"] == "admin":

        rosa = obtener_variedad(id)

        if rosa is None:
            abort(404)

        # Buscar las ubicaciones de esta variedad
        ubicaciones = [
            registro
            for registro in obtener_inventarios()
            if registro["variedad_id"] == id
        ]

        return render_template(
            "detalle_variedad.html",
            rosa=rosa,
            ubicaciones=ubicaciones
        )

    # VISTA PUBLICA DEL CLIENTE
    rosa = obtener_variedad_publica(id)

    if rosa is None:
        abort(404)

    return render_template(
        "detalle_cliente.html",
        rosa=rosa
    )



# ==========================================
# GUARDAR FOTOGRAFIA
# ==========================================

def guardar_fotografia(archivo):

    if not archivo or not archivo.filename:
        return None

    formatos = {
        "JPEG": (".jpg", "JPEG"),
        "PNG": (".png", "PNG"),
        "WEBP": (".webp", "WEBP")
    }

    try:

        imagen = Image.open(archivo.stream)
        imagen.verify()

        archivo.stream.seek(0)

        imagen = Image.open(archivo.stream)
        imagen.load()

        formato = imagen.format

        if formato not in formatos:
            raise ValueError(
                "Formato no permitido"
            )

        extension, tipo_guardado = formatos[formato]

        nombre_archivo = uuid4().hex + extension

        imagen.save(
            CARPETA_FOTOS / nombre_archivo,
            format=tipo_guardado
        )

        return (
            f"imagenes/variedades/"
            f"{nombre_archivo}"
        )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError
    ):

        raise ValueError(
            "La foto debe ser JPG, PNG o WebP válido."
        )
    
# ==========================================
# EDITAR VARIEDAD
# ==========================================

@app.route(
    "/editar-variedad/<int:id>",
    methods=["GET", "POST"]
)
@administrador_requerido
def editar_variedad(id):

    rosa = obtener_variedad(id)

    if rosa is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "editar_variedad.html",
            rosa=rosa
        )

    validar_csrf()

    nombre = request.form.get(
        "nombre", ""
    ).strip()

    color = request.form.get(
        "color", ""
    ).strip()

    if not nombre or not color:
        flash(
            "Nombre y color son obligatorios.",
            "error"
        )
        return redirect(
            url_for("editar_variedad", id=id)
        )

    petalos_texto = request.form.get(
        "petalos", ""
    ).strip()

    try:
        petalos = (
            int(petalos_texto)
            if petalos_texto
            else None
        )
        if petalos is not None and petalos < 0:
            raise ValueError()

    except ValueError:
        flash(
            "El número de pétalos no es válido.",
            "error"
        )
        return redirect(
            url_for("editar_variedad", id=id)
        )

    ruta_imagen = rosa["imagen"]

    archivo = request.files.get("imagen")

    if archivo and archivo.filename:
        try:
            ruta_imagen = guardar_fotografia(
                archivo
            )
        except ValueError as error:
            flash(str(error), "error")
            return redirect(
                url_for("editar_variedad", id=id)
            )

    datos = {
        "nombre": nombre,
        "denominacion": request.form.get(
            "denominacion", ""
        ).strip(),
        "codigo_vbn": request.form.get(
            "codigo_vbn", ""
        ).strip(),
        "color": color,
        "tipo": request.form.get(
            "tipo", ""
        ).strip(),
        "petalos": petalos,
        "tallo": request.form.get(
            "tallo", ""
        ).strip(),
        "vida_florero": request.form.get(
            "vida_florero", ""
        ).strip(),
        "imagen": ruta_imagen
    }

    actualizado = actualizar_variedad(
        id, datos
    )

    if not actualizado:
        abort(404)

    flash(
        "Variedad actualizada correctamente.",
        "success"
    )

    return redirect(
        url_for("panel_admin")
    )

# ==========================================
# ELIMINAR VARIEDAD
# ==========================================

@app.route(
    "/eliminar-variedad/<int:id>",
    methods=["POST"]
)
@administrador_requerido
def eliminar_variedad_ruta(id):

    # Validar seguridad del formulario
    validar_csrf()

    # Buscar la variedad
    rosa = obtener_variedad(id)

    if rosa is None:
        abort(404)

    # Eliminar de la base de datos
    try:
        eliminado = eliminar_variedad(id)

    except sqlite3.IntegrityError:
        flash(
            "No se puede eliminar esta variedad "
            "porque tiene registros relacionados.",
            "error"
        )
        return redirect(
            url_for("panel_admin")
        )

    if not eliminado:
        abort(404)

    flash(
        f"La variedad {rosa['nombre']} "
        "se eliminó correctamente.",
        "success"
    )

    return redirect(
        url_for("panel_admin")
    )




# ==========================================
# REGISTRAR VARIEDAD
# ==========================================

@app.route(
    "/registrar-variedad",
    methods=["GET", "POST"]
)
@administrador_requerido
def registrar_variedad():

    if request.method == "GET":

        return render_template(
            "registrar_variedad.html"
        )

    validar_csrf()

    nombre = request.form.get(
        "nombre", ""
    ).strip()

    color = request.form.get(
        "color", ""
    ).strip()

    if not nombre or not color:

        flash(
            "El nombre y el color son obligatorios.",
            "error"
        )

        return redirect(
            url_for("registrar_variedad")
        )

    petalos_texto = request.form.get(
        "petalos", ""
    ).strip()

    try:

        petalos = (
            int(petalos_texto)
            if petalos_texto
            else None
        )

    except ValueError:

        flash(
            "Número de pétalos inválido.",
            "error"
        )

        return redirect(
            url_for("registrar_variedad")
        )

    if petalos is not None and petalos < 0:

        flash(
            "Los pétalos no pueden ser negativos.",
            "error"
        )

        return redirect(
            url_for("registrar_variedad")
        )

    
    # ==========================================
    # FOTOGRAFIA OBLIGATORIA DE LA VARIEDAD
    # ==========================================

    archivo = request.files.get("imagen")

    if not archivo or not archivo.filename:

        flash(
            "Debes seleccionar una fotografía "
            "de la variedad antes de registrarla.",
            "error"
        )

        return redirect(
            url_for("registrar_variedad")
        )

    try:
        ruta_imagen = guardar_fotografia(archivo)

    except ValueError as error:

        flash(
            str(error),
            "error"
        )

        return redirect(
            url_for("registrar_variedad")
        )


    nueva_rosa = {

        "nombre": nombre,

        "denominacion": request.form.get(
            "denominacion", ""
        ).strip(),

        "codigo_vbn": request.form.get(
            "codigo_vbn", ""
        ).strip(),

        "color": color,

        "tipo": request.form.get(
            "tipo", ""
        ).strip(),

        "petalos": petalos,

        "tallo": request.form.get(
            "tallo", ""
        ).strip(),

        "vida_florero": request.form.get(
            "vida_florero", ""
        ).strip(),

        "imagen": ruta_imagen
    }

    nuevo_id = guardar_variedad(nueva_rosa)

    flash(
        f"¡La variedad {nombre} "
        f"se registró correctamente!",
        "success"
    )

    return redirect(
        url_for(
            "detalle_variedad",
            id=nuevo_id
        )
    )



# ==========================================
# REGISTRAR FINCA
# ==========================================

@app.route(
    "/registrar-finca",
    methods=["GET", "POST"]
)
@administrador_requerido
def registrar_finca():

    if request.method == "GET":
        return render_template(
            "registrar_finca.html"
        )

    # SEGURIDAD DEL FORMULARIO
    validar_csrf()

    # OBTENER INFORMACION DE LA FINCA
    datos = {
        "nombre": request.form.get(
            "nombre", ""
        ).strip(),

        "empresa": request.form.get(
            "empresa", ""
        ).strip(),

        "departamento": request.form.get(
            "departamento", ""
        ).strip(),

        "municipio": request.form.get(
            "municipio", ""
        ).strip(),

        "vereda": request.form.get(
            "vereda", ""
        ).strip(),

        "direccion": request.form.get(
            "direccion", ""
        ).strip(),

        "telefono": request.form.get(
            "telefono", ""
        ).strip(),

        "ubicacion_cultivo": request.form.get(
            "ubicacion_cultivo", ""
        ).strip(),

        "variedades_otras_casas": request.form.get(
            "variedades_otras_casas", ""
        ).strip(),

        "observaciones": request.form.get(
            "observaciones", ""
        ).strip(),

        "latitud": None,
        "longitud": None
    }

    # VALIDAR CAMPOS OBLIGATORIOS
    if (
        not datos["nombre"]
        or not datos["departamento"]
        or not datos["municipio"]
    ):

        flash(
            "Nombre, departamento y municipio "
            "son obligatorios.",
            "error"
        )

        return redirect(
            url_for("registrar_finca")
        )

    # VEREDA Y VARIEDADES EN OTRAS CASAS
    # SON OPCIONALES.
    # PUEDEN QUEDAR VACIAS.

    # OBTENER COORDENADAS
    latitud_texto = request.form.get(
        "latitud", ""
    ).strip()

    longitud_texto = request.form.get(
        "longitud", ""
    ).strip()

    # LAS DOS COORDENADAS DEBEN ESTAR
    # DILIGENCIADAS O LAS DOS VACIAS
    if bool(latitud_texto) != bool(longitud_texto):

        flash(
            "Debes ingresar latitud y longitud juntas.",
            "error"
        )

        return redirect(
            url_for("registrar_finca")
        )

    # VALIDAR COORDENADAS SI SE INGRESARON
    if latitud_texto and longitud_texto:

        try:
            latitud = float(latitud_texto)
            longitud = float(longitud_texto)

            if (
                not math.isfinite(latitud)
                or not math.isfinite(longitud)
                or not -90 <= latitud <= 90
                or not -180 <= longitud <= 180
            ):
                raise ValueError(
                    "Coordenadas fuera de rango."
                )

            datos["latitud"] = latitud
            datos["longitud"] = longitud

        except ValueError:

            flash(
                "Las coordenadas geograficas "
                "no son validas.",
                "error"
            )

            return redirect(
                url_for("registrar_finca")
            )

    # GUARDAR FINCA EN SQLITE
    guardar_finca(datos)

    flash(
        f"¡La finca {datos['nombre']} "
        f"se registró correctamente!",
        "success"
    )

    return redirect(
        url_for("lista_fincas")
    )


# ==========================================
# LISTA DE FINCAS
# ==========================================

@app.route("/fincas")
@administrador_requerido
def lista_fincas():

    fincas = obtener_fincas()

    return render_template(
        "lista_fincas.html",
        fincas=fincas
    )

# ==========================================
# FASE 9 - BUSCADOR DE FINCAS
# ==========================================

@app.route("/admin/buscar-fincas", methods=["GET"])
@administrador_requerido
def buscar_fincas_admin():

    busqueda = request.args.get("q", "").strip()

    if len(busqueda) > 100:
        abort(400, description="Busqueda demasiado larga.")

    # Obtener las fincas registradas
    fincas = obtener_fincas()

    # Filtrar por nombre
    if busqueda:
        fincas = [
            finca for finca in fincas
            if busqueda.casefold()
            in finca["nombre"].casefold()
        ]

    return render_template(
        "buscar_fincas.html",
        fincas=fincas,
        busqueda=busqueda
    )




# ==========================================
# UBICACIONES PUBLICAS: SOLO CAMPOS AUTORIZADOS
# ==========================================

@app.route("/ubicaciones")
def ubicaciones_publicas():
    return render_template(
        "ubicaciones_cliente.html", fincas=obtener_ubicaciones_publicas()
    )


# ==========================================
# FASE 3 - UBICACIONES DE CULTIVO
# SOLO ADMINISTRADORES
# ==========================================

@app.route("/admin/ubicaciones-cultivo", methods=["GET"])
@administrador_requerido
def ubicaciones_cultivo_admin():

    ubicaciones = obtener_inventarios()

    busqueda = request.args.get("q", "").strip()

    if len(busqueda) > 100:
        abort(400, description="Búsqueda demasiado larga.")

    if busqueda:

        texto = busqueda.casefold()

        campos = (
            "finca_nombre",
            "variedad_nombre",
            "casa",
            "bloque",
            "cama"
        )

        ubicaciones = [
            ubicacion for ubicacion in ubicaciones
            if any(
                texto in str(ubicacion.get(campo) or "").casefold()
                for campo in campos
            )
        ]

    total_plantas = sum(
        ubicacion["cantidad"]
        for ubicacion in ubicaciones
    )

    return render_template(
        "ubicaciones_cultivo_admin.html",
        ubicaciones=ubicaciones,
        busqueda=busqueda,
        total_plantas=total_plantas
    )


# ==========================================
# PANEL DE INVENTARIO: ADMINISTRADORES
# ==========================================

@app.route("/admin/inventario", methods=["GET", "POST"])

# ==========================================
# INVENTARIO ADMINISTRATIVO POR UBICACION
# ==========================================

@administrador_requerido
def inventario_admin():

    if request.method == "POST":

        # Seguridad del formulario.
        validar_csrf()

        try:
            finca_id = int(request.form.get("finca_id", ""))
            variedad_id = int(request.form.get("variedad_id", ""))
            cantidad = int(request.form.get("cantidad", ""))
        except (ValueError, TypeError):
            flash(
                "Selecciona una finca, variedad y cantidad valida.",
                "error"
            )
            return redirect(url_for("inventario_admin"))

        if cantidad < 0:
            flash("La cantidad no puede ser negativa.", "error")
            return redirect(url_for("inventario_admin"))

        casa = request.form.get("casa", "").strip()
        bloque = request.form.get("bloque", "").strip()
        cama = request.form.get("cama", "").strip()

        if not casa or not bloque or not cama:
            flash("Debes indicar casa, bloque y cama.", "error")
            return redirect(url_for("inventario_admin"))

        if any(len(valor) > 50 for valor in (casa, bloque, cama)):
            flash(
                "Casa, bloque y cama no pueden superar 50 caracteres cada uno.",
                "error"
            )
            return redirect(url_for("inventario_admin"))

        observaciones = request.form.get("observaciones", "").strip()
        if len(observaciones) > 500:
            flash(
                "Las observaciones no pueden superar 500 caracteres.",
                "error"
            )
            return redirect(url_for("inventario_admin"))

        # Datos tecnicos opcionales de la fecha historica del cultivo.
        # Las fechas tienen el formato AAAA-MM-DD; database.py las valida.
        fecha_siembra = request.form.get("fecha_siembra", "").strip() or None
        propagador = request.form.get("propagador", "").strip()
        numero_camas = request.form.get("numero_camas", "").strip() or None
        densidad_cama = request.form.get("densidad_cama", "").strip() or None
        fecha_primera_cosecha = (
            request.form.get("fecha_primera_cosecha", "").strip() or None
        )

        if len(propagador) > 120:
            flash(
                "El propagador no puede superar 120 caracteres.",
                "error"
            )
            return redirect(url_for("inventario_admin"))

        try:
            guardar_inventario(
                finca_id=finca_id,
                variedad_id=variedad_id,
                cantidad=cantidad,
                observaciones=observaciones,
                casa=casa,
                bloque=bloque,
                cama=cama,
                fecha_siembra=fecha_siembra,
                propagador=propagador,
                numero_camas=numero_camas,
                densidad_cama=densidad_cama,
                fecha_primera_cosecha=fecha_primera_cosecha
            )

        except sqlite3.IntegrityError:
            flash(
                "La finca o la variedad seleccionada no existe.",
                "error"
            )
        except ValueError as error:
            # Las fechas y campos numericos invalidos se notifican aqui.
            flash(str(error), "error")
        else:
            flash("Inventario guardado correctamente.", "success")

        return redirect(url_for("inventario_admin"))

    # Mostrar formulario y registros historicos.
    return render_template(
        "inventario_admin.html",
        fincas=obtener_fincas(),
        variedades=obtener_variedades(),
        inventarios=obtener_inventarios()
    )



@app.route("/admin/inventario/<int:inventario_id>/eliminar", methods=["POST"])
@administrador_requerido
def borrar_inventario_admin(inventario_id):
    validar_csrf()
    if eliminar_inventario(inventario_id):
        flash("Registro de inventario eliminado.", "success")
    else:
        flash("Registro de inventario no encontrado.", "warning")
    return redirect(url_for("inventario_admin"))

# ==========================================
# MANEJO DE ARCHIVOS GRANDES
# ==========================================


@app.errorhandler(RequestEntityTooLarge)
def archivo_demasiado_grande(error):

    flash(
        "El archivo supera el límite de 5 MB.",
        "error"
    )

    return redirect(
        url_for("registrar_variedad")
    )


# ==========================================
# PAGINA DE PRUEBA
# ==========================================

@app.route("/prueba")
def prueba_conexion():

    return (
        "<h1>NIRP International funcionando</h1>"
    )


# ==========================================
# FASE 7 - ACTAS DE INVENTARIO
# SOLO ADMINISTRADORES
# ==========================================

@app.route(
    "/admin/actas",
    methods=["GET", "POST"]
)
@administrador_requerido
def actas_inventario_admin():

    if request.method == "POST":

        # Verificar seguridad del formulario
        validar_csrf()

        try:
            finca_id = int(
                request.form.get("finca_id", "")
            )
        except (ValueError, TypeError):
            flash(
                "Debes seleccionar una finca válida.",
                "error"
            )
            return redirect(
                url_for("actas_inventario_admin")
            )

        fecha_corte = request.form.get(
            "fecha_corte", ""
        ).strip()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        # Obtener el administrador autenticado
        responsable_id = session.get("usuario_id")

        if not responsable_id:
            abort(403)

        # Generar el acta con el inventario actual
        try:
            acta_id = generar_acta_inventario(
                finca_id=finca_id,
                responsable_id=responsable_id,
                fecha_corte=fecha_corte,
                observaciones=observaciones
            )

        except ValueError as error:
            flash(str(error), "error")

        except sqlite3.IntegrityError:
            flash(
                "No se pudo generar el acta. "
                "Comprueba la finca y el administrador.",
                "error"
            )

        else:
            flash(
                f"Acta N.º {acta_id} generada correctamente.",
                "success"
            )

        return redirect(
            url_for("actas_inventario_admin")
        )

    # Mostrar el formulario y el historial
    return render_template(
        "actas_inventario.html",
        fincas=obtener_fincas(),
        actas=obtener_actas_inventario()
    )

# ==========================================
# VER DETALLE DE ACTA DE INVENTARIO
# ==========================================

@app.route("/admin/actas/<int:acta_id>")
@administrador_requerido
def detalle_acta(acta_id):

    resultado = obtener_detalle_acta(acta_id)

    if resultado is None:
        abort(404)

    return render_template(
        "detalle_acta.html",
        acta=resultado["acta"],
        detalles=resultado["detalles"],
        total_registros=resultado["total_registros"],
        total_cantidad=resultado["total_cantidad"]
    )

   
   

# ==========================================
# FASE 8 - REPORTES Y ESTADISTICAS
# SOLO ADMINISTRADORES
# ==========================================

@app.route("/admin/reportes", methods=["GET"])
@administrador_requerido
def reportes_inventario_admin():

    # Consultar las estadisticas actuales
    reporte = obtener_reporte_inventario()

    # Mostrar la pagina de reportes
    return render_template(
        "reportes_inventario.html",
        resumen=reporte["resumen"],
        fincas=reporte["fincas"],
        variedades=reporte["variedades"]
    )

# ==========================================
# FASE 9 - BUSCADOR DE INVENTARIOS
# SOLO ADMINISTRADORES
# ==========================================

@app.route("/admin/buscar-inventario", methods=["GET"])
@administrador_requerido
def buscar_inventario_admin():

    finca_id = request.args.get("finca_id", "").strip()
    variedad = request.args.get("variedad", "").strip()
    casa = request.args.get("casa", "").strip()
    bloque = request.args.get("bloque", "").strip()
    cama = request.args.get("cama", "").strip()

    # Validar el identificador de la finca
    if finca_id:
        try:
            finca_id = int(finca_id)

            if finca_id <= 0:
                raise ValueError()

        except ValueError:
            abort(400, description="Finca no valida.")

    # Limitar la longitud de los filtros
    if any(
        len(valor) > 100
        for valor in (variedad, casa, bloque, cama)
    ):
        abort(400, description="Filtro demasiado largo.")

    # Consultar registros
    inventarios = buscar_inventarios(
        finca_id=finca_id or None,
        variedad=variedad,
        casa=casa,
        bloque=bloque,
        cama=cama
    )

    return render_template(
        "buscar_inventario.html",
        inventarios=inventarios,
        fincas=obtener_fincas(),
        filtros={
            "finca_id": str(finca_id) if finca_id else "",
            "variedad": variedad,
            "casa": casa,
            "bloque": bloque,
            "cama": cama
        }
    )


# ==========================================
# FASE 11 - ESCANER DE INVENTARIOS
# ==========================================

@app.route("/admin/escanear-inventario", methods=["GET"])
@administrador_requerido
def escanear_inventario_admin():

    # Obtener las fincas registradas
    fincas = obtener_fincas()

    # Obtener las variedades registradas
    variedades = obtener_variedades()

    return render_template(
        "escanear_inventario.html",
        fincas=fincas,
        variedades=variedades
    )

# ==========================================
# FASE 5 - INVENTARIO POR VARIEDAD
# SOLO ADMINISTRADORES
# ==========================================

@app.route(
    "/admin/inventario-por-variedad/<int:variedad_id>",
    methods=["GET"]
)
@administrador_requerido
def inventario_por_variedad_admin(variedad_id):

    # Buscar la variedad
    rosa = obtener_variedad(variedad_id)

    if rosa is None:
        abort(404)

    # Obtener los inventarios de esta variedad
    inventarios = [
        registro
        for registro in obtener_inventarios()
        if registro["variedad_id"] == variedad_id
    ]

    # Calcular el total de plantas
    total_plantas = sum(
        registro["cantidad"]
        for registro in inventarios
    )

    return render_template(
        "inventario_por_variedad.html",
        rosa=rosa,
        inventarios=inventarios,
        total_plantas=total_plantas
    )

# ==========================================
# EXPORTAR ACTA A EXCEL
# ==========================================

@app.route(
    "/admin/actas/<int:acta_id>/excel",
    methods=["POST"]
)
@administrador_requerido
def exportar_acta_excel(acta_id):

    import base64
    import binascii
    from io import BytesIO

    from PIL import Image as PILImage
    from openpyxl import Workbook
    from openpyxl.styles import (
        Font, PatternFill, Alignment
    )
    from openpyxl.drawing.image import Image as XLImage

    validar_csrf()

    resultado = obtener_detalle_acta(acta_id)

    if resultado is None:
        abort(404)

    acta = resultado["acta"]
    detalles = resultado["detalles"]

    # Evitar que textos se interpreten
    # como formulas de Excel
    def texto_seguro(valor):
        texto = str(valor) if valor is not None else ""
        if texto.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + texto
        return texto

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Acta de inventario"

    hoja.sheet_view.showGridLines = False

    # ENCABEZADO
    hoja.merge_cells("A1:E1")
    hoja["A1"] = "NIRP INTERNATIONAL - ACTA DE INVENTARIO"
    hoja["A1"].font = Font(
        bold=True, color="FFFFFF", size=15
    )
    hoja["A1"].fill = PatternFill(
        "solid", fgColor="194B30"
    )
    hoja["A1"].alignment = Alignment(
        horizontal="center"
    )
    hoja.row_dimensions[1].height = 35

    # INFORMACION GENERAL
    hoja.append([
        "N.º acta", acta_id,
        "Fecha de corte", texto_seguro(acta["fecha_corte"])
    ])
    hoja.append([
        "Finca", texto_seguro(acta["finca_nombre"]),
        "Empresa", texto_seguro(acta["finca_empresa"])
    ])
    hoja.append([
        "Departamento", texto_seguro(acta["departamento"]),
        "Municipio", texto_seguro(acta["municipio"])
    ])
    hoja.append([
        "Responsable",
        texto_seguro(acta["responsable_nombre"])
    ])

    hoja.append([])

    # TITULOS DE LA TABLA
    encabezados = [
        "Variedad", "Casa", "Bloque",
        "Cama", "Cantidad"
    ]
    hoja.append(encabezados)

    fila_encabezado = hoja.max_row

    for celda in hoja[fila_encabezado]:
        celda.fill = PatternFill(
            "solid", fgColor="E6F2E9"
        )
        celda.font = Font(
            bold=True, color="194B30"
        )

    # INVENTARIO
    inicio = hoja.max_row + 1

    for item in detalles:
        hoja.append([
            texto_seguro(item["variedad_nombre"]),
            texto_seguro(item["casa"]),
            texto_seguro(item["bloque"]),
            texto_seguro(item["cama"]),
            int(item["cantidad"])
        ])

    fin = hoja.max_row

    # TOTAL
    fila_total = hoja.max_row + 1

    hoja.cell(fila_total, 1, "TOTAL DE PLANTAS")

    hoja.cell(
        fila_total, 5,
        f"=SUM(E{inicio}:E{fin})"
        if detalles else 0
    )

    for celda in hoja[fila_total]:
        celda.font = Font(bold=True, color="194B30")
        celda.fill = PatternFill(
            "solid", fgColor="E6F2E9"
        )

    # OBSERVACIONES
    fila_obs = fila_total + 2

    hoja.cell(fila_obs, 1, "OBSERVACIONES")
    hoja.merge_cells(
        start_row=fila_obs + 1,
        start_column=1,
        end_row=fila_obs + 2,
        end_column=5
    )

    hoja.cell(
        fila_obs + 1,
        1,
        texto_seguro(acta["observaciones"] or "Sin observaciones")
    )
    hoja.cell(fila_obs + 1, 1).alignment = Alignment(
        wrap_text=True,
        vertical="top"
    )

    # FIRMAS OPCIONALES
    fila_firmas = fila_obs + 5

    hoja.cell(
        fila_firmas, 1, "Firma del responsable"
    )
    hoja.cell(
        fila_firmas, 4, "Firma de quien verifica"
    )

    hoja.cell(
        fila_firmas + 1,
        1,
        texto_seguro(acta["responsable_nombre"])
    )

    for campo, columna in [
        ("firma_responsable", "A"),
        ("firma_verificador", "D")
    ]:
        contenido = request.form.get(campo, "")

        if not contenido:
            continue

        prefijo = "data:image/png;base64,"

        if (
            not contenido.startswith(prefijo)
            or len(contenido) > 1000000
        ):
            abort(400, description="Firma inválida.")

        try:
            datos = base64.b64decode(
                contenido[len(prefijo):],
                validate=True
            )

            with PILImage.open(BytesIO(datos)) as imagen:
                if (
                    imagen.format != "PNG"
                    or imagen.width > 2000
                    or imagen.height > 2000
                ):
                    abort(400)
                imagen.verify()

            firma = XLImage(BytesIO(datos))
            firma.width = 210
            firma.height = 65

            hoja.add_image(
                firma,
                f"{columna}{fila_firmas + 2}"
            )

        except (
            ValueError, OSError,
            binascii.Error
        ):
            abort(400, description="Firma inválida.")

    # ANCHOS DE COLUMNAS
    anchos = {
        "A": 30,
        "B": 24,
        "C": 22,
        "D": 24,
        "E": 17
    }

    for columna, ancho in anchos.items():
        hoja.column_dimensions[columna].width = ancho

    hoja.freeze_panes = f"A{inicio}"
    hoja.page_setup.orientation = "landscape"
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.page_setup.fitToWidth = 1

    # GENERAR EXCEL
    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"NIRP_Acta_{acta_id:04d}.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

# ==========================================
# EXPORTAR INVENTARIO POR VARIEDAD A EXCEL
# INCLUYE FECHAS HISTORICAS Y DATOS TECNICOS
# ==========================================

@app.route(
    "/admin/inventario-por-variedad/<int:variedad_id>/excel",
    methods=["GET"]
)
@administrador_requerido
def inventario_por_variedad_excel(variedad_id):
    from datetime import date
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    rosa = obtener_variedad(variedad_id)
    if rosa is None:
        abort(404)

    inventarios = [
        registro for registro in obtener_inventarios()
        if registro["variedad_id"] == variedad_id
    ]

    def texto_seguro(valor):
        texto = str(valor) if valor is not None else ""
        if texto.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + texto
        return texto

    def fecha_excel(valor):
        if not valor:
            return None
        try:
            return date.fromisoformat(str(valor))
        except ValueError:
            return texto_seguro(valor)

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Inventario por variedad"
    hoja.sheet_view.showGridLines = False

    verde = "194B30"
    verde_claro = "E6F2E9"
    hoja.merge_cells("A1:J1")
    hoja["A1"] = "NIRP INTERNATIONAL"
    hoja["A1"].font = Font(bold=True, color="FFFFFF", size=16)
    hoja["A1"].fill = PatternFill("solid", fgColor=verde)
    hoja["A1"].alignment = Alignment(horizontal="center", vertical="center")
    hoja.row_dimensions[1].height = 32

    hoja.merge_cells("A2:J2")
    hoja["A2"] = "INVENTARIO TECNICO POR VARIEDAD"
    hoja["A2"].font = Font(bold=True, color=verde, size=13)
    hoja["A2"].alignment = Alignment(horizontal="center")

    hoja["A4"] = "Variedad"
    hoja["B4"] = texto_seguro(rosa["nombre"])
    hoja["D4"] = "Codigo VBN"
    hoja["E4"] = texto_seguro(rosa.get("codigo_vbn"))
    hoja["G4"] = "Denominacion"
    hoja["H4"] = texto_seguro(rosa.get("denominacion"))

    encabezados = [
        "Finca", "Casa", "Bloque", "Cama", "Plantas",
        "Fecha de siembra", "Propagador", "N.o de camas",
        "Densidad por cama", "Primera cosecha"
    ]
    for columna, titulo in enumerate(encabezados, 1):
        celda = hoja.cell(6, columna, titulo)
        celda.fill = PatternFill("solid", fgColor=verde_claro)
        celda.font = Font(bold=True, color=verde)
        celda.alignment = Alignment(wrap_text=True, vertical="center")
    hoja.row_dimensions[6].height = 35

    fila = 7
    for item in inventarios:
        hoja.append([
            texto_seguro(item.get("finca_nombre")),
            texto_seguro(item.get("casa")),
            texto_seguro(item.get("bloque")),
            texto_seguro(item.get("cama")),
            int(item["cantidad"]),
            fecha_excel(item.get("fecha_siembra")),
            texto_seguro(item.get("propagador")),
            item.get("numero_camas"),
            item.get("densidad_cama"),
            fecha_excel(item.get("fecha_primera_cosecha")),
        ])
        for columna in (6, 10):
            hoja.cell(fila, columna).number_format = "DD/MM/YYYY"
        hoja.cell(fila, 5).number_format = "#,##0"
        fila += 1

    if inventarios:
        hoja.auto_filter.ref = f"A6:J{fila - 1}"

    hoja.cell(fila, 1, "TOTAL DE PLANTAS")
    hoja.cell(fila, 5, f"=SUM(E7:E{fila - 1})" if inventarios else 0)
    hoja.cell(fila, 5).number_format = "#,##0"
    for celda in hoja[fila]:
        celda.font = Font(bold=True, color=verde)
        celda.fill = PatternFill("solid", fgColor=verde_claro)

    anchos = {
        "A": 28, "B": 19, "C": 19, "D": 19, "E": 13,
        "F": 20, "G": 27, "H": 16, "I": 20, "J": 20
    }
    for columna, ancho in anchos.items():
        hoja.column_dimensions[columna].width = ancho

    hoja.freeze_panes = "A7"
    hoja.page_setup.orientation = "landscape"
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.page_setup.fitToWidth = 1

    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)
    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"NIRP_Inventario_Variedad_{variedad_id}.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )






# ==========================================
# INICIAR FLASK
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True 
    )
