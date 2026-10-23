

from flask import Flask, render_template, abort, request, redirect, url_for


# Crear aplicación Flask
app = Flask(__name__)


# VARIEDADES DE DEMOSTRACIÓN

variedades = [
    {
        "id": 1,
        "nombre": "Blueberry®",
        "denominacion": "Nirpber",
        "codigo_vbn": "112329",
        "color": "Lavanda muy oscuro",
        "tipo": "Flor grande (HT)",
        "petalos": 45,
        "tallo": "40-60 cm",
        "vida_florero": "15 días",
        "imagen": "imagenes/blueberry.jpg"
    },
    {
        "id": 2,
        "nombre": "Rosa de prueba",
        "denominacion": "Demostración",
        "codigo_vbn": "No asignado",
        "color": "Rosado",
        "tipo": "Flor grande",
        "petalos": 40,
        "tallo": "Sin registrar",
        "vida_florero": "Sin registrar",
        "imagen": "imagenes/blueberry.jpg"
    }
]



# PAGINA PRINCIPAL
@app.route("/")
def inicio():
    return render_template(
        "index.html",
        variedades=variedades
    )


# FICHA DE CADA VARIEDAD
@app.route("/variedad/<int:id>")
def detalle_variedad(id):

    rosa = next(
        (r for r in variedades if r["id"] == id),
        None
    )

    if rosa is None:
        abort(404)

    return render_template(
        "detalle_variedad.html",
        rosa=rosa
    )

# REGISTRAR NUEVAS VARIEDADES
@app.route("/registrar-variedad", methods=["GET", "POST"])
def registrar_variedad():

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        color = request.form.get("color", "").strip()

        if not nombre or not color:
            return "Nombre y color son obligatorios", 400

        petalos_texto = request.form.get("petalos", "").strip()

        try:
            petalos = int(petalos_texto) if petalos_texto else None
        except ValueError:
            return "Número de pétalos inválido", 400

        if petalos is not None and petalos < 0:
            return "El número de pétalos no puede ser negativo", 400

        nuevo_id = max(
            (rosa["id"] for rosa in variedades),
            default=0
        ) + 1

        nueva_rosa = {
            "id": nuevo_id,
            "nombre": nombre,
            "denominacion": request.form.get("denominacion", "").strip(),
            "codigo_vbn": request.form.get("codigo_vbn", "").strip(),
            "color": color,
            "tipo": request.form.get("tipo", "").strip(),
            "petalos": petalos,
            "tallo": request.form.get("tallo", "").strip(),
            "vida_florero": request.form.get("vida_florero", "").strip(),
            "imagen": "imagenes/blueberry.jpg"
        }

        variedades.append(nueva_rosa)

        return redirect(
            url_for("detalle_variedad", id=nuevo_id)
        )

    return render_template("registrar_variedad.html")


# INICIAR EL SERVIDOR FLASK
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )



