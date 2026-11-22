"""Inicio local de Altium con selección de puerto y comprobación de arranque."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from http.client import HTTPConnection
from urllib.parse import urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.streamlit' / 'servidor_local.json'
LOG = ROOT / 'streamlit_local.log'


def disponible(puerto):
    try:
        with socket.socket() as conexion:
            if os.name == 'nt':
                conexion.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            conexion.bind(('127.0.0.1', puerto))
        return True
    except OSError:
        return False


def responde(url):
    destino = urlsplit(url)
    conexion = HTTPConnection(destino.hostname, destino.port, timeout=1)
    try:
        conexion.request('GET', '/_stcore/health')
        respuesta = conexion.getresponse()
        return respuesta.status == 200 and respuesta.read().strip() == b'ok'
    except (OSError, ConnectionError):
        return False
    finally:
        conexion.close()


def main():
    opciones = argparse.ArgumentParser()
    opciones.add_argument('--no-browser', action='store_true')
    args = opciones.parse_args()
    try:
        saved = json.loads(STATE.read_text(encoding='utf-8'))
        puerto = saved.get('port')
        url = f'http://127.0.0.1:{puerto}'
        if saved.get('project') == str(ROOT) and isinstance(puerto, int) and 8501 <= puerto <= 8520 and responde(url):
            print('Altium ya esta funcionando: ' + url, flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            return 0
    except (OSError, ValueError, TypeError):
        pass
    entorno = os.environ.copy()
    for puerto in range(8501, 8521):
        if not disponible(puerto):
            continue
        url = f'http://127.0.0.1:{puerto}'
        with LOG.open('w', encoding='utf-8') as registro:
            proceso = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app.py',
                '--server.address=127.0.0.1', f'--server.port={puerto}',
                '--server.headless=true', '--server.runOnSave=true', '--server.fileWatcherType=poll',
                '--server.enableCORS=true'], cwd=ROOT, env=entorno, stdout=registro, stderr=subprocess.STDOUT)
            try:
                listo = False
                for _ in range(90):
                    if proceso.poll() is not None:
                        break
                    if responde(url):
                        listo = True
                        break
                    time.sleep(.5)
                if not listo:
                    if proceso.poll() is None:
                        proceso.terminate()
                        proceso.wait(timeout=10)
                    error = LOG.read_text(encoding='utf-8', errors='replace')
                    if '10013' in error or 'already in use' in error:
                        continue
                    print('No se pudo iniciar Streamlit. Detalle: ' + str(LOG), flush=True)
                    print(error[-3500:], flush=True)
                    return 1
                STATE.parent.mkdir(exist_ok=True)
                STATE.write_text(json.dumps({'port': puerto, 'pid': proceso.pid, 'project': str(ROOT)}), encoding='utf-8')
                print('Altium listo: ' + url, flush=True)
                print('Los cambios se actualizan al guardar. Para detener: Ctrl+C en esta ventana.', flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
                return proceso.wait()
            except KeyboardInterrupt:
                if proceso.poll() is None:
                    proceso.terminate()
                    proceso.wait(timeout=10)
                return 0
            finally:
                if proceso.poll() is not None and STATE.exists():
                    try:
                        if json.loads(STATE.read_text(encoding='utf-8')).get('pid') == proceso.pid:
                            STATE.unlink()
                    except (OSError, ValueError):
                        pass
    print('El sistema bloqueo u ocupo todos los puertos 8501 a 8520. Cierra otras instancias e intenta de nuevo.', flush=True)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
