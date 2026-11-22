# Imagen de Altium Financiero V26

Con Docker Desktop funcionando, **PUBLICAR_DOCKER_HUB.bat** construye y valida la imagen antes de publicarla con las etiquetas `javierolo123/cuentas:v26-sin-ia` y `javierolo123/cuentas:sin-ia`.

La construcción incluye código y recursos. El validador revisa los archivos y el arranque de Streamlit.

Una vez publicadas esas etiquetas, el archivo `docker-compose.hub.yml` permite iniciar esta versión con `docker compose -f docker-compose.hub.yml up -d` y abrir `http://127.0.0.1:8502`.

Para ejecutarla desde el código de esta carpeta, utiliza `docker compose up -d --build`.

Esta preparación guarda las instrucciones de publicación. La publicación se realiza cuando ejecutas el BAT correspondiente.
