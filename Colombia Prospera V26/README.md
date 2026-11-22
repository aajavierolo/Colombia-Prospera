# Colombia Prospera V26

Panel financiero con gastos, ingresos, presupuestos, patrimonio, metas, simulación de deudas e informe PDF.

## Windows

Descomprime la carpeta completa y abre **INICIAR_STREAMLIT.bat**. También puedes abrir **iniciar_altium.bat**.

El iniciador busca Python 3.11 o 3.12. Si hace falta, intenta instalar Python 3.12 mediante Windows Package Manager. Después prepara el entorno `.venv`, instala las dependencias y abre el navegador. El primer inicio necesita Internet. Los siguientes reutilizan lo instalado. Conserva la ventana abierta y usa Ctrl+C para detener el panel.

## macOS y Linux

Instala Python 3.11 o posterior. En una terminal dentro de esta carpeta, ejecuta `python3 preparar_altium.py`. También puedes ejecutar `sh iniciar_altium.sh`.

En las distribuciones que distribuyen venv por separado, instala el paquete de venv correspondiente a tu Python. El primer inicio necesita Internet para descargar las dependencias. El panel muestra la dirección local que debes abrir.

## Datos

Usa **Guardar plantilla en mi Drive** en la pantalla inicial para crear tu copia de [Colombia Prospera V26](https://docs.google.com/spreadsheets/d/1_-RDFht7kevHbSBu57m_mydpx41dEcVcfzb1QVp35Dw/copy). Completa tus datos y carga su enlace público o descarga el Excel y súbelo al panel. Las tablas principales están en las hojas **Gastos** e **Ingresos**. Se admite también la plantilla anterior con **Transaccional**.

También se leen **Datos**, **Historico_presupuesto**, **Patrimonio**, **Pasivos**, **Metas** y **Personales**. La plantilla incluye **Inversiones**, cuya visualización aún no está integrada en el aplicativo, y **Mapeo** como apoyo oculto a los desplegables. Los archivos personales anteriores pueden usar **Dale** como alternativa para el fondo de emergencia y tener referencias de Pasivos a **Enero2025**; la plantilla pública funciona sin esas hojas.

En Gastos, la columna I permite indicar la prioridad de un movimiento y la columna J su acción de control. Los valores vacíos usan la configuración de Datos.

## Docker

Con Docker instalado y funcionando, ejecuta **INSTALAR_DOCKER.bat** en Windows o `docker compose up -d --build` desde esta carpeta. El panel se abre en `http://127.0.0.1:8502`. Para detenerlo, usa **detener_altium_docker.bat** o `docker compose down`.

La configuración construye un único servicio con el código de esta carpeta. Las instrucciones de Docker Hub están en **PUBLICAR_EN_DOCKER_HUB.md**.

## Compartir

Comparte el ZIP de esta versión y pide que lo descompriman antes de iniciar. Cada equipo prepara su propio entorno. Los archivos necesarios son el código, los módulos, las imágenes y los iniciadores incluidos en el ZIP. Las cotizaciones de moneda consultadas por el panel requieren conexión.

## GitHub

El archivo principal es **app.py**. Conserva **requirements.txt**, **modules/**, **imagenes/** y **.streamlit/config.toml**. Los iniciadores, la documentación y los archivos de Docker permiten ejecutar la aplicación por las otras vías descritas arriba.

El **.gitignore** excluye el entorno local, registros, credenciales y archivos financieros. También excluye **plantilla_sheets/**, una automatización histórica del archivo personal que no necesita el aplicativo. La automatización vigente de la plantilla pública está vinculada a su Google Sheets y se conserva al crear una copia en Drive.

Si subes archivos mediante la web de GitHub, selecciona únicamente el código, las imágenes, la documentación y la configuración pública: esa carga manual no aplica las exclusiones de .gitignore.

## Streamlit Community Cloud

Sube el proyecto a GitHub y crea la aplicación en Streamlit Community Cloud. Selecciona el repositorio, la rama correspondiente y **app.py** como archivo principal. En las opciones avanzadas, usa **Python 3.12**, la versión utilizada para las comprobaciones locales.

Si el proyecto está dentro de una subcarpeta del repositorio, indica la ruta completa a su app.py. Conserva requirements.txt, modules/, imagenes/ y .streamlit/config.toml junto al archivo principal. La configuración compartida no fija una dirección local ni un puerto; el iniciador local los configura al ejecutar en Windows.

No se necesitan claves de IA ni credenciales de Google para subir Excel o leer enlaces públicos. Cada usuario carga sus datos en su sesión. Para guardar cambios de forma permanente, debe conservar su archivo o su copia de Google Sheets.

La aplicación se ha comprobado localmente; la validación final en Community Cloud se realiza al completar el primer despliegue.


Carga de datos: permite subir un archivo .xlsx o leer un enlace público de Google Sheets o de un Excel en Drive. Comparte el archivo como «Cualquier persona con el enlace», con lectura y descarga habilitadas. En la aplicación, elige Enlace público de Google y pulsa Cargar / actualizar datos. La lectura trae el libro completo y conserva la lógica de Altium; para ver cambios posteriores vuelve a pulsar el botón. No escribe cambios en Drive. Límite de descarga por enlace: 30 MB.
