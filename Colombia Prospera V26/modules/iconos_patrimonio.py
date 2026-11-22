"""Iconos vectoriales consistentes para las categorías del patrimonio."""
import unicodedata

ICONOS = {
 'inmueble':'<path d="M3 11l9-8 9 8M5 10v11h14V10M10 21v-7h4v7"/>',
 'vehiculo':'<path d="M4 10l2-5h12l2 5M3 10h18v8H3zM6 18v3M18 18v3M6 14h2M16 14h2"/>',
 'inversion':'<path d="M4 20V4M4 20h17M7 15l4-4 4 2 5-7M16 6h4v4"/>',
 'ahorro':'<path d="M5 7h14v14H5zM8 3h8v4M9 11h6M9 16h6"/><circle cx="12" cy="14" r="3"/>',
 'banco':'<path d="M3 8l9-5 9 5H3zM4 21h16M6 10v8M12 10v8M18 10v8"/>',
 'negocio':'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V3h8v4M3 12l9 3 9-3M12 12v5"/>',
 'prestamo':'<circle cx="15" cy="7" r="4"/><path d="M3 14h5l3-3 4 2-3 3H9M3 20h5l12-6M3 13v8"/>',
 'deuda':'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18M7 15h4"/>',
 'pension':'<path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3zM8 12l3 3 5-6"/>',
 'joya':'<path d="M3 8l4-5h10l4 5-9 13L3 8zM3 8h18M7 3l5 18 5-18"/>',
 'equipo':'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
 'general':'<path d="M3 7l9-4 9 4-9 4-9-4zM3 12l9 4 9-4M3 17l9 4 9-4"/>',
}


def tipo_icono_patrimonio(nombre):
    clave=''.join(c for c in unicodedata.normalize('NFD',str(nombre).upper()) if unicodedata.category(c)!='Mn')
    if clave.startswith('PASIVO'):return 'deuda'
    grupos=[
        ('pension',['PENSION','CESANTIA','JUBILA']),
        ('ahorro',['EMERGENCIA','AHORRO']),
        ('prestamo',['POR COBRAR','PRESTAM','CREDITO A','CUENTAS POR COBRAR']),
        ('inmueble',['INMUEBL','INMOBILI','RAIZ','RAICES','VIVIENDA','TERRENO','APARTAMENTO','CASA','LOTE']),
        ('vehiculo',['VEHICUL','CARRO','MOTO','TRANSPORTE']),
        ('joya',['JOYA','ORO','METAL','COLECCION']),
        ('negocio',['NEGOCIO','EMPRESA','COMERCIO','PARTICIPACION']),
        ('inversion',['INVERSION','ACCION','BONO','CDT','FONDO','CRIPTO']),
        ('banco',['EFECTIVO','BANCO','BANCAR','CUENTA','MONETAR','FINANCIER','LIQUID']),
        ('equipo',['EQUIPO','MUEBLE','TECNOLOG','COMPUTADOR']),
    ]
    return next((tipo for tipo,palabras in grupos if any(p in clave for p in palabras)),'general')


def icono_patrimonio_svg(nombre,x,y,tamano=24):
    tipo=tipo_icono_patrimonio(nombre)
    return (f'<g data-icono-patrimonio="{tipo}" transform="translate({x},{y}) scale({tamano/24})" '
        'fill="none" stroke="#F8FAFC" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" pointer-events="none">'
        +ICONOS[tipo]+'</g>')
