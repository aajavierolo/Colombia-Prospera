# Altium Financiero V26

Panel financiero con gastos, ingresos, presupuestos, patrimonio, metas, simulación de deudas e informe PDF.

## Windows

Descomprime la carpeta completa y abre **INICIAR_STREAMLIT.bat**. También puedes abrir **iniciar_altium.bat**.

El iniciador busca Python 3.11 o 3.12. Si hace falta, intenta instalar Python 3.12 mediante Windows Package Manager. Después prepara el entorno `.venv`, instala las dependencias y abre el navegador. El primer inicio necesita Internet. Los siguientes reutilizan lo instalado. Conserva la ventana abierta y usa Ctrl+C para detener el panel.

## macOS y Linux

Instala Python 3.11 o posterior. En una terminal dentro de esta carpeta, ejecuta `python3 preparar_altium.py`. También puedes ejecutar `sh iniciar_altium.sh`.

En las distribuciones que distribuyen venv por separado, instala el paquete de venv correspondiente a tu Python. El primer inicio necesita Internet para descargar las dependencias. El panel muestra la dirección local que debes abrir.

## Datos

Exporta tu Google Sheets como archivo Excel y cárgalo desde el panel. Las tablas principales están en las hojas **Gastos** e **Ingresos**. Se admite también la plantilla anterior con **Transaccional**.

También se leen **Datos**, **Historico_presupuesto**, **Patrimonio**, **Pasivos**, **Metas** y **Personales**. **Dale** sirve de apoyo al fondo de emergencia cuando su valor en Patrimonio llega en cero. Las automatizaciones de Sheets utilizan **Mapeo**. Revisa las fórmulas de Pasivos antes de modificar **Enero2025**, porque actualmente la consultan.

En Gastos, la columna I permite indicar la prioridad de un movimiento y la columna J su acción de control. Los valores vacíos usan la configuración de Datos.

## Docker

Con Docker instalado y funcionando, ejecuta **INSTALAR_DOCKER.bat** en Windows o `docker compose up -d --build` desde esta carpeta. El panel se abre en `http://127.0.0.1:8502`. Para detenerlo, usa **detener_altium_docker.bat** o `docker compose down`.

La configuración construye un único servicio con el código de esta carpeta. Las instrucciones de Docker Hub están en **PUBLICAR_EN_DOCKER_HUB.md**.

## Compartir

Comparte el ZIP de esta versión y pide que lo descompriman antes de iniciar. Cada equipo prepara su propio entorno. Los archivos necesarios son el código, los módulos, las imágenes y los iniciadores incluidos en el ZIP. Las cotizaciones de moneda consultadas por el panel requieren conexión.
