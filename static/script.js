
document.addEventListener("DOMContentLoaded", function () {

    // MENU DEL CELULAR
    const botonMenu = document.getElementById("menuBoton");
    const menu = document.getElementById("menu");

    if (botonMenu && menu) {

        // Abrir y cerrar el menu
        botonMenu.addEventListener("click", function () {

            const abierto = menu.classList.toggle("abierto");

            botonMenu.setAttribute(
                "aria-expanded",
                String(abierto)
            );

            botonMenu.textContent = abierto ? "✕" : "☰";
        });

        // Cerrar el menu al seleccionar una opcion
        menu.querySelectorAll("a").forEach(function (enlace) {

            enlace.addEventListener("click", function () {

                menu.classList.remove("abierto");

                botonMenu.setAttribute(
                    "aria-expanded",
                    "false"
                );

                botonMenu.textContent = "☰";
            });
        });
    }

    // ANIMACION DEL LOGO ORIGINAL
    const intro = document.getElementById("intro");

    if (intro) {
        intro.addEventListener("animationend", function (evento) {

            if (evento.animationName === "salir") {
                intro.remove();
            }

        });
    }

});
