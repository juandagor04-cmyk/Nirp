
from getpass import getpass
from werkzeug.security import generate_password_hash

from database import conectar, crear_tabla_usuarios

crear_tabla_usuarios()

print("\n=== NIRP INTERNATIONAL ===")
print("CREAR CUENTAS DE PRUEBA\n")

cuentas = [
    ("Administrador de prueba", "admin.prueba@nirp.local", "admin"),
    ("Cliente de prueba", "cliente.prueba@nirp.local", "cliente")
]

with conectar() as conexion:
    for nombre, correo, rol in cuentas:

        existe = conexion.execute(
            "SELECT id FROM usuarios WHERE correo = ?",
            (correo,)
        ).fetchone()

        if existe:
            print(f"Esta cuenta ya existe: {correo}")
            continue

        print(f"\nCreando cuenta: {nombre}")
        password = getpass("Escribe una contraseña de mínimo 12 caracteres: ")

        if len(password) < 12:
            print("Contraseña demasiado corta. Cuenta omitida.")
            continue

        conexion.execute("""
            INSERT INTO usuarios (
                nombre, correo, password_hash, rol
            )
            VALUES (?, ?, ?, ?)
        """, (
            nombre,
            correo,
            generate_password_hash(password),
            rol
        ))

        print(f"Cuenta creada: {correo} ({rol})")

print("\nProceso terminado.")
