
from flask import (
    Flask, render_template, abort, request,
    redirect, url_for, flash, session
)

from pathlib import Path
from uuid import uuid4
from datetime import timedelta
from functools import wraps
import os
import secrets
import sqlite3

from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

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
    aprobar_solicitud_admin
)


# ====================================
# CONFIGURACION GENERAL
# ====================================

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
    Path(app.static_folder) / "imagenes" / "variedades"
)
CARPETA_FOTOS.mkdir(parents=True, exist_ok=True)

Image.MAX_IMAGE_PIXELS = 20_000_000

crear_tablas()
crear_tabla_usuarios()
crear_tabla_perfiles()


# ====================================
# SEGURIDAD DE FORMULARIOS
# ====================================

def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def funciones_plantilla():
    return {"csrf_token": csrf_token}


def validar_csrf():
    recibido = request.form.get("csrf_token", "")
    esperado = session.get("csrf_token", "")

    if not recibido or not esperado:
        abort(400)

    if not secrets.compare_digest(recibido, esperado):
        abort(400)


def administrador_requerido(funcion):

    @wraps(funcion)
    def protegida(*args, **kwargs):
        usuario_id = session.get("usuario_id")

        if not usuario_id:
            flash("Primero debes iniciar sesión.", "warning")
            return redirect(url_for("login"))

        usuario = obtener_usuario_id(usuario_id)

        if not usuario:
            session.clear()
            return redirect(url_for("login"))

        if usuario["rol"] != "admin":
            abort(403)

        return funcion(*args, **kwargs)

    return protegida


# ====================================
# PAGINA PRINCIPAL
# ====================================

@app.route("/")
def inicio():
    return render_template(
        "index.html",
        variedades=obtener_variedades()
    )


# ====================================
# CATALOGO
# ====================================

@app.route("/variedades")
def catalogo():
    return render_template(
        "catalogo.html",
        variedades=obtener_variedades()
    )


# ====================================
# REGISTRO DE USUARIOS
# ====================================

@app.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "GET":
        tipo = request.args.get("tipo", "cliente")

        if tipo not in ("cliente", "admin"):
            tipo = "cliente"

        return render_template("registro.html", tipo=tipo)

    validar_csrf()

    tipo = request.form.get("tipo", "cliente")
    nombre = request.form.get("nombre", "").strip()
    correo = request.form.get("correo", "").strip().lower()
    telefono = request.form.get("telefono", "").strip()
    password = request.form.get("password", "")
    confirmar = request.form.get("confirmar", "")

    empresa_finca = request.form.get(
        "empresa_finca", ""
    ).strip()

    cargo = request.form.get("cargo", "").strip()
    motivo = request.form.get("motivo", "").strip()

    if tipo not in ("cliente", "admin"):
        abort(400)

    if not nombre or not correo or not telefono:
        flash(
            "Nombre, correo y teléfono son obligatorios.",
            "error"
        )
        return redirect(url_for("registro", tipo=tipo))

    if len(password) < 12:
        flash(
            "La contraseña debe tener mínimo 12 caracteres.",
            "error"
        )
        return redirect(url_for("registro", tipo=tipo))

    if password != confirmar:
        flash("Las contraseñas no coinciden.", "error")
        return redirect(url_for("registro", tipo=tipo))

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
        # Todas las cuentas públicas nacen como clientes.
        # Solo otro administrador puede dar acceso admin.
        registrar_usuario_con_perfil(
            nombre=nombre,
            correo=correo,
            password_hash=generate_password_hash(password),
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
        return redirect(url_for("registro", tipo=tipo))

    if tipo == "admin":
        flash(
            "Cuenta creada. Tu solicitud de administrador "
            "está pendiente de aprobación.",
            "success"
        )
    else:
        flash(
            "¡Registro exitoso! Ya puedes iniciar sesión.",
            "success"
        )

    return redirect(url_for("login"))


# ====================================
# INICIAR SESION
# ====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    validar_csrf()

    correo = request.form.get(
        "correo", ""
    ).strip().lower()

    password = request.form.get("password", "")

    usuario = obtener_usuario_correo(correo)

    if (
        not usuario
        or not check_password_hash(
            usuario["password_hash"],
            password
        )
    ):
        flash("Correo o contraseña incorrectos.", "error")
        return redirect(url_for("login"))

    session.clear()
    session.permanent = True

    session["usuario_id"] = usuario["id"]
    session["nombre"] = usuario["nombre"]
    session["rol"] = usuario["rol"]
    session["csrf_token"] = secrets.token_urlsafe(32)

    flash(
        f"¡Bienvenido a NIRP International, "
        f"{usuario['nombre']}!",
        "success"
    )

    if usuario["rol"] == "admin":
        return redirect(url_for("panel_admin"))

    return redirect(url_for("inicio"))


# ====================================
# CERRAR SESION
# ====================================

@app.route("/logout", methods=["POST"])
def logout():
    validar_csrf()
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("login"))


# ====================================
# PANEL ADMINISTRATIVO
# ====================================

@app.route("/admin")
@administrador_requerido
def panel_admin():
    return render_template("panel_admin.html")


# ====================================
# SOLICITUDES DE ADMINISTRADORES
# ====================================

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

    return redirect(url_for("solicitudes_admin"))


# ====================================
# DETALLE DE UNA ROSA
# ====================================

@app.route("/variedad/<int:id>")
def detalle_variedad(id):

    rosa = obtener_variedad(id)

    if rosa is None:
        abort(404)

    return render_template(
        "detalle_variedad.html",
        rosa=rosa
    )


# ====================================
# GUARDAR FOTO
# ====================================

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
            raise ValueError("Formato no permitido")

        extension, tipo_guardado = formatos[formato]
        nombre_archivo = uuid4().hex + extension

        imagen.save(
            CARPETA_FOTOS / nombre_archivo,
            format=tipo_guardado
        )

        return f"imagenes/variedades/{nombre_archivo}"

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError
    ):
        raise ValueError(
            "La foto debe ser JPG, PNG o WebP válido."
        )


# ====================================
# REGISTRAR VARIEDAD
# ====================================

@app.route(
    "/registrar-variedad",
    methods=["GET", "POST"]
)
@administrador_requerido
def registrar_variedad():

    if request.method == "GET":
        return render_template("registrar_variedad.html")

    validar_csrf()

    nombre = request.form.get("nombre", "").strip()
    color = request.form.get("color", "").strip()

    if not nombre or not color:
        flash(
            "El nombre y el color son obligatorios.",
            "error"
        )
        return redirect(url_for("registrar_variedad"))

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
        flash("Número de pétalos inválido.", "error")
        return redirect(url_for("registrar_variedad"))

    if petalos is not None and petalos < 0:
        flash("Los pétalos no pueden ser negativos.", "error")
        return redirect(url_for("registrar_variedad"))

    try:
        ruta_imagen = guardar_fotografia(
            request.files.get("imagen")
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("registrar_variedad"))

    nueva_rosa = {
        "nombre": nombre,
        "denominacion": request.form.get(
            "denominacion", ""
        ).strip(),
        "codigo_vbn": request.form.get(
            "codigo_vbn", ""
        ).strip(),
        "color": color,
        "tipo": request.form.get("tipo", "").strip(),
        "petalos": petalos,
        "tallo": request.form.get("tallo", "").strip(),
        "vida_florero": request.form.get(
            "vida_florero", ""
        ).strip(),
        "imagen": ruta_imagen
    }

    nuevo_id = guardar_variedad(nueva_rosa)

    flash(
        f"¡La variedad {nombre} se registró correctamente!",
        "success"
    )

    return redirect(
        url_for("detalle_variedad", id=nuevo_id)
    )


# ====================================
# MANEJO DE ARCHIVOS GRANDES
# ====================================

@app.errorhandler(RequestEntityTooLarge)
def archivo_demasiado_grande(error):
    flash(
        "El archivo supera el límite de 5 MB.",
        "error"
    )
    return redirect(url_for("registrar_variedad"))


# ====================================
# PRUEBA
# ====================================

@app.route("/prueba")
def prueba_conexion():
    return "<h1>NIRP International funcionando</h1>"


# ====================================
# INICIAR FLASK
# ====================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
