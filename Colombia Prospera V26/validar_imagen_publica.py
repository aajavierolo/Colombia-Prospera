from pathlib import Path
import ast
import importlib
import sys
root = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/app')
# El validador vive fuera de /app; habilitar explícitamente sus módulos.
sys.path.insert(0, str(root))
if not (root / 'app.py').is_file():
    raise SystemExit('No se encuentra app.py en la ruta de validación: ' + str(root))
print('Validando contenido y sintaxis de la aplicación...', flush=True)
blocked = {'.xlsx', '.xls', '.xlsm', '.csv', '.tsv', '.zip', '.log', '.sqlite', '.db'}
private = [str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and (p.suffix.lower() in blocked or p.name in ('secrets.toml', '.env', 'servidor_local.json') or any(x in p.parts for x in ('.venv', '.git', '.altium')))]
if private:
    raise SystemExit('Hay archivos que no deben publicarse: ' + ', '.join(private[:20]))
for p in [root / 'app.py', *list((root / 'modules').glob('*.py'))]:
    compile(p.read_text(encoding='utf-8-sig'), str(p), 'exec')
print('Validando dependencias y módulos de la aplicación...', flush=True)
for name in ('streamlit', 'pandas', 'plotly', 'openpyxl', 'matplotlib', 'reportlab'):
    importlib.import_module(name)
for module in ('modules.report_pdf','modules.report_resumen_v22','modules.sunburst_deudas_noche','modules.proyeccion_creditos'):
    importlib.import_module(module)
assert (root / 'imagenes' / 'hamster.png').is_file()
print('Imagen verificada: codigo y recursos, sin Excel, datos financieros, logs ni secretos.')
