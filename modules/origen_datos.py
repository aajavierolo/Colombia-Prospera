"""Lectura anónima de libros públicos de Google, sin modificar el original."""
from io import BytesIO
import re
import ssl
from urllib.parse import urlsplit, parse_qs, urlencode
from urllib.request import Request, HTTPSHandler, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from zipfile import ZipFile, BadZipFile

LIMITE_BYTES = 30 * 1024 * 1024


def contexto_https():
    """Conserva TLS verificado si un registro de depuración no es accesible."""
    try:
        return ssl.create_default_context()
    except PermissionError:
        # Algunos equipos definen SSLKEYLOGFILE en un dispositivo no accesible.
        # El registro de claves es opcional; los certificados siguen verificándose.
        contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        contexto.load_default_certs()
        return contexto


def url_descarga(enlace):
    partes = urlsplit(enlace.strip())
    if partes.scheme != 'https' or partes.hostname not in {'docs.google.com', 'drive.google.com'} or partes.username or partes.password or partes.port:
        raise ValueError('Pega un enlace HTTPS de Google Sheets o Google Drive.')
    consulta = parse_qs(partes.query)
    coincidencia = re.fullmatch(r'/spreadsheets/d/([\w-]+)(?:/.*)?', partes.path) if partes.hostname == 'docs.google.com' else None
    if coincidencia:
        identificador = coincidencia[1]
        base = f'https://docs.google.com/spreadsheets/d/{identificador}/export'
        parametros = {'format': 'xlsx'}
    else:
        coincidencia = re.fullmatch(r'/file/d/([\w-]+)(?:/.*)?', partes.path)
        identificador = coincidencia[1] if coincidencia else consulta.get('id', [''])[0] if partes.path in {'/open', '/uc'} else ''
        if partes.hostname != 'drive.google.com' or not re.fullmatch(r'[\w-]+', identificador):
            raise ValueError('Usa el enlace de una hoja de Google Sheets o de un archivo Excel en Drive; las carpetas no son compatibles.')
        base = 'https://drive.google.com/uc'
        parametros = {'export': 'download', 'id': identificador}
    if consulta.get('resourcekey'):
        parametros['resourcekey'] = consulta['resourcekey'][0]
    return base + '?' + urlencode(parametros)


class _RedireccionesGoogle(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        partes = urlsplit(newurl)
        host = partes.hostname or ''
        if partes.scheme != 'https' or not any(host == dominio or host.endswith('.' + dominio) for dominio in ('google.com', 'googleusercontent.com', 'usercontent.google.com')):
            raise ValueError('Google devolvió una dirección de descarga no compatible.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def descargar_libro_publico(enlace):
    direccion = url_descarga(enlace)
    try:
        with build_opener(_RedireccionesGoogle(), HTTPSHandler(context=contexto_https())).open(Request(direccion, headers={'User-Agent': 'Colombia-Prospera/26'}), timeout=30) as respuesta:
            contenido = respuesta.read(LIMITE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ValueError('No se pudo descargar el archivo. Comprueba la conexión y que esté compartido como «Cualquier persona con el enlace», con permiso de lectura y descarga.') from exc
    if len(contenido) > LIMITE_BYTES:
        raise ValueError('El archivo supera el límite de 30 MB para enlaces.')
    try:
        with ZipFile(BytesIO(contenido)) as libro:
            if 'xl/workbook.xml' not in libro.namelist():
                raise BadZipFile()
    except BadZipFile as exc:
        raise ValueError('El enlace no devolvió un Excel válido. Revisa que el archivo sea público, permita descargarlo y sea Google Sheets o .xlsx.') from exc
    return contenido
