
from getpass import getpass
from sqlite3 import IntegrityError
from werkzeug.security import generate_password_hash

from database import (
    crear_tabla_usuarios,
    guardar_usuario,
    obtener_usuario_correo
)


def crear_administrador():

    crear_tabla_usuarios()

    print("\nNIRP INTERNATIONAL")
    print("CREAR ADMINISTRADOR\n")

    nombre = input("Nombre completo: ").strip()
    correo = input("Correo electrónico: ").strip().lower()

    if not nombre or not correo or "@" not in correo:
        print("Nombre o correo inválidos.")
        return

    if obtener_usuario_correo(correo):
        print("Ya existe una cuenta con ese correo.")
        return

    password = getpass("Contraseña: ")
    confirmar = getpass("Confirmar contraseña: ")

    if password != confirmar:
        print("Las contraseñas no coinciden.")
        return

    if len(password) < 12:
        print("Usa una contraseña de mínimo 12 caracteres.")
        return

    password_hash = generate_password_hash(password)

    try:
        guardar_usuario(
            nombre,
            correo,
            password_hash,
            rol="admin"
        )

    except IntegrityError:
        print("Ese correo ya está registrado.")
        return

    print("\nAdministrador creado correctamente.")
    print("Ya puedes iniciar sesión en NIRP International.")


if __name__ == "__main__":
    crear_administrador()
