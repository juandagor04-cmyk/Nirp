
from flask import (
    Flask,
    render_template,
    abort,
    request,
    redirect,
    url_for,
    flash,
    session
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
    eliminar_variedad
    
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
        variedades=obtener_variedades()
    )


# ==========================================
# CATALOGO DE ROSAS
# ==========================================

@app.route("/variedades")
def catalogo():

    return render_template(
        "catalogo.html",
        variedades=obtener_variedades()
    )


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

    rosa = obtener_variedad(id)

    if rosa is None:
        abort(404)

    return render_template(
        "detalle_variedad.html",
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
# INICIAR FLASK
# ==========================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
