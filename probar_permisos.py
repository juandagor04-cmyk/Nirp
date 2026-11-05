
# ==========================================
# NIRP INTERNATIONAL
# PRUEBAS DE PERMISOS DE CLIENTE
# ==========================================

from app import app
from database import conectar

# Buscar una cuenta de cliente existente
with conectar() as conexion:
    usuario = conexion.execute(
        """
        SELECT id, nombre
        FROM usuarios
        WHERE rol = ?
        LIMIT 1
        """,
        ("cliente",)
    ).fetchone()

if usuario is None:
    print("No se encontró una cuenta de cliente.")

else:
    print("Cliente encontrado:", usuario["nombre"])

    cliente = app.test_client()

    # Crear sesión de prueba
    with cliente.session_transaction() as sesion:
        sesion["usuario_id"] = usuario["id"]
        sesion["rol"] = "cliente"

    # Rutas y resultados esperados
    pruebas = {
        "/admin": 403,
        "/admin/inventario": 403,
        "/registrar-variedad": 403,
        "/registrar-finca": 403,
        "/fincas": 403,
        "/variedades": 200,
        "/ubicaciones": 200,
    }

    print("\nRESULTADOS DE SEGURIDAD")
    print("=" * 45)

    for ruta, esperado in pruebas.items():

        respuesta = cliente.get(ruta)

        estado = (
            "CORRECTO"
            if respuesta.status_code == esperado
            else "REVISAR"
        )

        print(
            f"{estado} | {ruta} | "
            f"Resultado: {respuesta.status_code} | "
            f"Esperado: {esperado}"
        )

    print("=" * 45)
    print("Prueba finalizada.")
