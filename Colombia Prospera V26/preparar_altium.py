"""Prepara Altium y abre el panel en Windows, macOS o Linux."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ENVIRONMENT = ROOT / '.venv'
PYTHON = ENVIRONMENT / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
STATE = ROOT / '.altium'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preparar', action='store_true', help='Preparar las dependencias y terminar.')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print('Instala Python 3.11 o posterior para iniciar Altium.')
        return 1
    if not PYTHON.is_file():
        print('Preparando el entorno de Altium...', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(ENVIRONMENT)], check=True)
    requirements = ROOT / 'requirements.txt'
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    stamp = STATE / 'requirements.sha256'
    previous = stamp.read_text(encoding='utf-8').strip().lower() if stamp.is_file() else ''
    imports = subprocess.run(
        [str(PYTHON), '-c', 'import streamlit,pandas,plotly,openpyxl,matplotlib,reportlab'],
        capture_output=True,
    )
    if previous != fingerprint or imports.returncode:
        print('Instalando dependencias. El primer inicio necesita Internet...', flush=True)
        subprocess.run([str(PYTHON), '-m', 'pip', 'install', '--use-feature=truststore', '-r', str(requirements)], check=True)
        subprocess.run([str(PYTHON), '-m', 'pip', 'check'], check=True)
        STATE.mkdir(exist_ok=True)
        stamp.write_text(fingerprint, encoding='utf-8')
    if args.preparar:
        print('Altium está preparado.', flush=True)
        return 0
    command = [str(PYTHON), str(ROOT / 'iniciar_streamlit.py')]
    if args.no_browser:
        command.append('--no-browser')
    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print('No se pudo preparar Altium. Revisa el mensaje y vuelve a ejecutar el iniciador.')
        print(error)
        raise SystemExit(1)
