"""Cálculos compartidos entre el dashboard y el informe de deudas."""
import math
import pandas as pd
from modules.intereses_deudas import meses_interes
from modules.proyeccion_creditos import numero, texto, proyectar_saldo, tabla_proyeccion, proyectar_cuota_compensada, referencia_pago_original, cuota_financiera_excel, cargos_mensuales
from modules.proyeccion_creditos import cuotas_restantes_estimadas, proyectar_aleman, proyectar_ingles


def metodo_credito(deuda):
    if texto(deuda.get('Hoja origen')) != 'pasivos':
        return None
    etiqueta = texto(deuda.get('Sistema de amortización')) or texto(deuda.get('Tipo'))
    for raiz, nombre in [('frances', 'frances'), ('aleman', 'aleman'), ('ingles', 'ingles'), ('american', 'ingles')]:
        if raiz in etiqueta:
            return nombre
    return None


def preparar_deudas(deudas, corte):
    datos = deudas.copy()
    for col in ['Deuda inicial', 'Interés', 'Saldo']:
        datos[col] = pd.to_numeric(datos.get(col, pd.Series(index=datos.index, dtype=float)), errors='coerce').fillna(0).clip(lower=0)
    datos['Interés'] = datos['Interés'].where(datos['Interés'].le(1), datos['Interés'] / 100)
    datos['Pagado'] = (datos['Deuda inicial'] - datos['Saldo']).clip(lower=0)
    datos['Avance'] = (datos['Pagado'] / datos['Deuda inicial'].where(datos['Deuda inicial'].gt(0)) * 100).fillna(0)
    datos['Tasa mensual'] = datos['Interés']
    datos['Interés %'] = datos['Interés'] * 100
    datos['Tasa efectiva anual %'] = ((1 + datos['Interés']) ** 12 - 1) * 100
    fechas = datos.get('Inicio del crédito', pd.Series(pd.NaT, index=datos.index))
    datos['Inicio del crédito'] = pd.to_datetime(fechas, errors='coerce', dayfirst=True, format='mixed')
    datos['Días transcurridos'] = (pd.Timestamp(corte).normalize() - datos['Inicio del crédito']).dt.days.clip(lower=0)
    datos['Meses transcurridos'] = datos.apply(lambda r: meses_interes(r['Inicio del crédito'], corte, r.get('Sistema de amortización')), axis=1)
    datos['Saldo promedio estimado'] = (datos['Deuda inicial'] + datos['Saldo']) / 2
    datos['Interés acumulado estimado'] = datos['Saldo promedio estimado'] * datos['Interés'] * datos['Meses transcurridos']
    datos['Pago económico estimado'] = datos['Pagado'] + datos['Interés acumulado estimado']
    datos['Total pagado estimado'] = datos['Pago económico estimado']
    total = datos['Saldo'].sum()
    datos['Participación saldo %'] = datos['Saldo'] / total * 100 if total else 0.0
    datos['Costo mensual estimado'] = datos['Saldo'] * datos['Interés']
    datos['Costo anual estimado'] = datos['Costo mensual estimado'] * 12
    return datos


def credito_frances(deuda):
    sistema = texto(deuda.get('Sistema de amortización'))
    tipo = texto(deuda.get('Tipo'))
    etiquetas = {'frances', 'francesa', 'sistema frances', 'amortizacion francesa', 'credito frances'}
    return texto(deuda.get('Hoja origen')) == 'pasivos' and (sistema in etiquetas or (not sistema and tipo in etiquetas))


def configuracion_cuota(deuda, valor_editado=None):
    saldo, tasa, cuota = numero(deuda.get('Saldo')), numero(deuda.get('Interés')), cuota_financiera_excel(deuda)
    if saldo is None or saldo <= 0 or tasa is None or tasa < 0:
        return None
    if tasa > 1:
        tasa /= 100
    if numero(valor_editado) is not None:
        cuota = numero(valor_editado)
    elif cuota is None or cuota <= 0:
        plazo = cuotas_restantes_estimadas(deuda)
        if plazo:
            cuota = round(saldo / plazo if tasa == 0 else saldo * tasa / (-math.expm1(-plazo * math.log1p(tasa))), 2)
    estimada = cuota is None or cuota <= saldo * tasa + .01 or cuota <= 0
    if estimada:
        cuota = numero(valor_editado)
        if cuota is None:
            inicial, plazo = numero(deuda.get('Deuda inicial')), numero(deuda.get('Cuotas totales'))
            if not inicial or not plazo or not 1 <= plazo <= 1200 or not plazo.is_integer():
                return None
            cuota = round(inicial / plazo if tasa == 0 else inicial * tasa / (-math.expm1(-plazo * math.log1p(tasa))), 2)
    return {'saldo': saldo, 'tasa': tasa, 'cuota': cuota, 'estimada': estimada}


def recoger_simulaciones_deudas(deudas, estado):
    simulaciones = {}
    for posicion, (_, deuda) in enumerate(deudas.iterrows(), start=1):
        metodo = metodo_credito(deuda)
        if metodo in {'aleman', 'ingles'}:
            clave = f'credito_frances_{posicion}'
            plazo = cuotas_restantes_estimadas(deuda)
            saldo, tasa = numero(deuda.get('Saldo')), numero(deuda.get('Interés'))
            if not plazo or saldo is None or saldo <= 0 or tasa is None or tasa < 0:
                continue
            tasa = tasa / 100 if tasa > 1 else tasa
            cuota = numero(estado.get(clave + '_cuota_editable'))
            if cuota is None:
                cuota = round(saldo * tasa + (0 if metodo == 'ingles' else saldo / plazo), 2)
            compatible = estado.get(clave + '_firma_nuevos_abonos') == (metodo, saldo, tasa, plazo)
            # El americano utiliza la misma lógica y conserva su nombre en la firma de pantalla.
            compatible = compatible or estado.get(clave + '_firma_nuevos_abonos') == ('americano', saldo, tasa, plazo)
            simulaciones[str(posicion)] = dict(cuota=cuota, plazo=plazo,
                abonos=dict(estado.get(clave + '_nuevos_abonos', {})) if compatible else {},
                modo=estado.get(clave + '_nuevo_modo_abonos', 'plazo') if compatible else 'plazo')
            continue
        if not credito_frances(deuda):
            continue
        clave = f'credito_frances_{posicion}'
        total = numero(estado.get(clave + '_cuota_total'))
        cuota_editada = round(total - sum(cargos_mensuales(deuda)), 2) if total is not None else None
        cuota_editada = estado.get(clave + '_cuota_simulada_financiera', cuota_editada)
        config = configuracion_cuota(deuda, cuota_editada)
        if not config:
            continue
        firma = (config['saldo'], config['tasa'], config['cuota'])
        compatible = estado.get(clave + '_firma_abonos') == firma
        simulaciones[str(posicion)] = {
            'cuota': config['cuota'],
            'compensar_cuota': bool(estado.get(clave + '_compensar_cuota', False)),
            'abonos': dict(estado.get(clave + '_abonos_tabla', {})) if compatible else {},
            'modo': estado.get(clave + '_modo_abonos', 'plazo') if compatible else 'plazo',
        }
    return simulaciones


def proyeccion_deuda(deuda, simulacion=None):
    metodo = metodo_credito(deuda)
    if metodo in {'aleman', 'ingles'}:
        simulacion = simulacion or {}
        saldo, tasa = numero(deuda.get('Saldo')), numero(deuda.get('Interés'))
        plazo = simulacion.get('plazo') or cuotas_restantes_estimadas(deuda)
        if saldo is None or saldo <= 0 or tasa is None or tasa < 0 or not plazo:
            return None
        tasa = tasa / 100 if tasa > 1 else tasa
        cuota = numero(simulacion.get('cuota'))
        if cuota is None:
            cuota = round(saldo*tasa + (0 if metodo == 'ingles' else saldo/plazo), 2)
        abonos = {int(k): float(v) for k, v in simulacion.get('abonos', {}).items()}
        modo = simulacion.get('modo', 'plazo')
        constructor = proyectar_aleman if metodo == 'aleman' else proyectar_ingles
        base = constructor(saldo, tasa, plazo, cuota=cuota)
        opciones = {'reduccion': modo} if metodo == 'aleman' else {}
        tabla = constructor(saldo, tasa, plazo, cuota=cuota, abonos=abonos, **opciones)
        return dict(saldo=saldo, tasa=tasa, cuota=cuota, estimada=False, base=base,
            tabla=tabla, detalle=tabla_proyeccion(tabla, deuda), modo=modo, abonos=abonos,
            cuota_resultado=float(tabla.iloc[1]['Pago']-tabla.iloc[1]['Abono extra']),
            meses_ahorrados=len(base)-len(tabla),
            ahorro_intereses=max(0.0,float(base.Intereses.sum()-tabla.Intereses.sum())))
    if not credito_frances(deuda):
        return None
    simulacion = simulacion or {}
    config = configuracion_cuota(deuda, simulacion.get('cuota'))
    if not config:
        return None
    base = referencia_pago_original(deuda, config['saldo'], config['tasa'], config['cuota'])
    abonos = {int(k): float(v) for k, v in simulacion.get('abonos', {}).items()}
    modo = simulacion.get('modo', 'plazo')
    if modo == 'cuota' and simulacion.get('compensar_cuota', False):
        tabla = proyectar_cuota_compensada(config['saldo'], config['tasa'],
            cuota_financiera_excel(deuda) or config['cuota'], config['cuota'], abonos)
    else:
        tabla = proyectar_saldo(config['saldo'], config['tasa'], config['cuota'], abonos=abonos, reduccion=modo)
    ultima = tabla.loc[tabla['Abono extra'].gt(0), 'Cuota'].max()
    cuota_resultado = config['cuota']
    if abonos and modo == 'cuota':
        siguientes = tabla.loc[tabla['Cuota'].gt(ultima)]
        cuota_resultado = float(siguientes.iloc[0]['Pago']) if not siguientes.empty else 0.0
    return dict(config, base=base, tabla=tabla, detalle=tabla_proyeccion(tabla, deuda), modo=modo,
        abonos=abonos, cuota_resultado=cuota_resultado,
        meses_ahorrados=len(base) - len(tabla),
        ahorro_intereses=max(0.0, float(base['Intereses'].sum() - tabla['Intereses'].sum())))
