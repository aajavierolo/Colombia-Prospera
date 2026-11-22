"""Clasificación inicial revisable para la regla 50/30/20."""
import unicodedata


def tooltip_regla(grupo, monto, ingresos):
    limites = {'Necesidades': .5, 'Gustos': .3, 'Ahorro': .2}
    explicaciones = {
        'Necesidades': 'Gastos básicos y cuotas de deuda según tu clasificación.',
        'Gustos': 'Gastos de tu categoría GUSTOS y ajustes realizados.',
        'Ahorro': 'Aportes a ahorro, inversión y abonos extra a deudas.',
        'No utilizado': 'Saldo disponible después de las salidas registradas.<br>No se cuenta como ahorro realizado.',
    }
    iconos = {'Necesidades': '🏠', 'Gustos': '🎉', 'Ahorro': '🐷', 'No utilizado': '💵'}
    lineas = [f'<b>{iconos.get(grupo, "📊")} {grupo}</b>', f'💰 Monto: <b>${monto:,.0f}</b>',
              f'📥 Ingresos del período: ${ingresos:,.0f}']
    if ingresos > 0:
        lineas.append(f'📊 Parte de tus ingresos: <b>{monto / ingresos * 100:.1f}%</b>')
        if grupo in limites:
            limite = limites[grupo]
            referencia = ingresos * limite
            diferencia = monto - referencia
            lineas.append(f'🎯 Referencia {limite:.0%}: ${referencia:,.0f}')
            if abs(diferencia) <= .000001:
                estado = '✅ Justo en la referencia.'
            elif grupo == 'Ahorro':
                estado = (f'🌟 Meta superada en ${diferencia:,.0f}.' if diferencia > 0
                          else f'⏳ Faltan ${-diferencia:,.0f} para la meta de ahorro.')
            else:
                estado = (f'🔴 Supera la referencia en ${diferencia:,.0f}.' if diferencia > 0
                          else f'✅ Margen hasta la referencia: ${-diferencia:,.0f}.')
            lineas.append(estado)
        else:
            lineas.append('ℹ️ Sin porcentaje objetivo en la regla 50/30/20.')
    else:
        lineas.append('⚠️ Porcentaje y comparación no disponibles: faltan ingresos positivos.')
    lineas.append('📝 ' + explicaciones.get(grupo, ''))
    return '<br>'.join(lineas)


def clasificar_regla(categoria, subcategoria):
    def limpio(valor):
        return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(valor))
                                if unicodedata.category(c) != 'Mn').upper().split())
    categoria, subcategoria = limpio(categoria), limpio(subcategoria)
    if categoria == 'GUSTOS':
        return 'Gustos'
    if categoria in {'AHORRO', 'AHORROS', 'INVERSION', 'INVERSIONES', 'AHORRO E INVERSION'}:
        return 'Ahorro'
    if subcategoria in {'AHORRO', 'AHORROS', 'INVERSION', 'INVERSIONES',
                        'FONDO DE TRANQUILIDAD', 'FONDO DE EMERGENCIA',
                        'AHORRO VOLUNTARIO', 'PENSION VOLUNTARIA',
                        'ABONO EXTRA A DEUDA', 'ABONO EXTRA A DEUDAS'}:
        return 'Ahorro'
    return 'Necesidades'
