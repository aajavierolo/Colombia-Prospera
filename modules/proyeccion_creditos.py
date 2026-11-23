"""Proyección de cuota fija desde el saldo vigente; no reconstruye pagos históricos."""
import base64
import math
import re
import html
import unicodedata
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components


def texto(valor):
    if pd.isna(valor):
        return ''
    return ''.join(c for c in unicodedata.normalize('NFD', str(valor).strip().lower()) if unicodedata.category(c) != 'Mn')


def numero(valor):
    try:
        resultado = float(valor)
        return resultado if math.isfinite(resultado) else None
    except (ValueError, TypeError):
        return None


def proyectar_saldo(saldo, tasa, cuota, limite=1200, abonos=None, reduccion='plazo'):
    """Tasa mensual decimal; última cuota ajustada al capital y al interés restantes."""
    saldo, tasa, cuota = numero(saldo), numero(tasa), numero(cuota)
    if saldo is None or tasa is None or cuota is None or saldo < 0 or tasa < 0 or cuota <= 0:
        raise ValueError('Se necesitan un saldo válido, una tasa mensual no negativa y una cuota positiva.')
    if reduccion not in {'plazo', 'cuota'}:
        raise ValueError('Selecciona reducción de tiempo o de cuota.')
    abonos = abonos or {}
    plazo_original = len(proyectar_saldo(saldo, tasa, cuota, limite=limite)) - 1 if abonos and reduccion == 'cuota' else None
    cuota_actual = cuota
    for periodo, importe in abonos.items():
        if not isinstance(periodo, int) or not 1 <= periodo <= limite or numero(importe) is None or importe < 0:
            raise ValueError('El abono debe ser positivo y corresponder a una cuota válida.')
    filas = [[0, saldo, 0.0, 0.0, 0.0, 0.0]]
    if saldo > 0 and cuota <= saldo * tasa + 0.01:
        raise ValueError('La cuota no alcanza para reducir el saldo: debe superar los intereses del primer mes.')
    for mes in range(1, limite + 1):
        if saldo <= 0:
            break
        interes = saldo * tasa
        pago = min(cuota_actual, saldo + interes)
        capital = pago - interes
        saldo = max(0.0, saldo - capital)
        extra = min(float(abonos.get(mes, 0)), saldo)
        saldo -= extra
        capital += extra
        pago += extra
        if saldo < 0.000001:
            saldo = 0.0
        filas.append([mes, saldo, pago, capital, interes, extra])
        if extra > 0 and saldo > 0 and reduccion == 'cuota':
            restantes = plazo_original - mes
            if restantes > 0:
                cuota_actual = saldo / restantes if tasa == 0 else saldo * tasa / (-math.expm1(-restantes * math.log1p(tasa)))
    if saldo > 0:
        raise ValueError('El crédito supera 1.200 cuotas con estos valores. Revisa la cuota y la tasa mensual.')
    return pd.DataFrame(filas, columns=['Cuota', 'Saldo pendiente', 'Pago', 'Capital', 'Intereses', 'Abono extra'])


def cuotas_restantes_estimadas(deuda, hoy=None):
    """Estima cuotas pendientes con el plazo original y los meses completos desde el inicio."""
    total = numero(deuda.get('Cuotas totales'))
    if total is None or total < 1 or total > 1200 or not total.is_integer():
        return None
    inicio = pd.to_datetime(deuda.get('Inicio del crédito'), errors='coerce')
    if pd.isna(inicio):
        return int(total)
    corte = pd.Timestamp.today().normalize() if hoy is None else pd.to_datetime(hoy, errors='coerce').normalize()
    if pd.isna(corte) or corte < inicio.normalize():
        transcurridas = 0
    else:
        transcurridas = (corte.year - inicio.year) * 12 + corte.month - inicio.month
        if corte < inicio.normalize() + pd.DateOffset(months=transcurridas):
            transcurridas -= 1
        transcurridas = max(0, transcurridas)
    return max(1, int(total) - transcurridas)


def proyectar_aleman(saldo, tasa, cuotas, abonos=None, reduccion='plazo', cuota=None):
    """Amortización alemana: capital constante e intereses sobre saldo decreciente."""
    saldo, tasa, cuotas = numero(saldo), numero(tasa), numero(cuotas)
    if saldo is None or tasa is None or cuotas is None or saldo < 0 or tasa < 0 or cuotas < 1 or cuotas > 1200 or not cuotas.is_integer():
        raise ValueError('Se necesitan un saldo, una tasa mensual y un número entero válido de cuotas restantes.')
    filas = [[0, saldo, 0.0, 0.0, 0.0, 0.0]]
    if reduccion not in {'plazo', 'cuota'}:
        raise ValueError('Selecciona reducción de tiempo o de cuota.')
    capital_fijo = saldo / int(cuotas) if saldo > 0 else 0.0
    if cuota is not None:
        capital_fijo = float(cuota) - saldo * tasa
        if capital_fijo <= 0:
            raise ValueError('La cuota inicial debe superar los intereses del primer mes.')
        periodos_calculados = saldo / capital_fijo
        cercano = max(1, round(periodos_calculados))
        # La cuota editable se expresa en centavos: evita un mes adicional
        # cuando el residuo solo procede de ese redondeo.
        if abs(saldo - capital_fijo * cercano) <= .005 * cercano + 1e-6:
            cuotas = float(cercano)
        else:
            cuotas = float(max(1, math.ceil(periodos_calculados)))
        if cuotas > 1200:
            raise ValueError('La cuota produce más de 1.200 pagos; aumenta el importe.')
    abonos = abonos or {}
    for mes in range(1, int(cuotas) + 1):
        if saldo <= 0:
            break
        interes = saldo * tasa
        capital = saldo if mes == int(cuotas) else min(capital_fijo, saldo)
        pago = capital + interes
        saldo = max(0.0, saldo - capital)
        extra = min(max(0.0, float(abonos.get(mes, 0.0))), saldo)
        saldo -= extra
        filas.append([mes, saldo, pago + extra, capital + extra, interes, extra])
        if extra > 0 and saldo > 0 and reduccion == 'cuota' and mes < int(cuotas):
            capital_fijo = saldo / (int(cuotas) - mes)
    return pd.DataFrame(filas, columns=['Cuota', 'Saldo pendiente', 'Pago', 'Capital', 'Intereses', 'Abono extra'])


def proyectar_ingles(saldo, tasa, cuotas, abonos=None, cuota=None):
    """Amortización inglesa/americana: intereses periódicos y capital al vencimiento."""
    saldo, tasa, cuotas = numero(saldo), numero(tasa), numero(cuotas)
    if saldo is None or tasa is None or cuotas is None or saldo < 0 or tasa < 0 or cuotas < 1 or cuotas > 1200 or not cuotas.is_integer():
        raise ValueError('Se necesitan un saldo, una tasa mensual y un número entero válido de cuotas restantes.')
    filas = [[0, saldo, 0.0, 0.0, 0.0, 0.0]]
    abonos = abonos or {}
    for mes in range(1, int(cuotas) + 1):
        if saldo <= 0:
            break
        interes = saldo * tasa
        if cuota is not None and float(cuota) + 1e-6 < interes:
            raise ValueError('La cuota debe cubrir al menos los intereses mensuales.')
        capital = saldo if mes == int(cuotas) else min(saldo, max(0.0, float(cuota) - interes)) if cuota is not None else 0.0
        pago = capital + interes
        saldo = max(0.0, saldo - capital)
        extra = min(max(0.0, float(abonos.get(mes, 0.0))), saldo)
        saldo -= extra
        filas.append([mes, saldo, pago + extra, capital + extra, interes, extra])
    return pd.DataFrame(filas, columns=['Cuota', 'Saldo pendiente', 'Pago', 'Capital', 'Intereses', 'Abono extra'])


def _texto_plazo(cuota):
    anios, meses = divmod(max(0, int(cuota)), 12)
    partes = []
    if anios:
        partes.append(f'{anios} año' + ('s' if anios != 1 else ''))
    if meses:
        partes.append(f'{meses} mes' + ('es' if meses != 1 else ''))
    return ' y '.join(partes) if partes else 'hoy'


def _agregar_plazo_tooltip(fig):
    """Expresa cada cuota mensual como tiempo desde el saldo actual."""
    traza = fig.data[0]
    traza.text = ['Dentro de ' + _texto_plazo(n) if int(n) > 0 else 'Saldo actual · hoy' for n in traza.x]
    traza.textposition = 'none'
    traza.hovertemplate = '<b>⏳ %{text}</b><br>' + traza.hovertemplate
    return fig


def crear_grafico_saldo(tabla):
    """Cada barra es una cuota: capital amortizado y saldo pendiente."""
    base = float(tabla.iloc[0]['Saldo pendiente'])
    amortizado = base - tabla['Saldo pendiente']
    datos = tabla[['Pago', 'Capital', 'Intereses', 'Saldo pendiente']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=tabla['Cuota'], y=amortizado,
        name='Capital amortizado', marker_color='#00FF00',
        customdata=datos,
        hovertemplate='<b>Capital amortizado</b>  $%{y:,.0f}<br>Capital de esta cuota: $%{customdata[1]:,.0f}<extra></extra>'))
    fig.add_trace(go.Bar(x=tabla['Cuota'], y=tabla['Saldo pendiente'],
        name='Saldo pendiente', marker_color='#FF0000', customdata=datos,
        hovertemplate='<b>Saldo pendiente</b>  $%{y:,.0f}<br>Capital de esta cuota: $%{customdata[1]:,.0f}<br>Intereses: $%{customdata[2]:,.0f}<br>Pago mensual: $%{customdata[0]:,.0f}<extra></extra>'))
    fig.update_layout(template='plotly_dark', height=470, separators=',.',
        barmode='stack', bargap=.23, barcornerradius=0,
        hovermode='x unified', hoverdistance=30,
        title=dict(text='Avance proyectado de la deuda por cuota',
            x=.025, y=.97, xanchor='left', font=dict(size=21, color='#F8FAFC')),
        paper_bgcolor='#07111F', plot_bgcolor='#0B1829',
        font=dict(family='Arial, sans-serif', size=12, color='#B4C9D9'),
        legend=dict(orientation='h', y=-.25, x=.5, xanchor='center',
            font=dict(size=12, color='#E2E8F0'), bgcolor='rgba(0,0,0,0)',
            itemsizing='constant', tracegroupgap=20),
        hoverlabel=dict(bgcolor='#111F33', bordercolor='#38BDF8',
            font=dict(size=13, color='#F8FAFC'), align='left', namelength=-1),
        margin=dict(t=100, b=100, l=85, r=35))
    fig.update_traces(marker_line_width=0)
    fig.update_xaxes(title='Cuotas mensuales desde el saldo actual',
        rangemode='tozero', dtick=1 if len(tabla) < 15 else None,
        showgrid=False, showline=True, linecolor='#284562',
        tickfont=dict(color='#94A3B8'), title_font=dict(color='#B4C9D9', size=12),
        showspikes=True, spikecolor='#38BDF8', spikethickness=1, spikedash='dot',
        zeroline=False, automargin=True)
    fig.update_yaxes(title='Capital del crédito', tickprefix='$', tickformat=',.0f',
        rangemode='tozero', gridcolor='rgba(148,163,184,0.10)',
        zerolinecolor='#284562', tickfont=dict(color='#94A3B8'),
        title_font=dict(color='#B4C9D9'), automargin=True)
    fig.add_shape(type='path', xref='paper', yref='paper', layer='below',
        path='M 0.02,0 L 0.98,0 Q 1,0 1,0.04 L 1,0.96 Q 1,1 0.98,1 L 0.02,1 Q 0,1 0,0.96 L 0,0.04 Q 0,0 0.02,0 Z',
        line=dict(color='#284562', width=1), fillcolor='#0B1829')
    fig.add_annotation(xref='paper', yref='paper', x=0, y=1.14,
        text='Cómo se transforma el saldo pendiente en capital pagado',
        showarrow=False, xanchor='left', font=dict(size=12, color='#94A3B8'))
    return _agregar_plazo_tooltip(fig)


def crear_grafico_cuotas_aleman(tabla, separar_abonos=True):
    """Descompone la cuota decreciente en capital constante e intereses."""
    pagos = tabla.loc[tabla['Cuota'].gt(0)]
    fig = go.Figure()
    for columna, color in [('Capital', '#00FF00'), ('Intereses', '#FF0000' if separar_abonos else '#38BDF8')]:
        valores = pagos['Capital'] - pagos['Abono extra'] if columna == 'Capital' else pagos[columna]
        fig.add_trace(go.Bar(x=pagos['Cuota'], y=valores, name=columna,
            customdata=pagos[['Pago', 'Abono extra', 'Saldo pendiente']],
            marker_color=color, hovertemplate=columna + ': $%{y:,.0f}<br>Abono extra: $%{customdata[1]:,.0f}<br><b>Total a pagar: $%{customdata[0]:,.0f}</b><br>Saldo después del pago: $%{customdata[2]:,.0f}<extra></extra>'))
    if separar_abonos:
        resumen = pd.DataFrame({
            'capital': pagos['Capital'] - pagos['Abono extra'],
            'intereses': pagos['Intereses'],
            'cuota': pagos['Pago'] - pagos['Abono extra'],
            'extra': pagos['Abono extra'],
            'total': pagos['Pago'],
            'saldo': pagos['Saldo pendiente'],
        })
        fig.data[0].customdata = resumen
        fig.data[0].name = 'Capital de la cuota'
        fig.data[0].hovertemplate = (
            '<b>Cuota %{x}</b><br>'
            'Capital que pagas: $%{customdata[0]:,.0f}<br>'
            'Intereses: $%{customdata[1]:,.0f}<br>'
            '<b>Cuota normal: $%{customdata[2]:,.0f}</b><br>'
            'Abono adicional: $%{customdata[3]:,.0f}<br>'
            '<b>Total a pagar este mes: $%{customdata[4]:,.0f}</b><br>'
            'Deuda después de pagar: $%{customdata[5]:,.0f}<extra></extra>')
        fig.data[1].hovertemplate = None
        fig.data[1].hoverinfo = 'skip'
    if pagos['Abono extra'].gt(0).any():
        if separar_abonos:
            extras = pagos.loc[pagos['Abono extra'].gt(0)]
            fig.add_trace(go.Scatter(x=extras['Cuota'], y=extras['Abono extra'],
                name='Abono extra · escala derecha', mode='markers', yaxis='y2',
                marker=dict(color='#FBBF24', size=13, symbol='diamond', line=dict(color='#07111F', width=2)),
                customdata=extras[['Pago', 'Saldo pendiente']],
                hoverinfo='skip'))
            fig.update_layout(yaxis2=dict(title='Abono extra · escala independiente',
                overlaying='y', side='right', rangemode='tozero', showgrid=False,
                tickprefix='$', tickformat=',.0f', color='#FBBF24'))
        else:
            fig.add_trace(go.Bar(x=pagos['Cuota'], y=pagos['Abono extra'], name='Abono extra',
                marker_color='#FBBF24', hovertemplate='Abono extra: $%{y:,.0f}<extra></extra>'))
    fig.update_layout(template='plotly_dark', barmode='stack', barcornerradius=0, height=470,
        title=dict(text='Método alemán · composición de la cuota', font=dict(size=18)),
        xaxis_title='Mes / número de cuota', yaxis_title='Cuota normal: capital + intereses' if separar_abonos else 'Valor de la cuota',
        margin=dict(l=85, r=110 if separar_abonos else 35, t=80, b=110),
        legend=dict(orientation='h', y=-.23, x=0), bargap=.25,
        paper_bgcolor='#07111F', plot_bgcolor='#0B1829', hovermode='x unified',
        separators=',.', hoverlabel=dict(bgcolor='#111F33', font=dict(color='#F8FAFC', size=14), align='left'))
    fig.update_layout(yaxis=dict(tickprefix='$', tickformat=',.0f', rangemode='tozero', automargin=True))
    fig.update_xaxes(dtick=1 if len(pagos) < 20 else None, automargin=True)
    if separar_abonos:
        fig.add_annotation(xref='paper', yref='paper', x=0, y=1.12, xanchor='left',
            text='Barras: cuota normal · Rombos amarillos: abonos adicionales (escala derecha)',
            showarrow=False, font=dict(size=11, color='#B4C9D9'))
    return _agregar_plazo_tooltip(fig)


def crear_grafico_cuotas_ingles(tabla):
    """Separa el pago final para conservar la escala de los pagos habituales."""
    pagos = tabla.loc[tabla['Cuota'].gt(0)]
    fig = make_subplots(rows=1, cols=2, column_widths=[.72, .28], horizontal_spacing=.16,
        subplot_titles=('Pagos durante el plazo', 'Última cuota · pago de cierre'))
    for columna, tramo in [(1, pagos.iloc[:-1]), (2, pagos.iloc[-1:])]:
        if tramo.empty:
            continue
        datos = tramo[['Capital', 'Intereses', 'Pago', 'Abono extra', 'Saldo pendiente']].copy()
        datos['Capital'] -= datos['Abono extra']
        for indice, (nombre, valores, color) in enumerate([
            ('Intereses', tramo['Intereses'], '#FF0000'),
            ('Capital', datos['Capital'], '#00FF00'),
            ('Abono adicional', tramo['Abono extra'], '#FBBF24'),
        ]):
            fig.add_trace(go.Bar(x=tramo['Cuota'], y=valores, name=nombre,
                marker_color=color, legendgroup=nombre, showlegend=columna == 2,
                customdata=datos.to_numpy(),
                text=['Dentro de ' + _texto_plazo(n) for n in tramo['Cuota']], textposition='none',
                hovertemplate=('<b>⏳ %{text}</b><br><b>Cuota %{x}</b><br>'
                    'Intereses: $%{customdata[1]:,.0f}<br>Capital: $%{customdata[0]:,.0f}<br>'
                    'Abono adicional: $%{customdata[3]:,.0f}<br><b>Total: $%{customdata[2]:,.0f}</b><br>'
                    'Saldo después del pago: $%{customdata[4]:,.0f}<extra></extra>') if indice == 0 else None,
                hoverinfo=None if indice == 0 else 'skip'), row=1, col=columna)
    if len(pagos) == 1:
        fig.add_annotation(text='Solo queda el pago de cierre', x=.3, y=.5,
            xref='paper', yref='paper', showarrow=False, font=dict(color='#B4C9D9'))
    fig.update_layout(template='plotly_dark', height=470, barmode='stack', bargap=.3,
        title=dict(text='Amortización inglesa · pagos y cierre', font=dict(size=20)),
        paper_bgcolor='#07111F', plot_bgcolor='#0B1829', separators=',.',
        font=dict(color='#D8E7F3'), margin=dict(l=85, r=35, t=100, b=75),
        hovermode='x unified', hoverlabel=dict(bgcolor='#0B1829', bordercolor='#38BDF8',
            font=dict(color='#F8FAFC', size=14), namelength=-1),
        legend=dict(orientation='h', y=-.13, x=.5, xanchor='center'))
    fig.update_yaxes(title='Pago (COP)', tickprefix='$', tickformat=',.0f', rangemode='tozero',
        gridcolor='rgba(148,163,184,.12)', automargin=True)
    fig.update_xaxes(title='Número de cuota', dtick=1 if len(pagos) < 20 else None, row=1, col=1)
    if not pagos.empty:
        ultima = int(pagos.iloc[-1]['Cuota'])
        fig.update_xaxes(tickvals=[ultima], ticktext=[f'Cuota {ultima} · cierre'],
            range=[ultima - 1, ultima + 1], row=1, col=2)
    return fig


def mejorar_tooltips_frances(fig, tabla):
    """Una sola explicación por cuota, compartida por las dos vistas francesas."""
    datos = tabla.set_index('Cuota')
    datos['Capital ordinario'] = datos['Capital'] - datos['Abono extra']
    datos['Cuota normal'] = datos['Pago'] - datos['Abono extra']
    columnas = ['Capital ordinario', 'Intereses', 'Cuota normal', 'Abono extra', 'Pago', 'Saldo pendiente']
    for indice, traza in enumerate(fig.data):
        if indice == 0:
            traza.customdata = datos.loc[list(traza.x), columnas].to_numpy()
            traza.hovertemplate = (
                '<b>📅 Cuota n.º %{x}</b><br><br>'
                '💳 <b>Valor de la cuota: $%{customdata[2]:,.0f}</b><br>'
                '🔴 Intereses incluidos: $%{customdata[1]:,.0f}<br>'
                '🟢 Capital incluido: $%{customdata[0]:,.0f}<br>'
                '<br>➕ Abono extra a capital: $%{customdata[3]:,.0f}<br>'
                '💰 <b>Total a pagar: $%{customdata[4]:,.0f}</b><br>'
                '<br>🏦 Deuda restante: <b>$%{customdata[5]:,.0f}</b>'
                '<extra></extra>')
        else:
            traza.hovertemplate = None
            traza.hoverinfo = 'skip'
    fig.update_layout(hovermode='x unified', separators=',.',
        hoverlabel=dict(bgcolor='#0B1829', bordercolor='#38BDF8',
            font=dict(family='Arial, sans-serif', size=14, color='#F8FAFC'),
            align='left', namelength=-1))
    return _agregar_plazo_tooltip(fig)


def cargos_mensuales(deuda):
    return tuple(max(0.0, numero(deuda.get(columna)) or 0.0)
                 for columna in ('Seguro', 'Costos extra'))


def proyectar_cuota_compensada(saldo, tasa, cuota_original, pago_fijo, abonos=None):
    """Recalcula la cuota requerida y compensa cada mes hasta el pago fijo."""
    referencia = proyectar_saldo(saldo, tasa, cuota_original)
    tabla = proyectar_saldo(saldo, tasa, pago_fijo, abonos=abonos)
    restante = len(referencia) - 1
    pendiente = saldo
    requerida = cuota_original
    extras = [0.0]
    automaticos = [0.0]
    for _, fila in tabla.iloc[1:].iterrows():
        ordinario = min(requerida, fila['Pago'] - fila['Abono extra'])
        automatico = max(0.0, fila['Pago'] - fila['Abono extra'] - ordinario)
        automaticos.append(automatico)
        extras.append(automatico + fila['Abono extra'])
        pendiente = fila['Saldo pendiente']
        restante = max(1, restante - 1)
        if extras[-1] > 0 and pendiente > 0:
            requerida = pendiente / restante if tasa == 0 else pendiente * tasa / (-math.expm1(-restante * math.log1p(tasa)))
    tabla['Abono extra'] = extras
    tabla['Abono automático'] = automaticos
    return tabla


def referencia_pago_original(deuda, saldo, tasa, cuota):
    original = cuota_financiera_excel(deuda)
    if original and original > saldo * tasa + .01:
        return proyectar_saldo(saldo, tasa, original)
    return proyectar_saldo(saldo, tasa, cuota)


def conservar_edicion_abonos(key, editor_key, filas):
    abonos = dict(st.session_state.get(key + '_abonos_tabla', {}))
    try:
        for posicion, cambios in st.session_state.get(editor_key, {}).get('edited_rows', {}).items():
            if 'Abono extra' in cambios:
                n = int(filas[int(posicion)])
                valor = interpretar_abono_tabla(cambios['Abono extra'], abonos.get(n))
                if valor > 0:
                    abonos[n] = valor
                else:
                    abonos.pop(n, None)
    except ValueError as exc:
        st.session_state[key + '_error_abono'] = str(exc)
        return
    st.session_state[key + '_abonos_tabla'] = abonos
    st.session_state.pop(key + '_error_abono', None)


def cuota_total_registrada(deuda):
    """Pago mensual del Excel, independiente de los valores de la simulación."""
    total = numero(deuda.get('Pago mensual'))
    return total if total is not None else 0.0


def cuota_financiera_excel(deuda):
    total = numero(deuda.get('Pago mensual'))
    return max(0.0, total - sum(cargos_mensuales(deuda))) if total is not None else None


def tabla_proyeccion(tabla, deuda=None):
    """Saldo de apertura y cierre explícitos para reconciliar cada mensualidad."""
    detalle = tabla.rename(columns={'Cuota': 'Cuota número',
        'Capital': 'Abono a capital', 'Saldo pendiente': 'Saldo restante', 'Pago': 'Pago total'}).copy()
    detalle['Abono extra'] = tabla.get('Abono extra', 0.0)
    detalle['Valor cuota'] = detalle['Pago total'] - detalle['Abono extra']
    detalle['Saldo inicial'] = detalle['Saldo restante'].shift(1)
    detalle.loc[detalle.index[0], 'Saldo inicial'] = detalle.iloc[0]['Saldo restante']
    columnas = ['Cuota número', 'Saldo inicial', 'Valor cuota', 'Intereses',
        'Abono extra', 'Abono a capital', 'Pago total', 'Saldo restante']
    if deuda is not None:
        seguro, costos_extra = cargos_mensuales(deuda)
        mensualidad = detalle['Cuota número'].gt(0)
        detalle['Seguro'] = mensualidad * seguro
        detalle['Costos extra'] = mensualidad * costos_extra
        detalle['Valor cuota'] += detalle['Seguro'] + detalle['Costos extra']
        detalle['Desembolso total'] = detalle['Valor cuota'] + detalle['Abono extra']
        columnas = columnas[:-1] + ['Seguro', 'Costos extra', 'Desembolso total', 'Saldo restante']
    if 'Abono automático' in tabla:
        detalle['Abono automático'] = tabla['Abono automático']
        detalle['Total abonos extra'] = detalle['Abono extra']
        detalle['Abono extra'] -= detalle['Abono automático']
        columnas.insert(columnas.index('Abono extra'), 'Abono automático')
        columnas.insert(columnas.index('Abono a capital'), 'Total abonos extra')
    return detalle[columnas]


def formatear_importe_tabla(valor):
    if pd.isna(valor):
        return ''
    return '$ ' + f'{float(valor):,.0f}'.replace(',', '.')


def interpretar_abono_tabla(valor, anterior=None):
    if valor is None or pd.isna(valor) or str(valor).strip() == '':
        return 0.0
    if not isinstance(valor, str):
        importe = numero(valor)
    else:
        entrada = valor.strip().replace('$', '').replace(' ', '').replace('\u00a0', '')
        # Un importe que solo cambió de presentación conserva sus centavos originales.
        if anterior is not None and entrada == f'{float(anterior):,.0f}'.replace(',', '.'):
            return float(anterior)
        if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]+)?', entrada):
            raise ValueError('Escribe los abonos como 1.000.000 o 1.000.000,50; deja la celda vacía para eliminar un abono.')
        importe = numero(entrada.replace('.', '').replace(',', '.'))
    if importe is None or importe < 0:
        raise ValueError('Los abonos deben ser importes positivos y válidos.')
    return importe


def mostrar_tarjeta_ahorro(titulo, valor, descripcion, positivo, tipo, tono=None):
    color = '#55F6B1' if positivo else '#7BD4FF'
    fondo = '#0B302A' if positivo else '#102E4A'
    borde = 'rgba(85,246,177,.28)' if positivo else 'rgba(123,212,255,.28)'
    if tono == 'rojo':
        color, fondo, borde = '#FF8A94', '#381B29', 'rgba(255,138,148,.48)'
    elif tono == 'verde':
        color, fondo, borde = '#55F6B1', '#0B302A', 'rgba(85,246,177,.48)'
    texto_estilo = f'--texto-tarjeta:{color};--texto-detalle:{color};' if tono else ''
    icono = ('<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>'
        if tipo == 'tiempo' else '<path d="M4 7h16v12H4zM4 7l11-4v4M15 12h5v4h-5z"/><circle cx="16.5" cy="14" r=".5"/>')
    if tipo == 'tiempo':
        cifra = valor.split(' ')[0]
        unidad = 'mes' if cifra == '1' else 'meses'
        contenido_valor = f'{html.escape(cifra)}<span class="ahorro-unidad">{unidad}</span>'
    else:
        contenido_valor = html.escape(valor)
    st.html(f'''<style>
    .altium-ahorro-card {{
        position:relative; isolation:isolate; overflow:hidden; box-sizing:border-box;
        container-type:inline-size;
        width:100%; min-height:125px; padding:15px 17px 13px 20px;
        border:1px solid var(--borde); border-radius:17px;
        background:radial-gradient(ellipse at 110% -20%,var(--fondo) 0%,transparent 80%),
            linear-gradient(135deg,#14263C 0%,#0A1829 100%);
        box-shadow:0 8px 22px rgba(0,0,0,.2),inset 0 1px 0 rgba(255,255,255,.055);
        font-family:Arial,sans-serif;
    }}
    .altium-ahorro-card::before {{
        content:""; position:absolute; left:0; top:18px; bottom:18px; width:3px;
        border-radius:0 5px 5px 0; background:var(--accent);
        box-shadow:0 0 16px var(--borde);
    }}
    .altium-ahorro-card::after {{
        content:""; position:absolute; z-index:-1; right:-30px; bottom:-65px;
        width:140px; height:140px; border-radius:50%;
        border:18px solid var(--accent); opacity:.035;
    }}
    .altium-ahorro-card .ahorro-encabezado {{display:flex;align-items:center;gap:9px;}}
    .altium-ahorro-card .ahorro-icono {{
        display:flex;align-items:center;justify-content:center;flex-shrink:0;
        width:29px;height:29px;border-radius:10px;
        background:var(--fondo);border:1px solid var(--borde);color:var(--accent);
    }}
    .altium-ahorro-card .ahorro-titulo {{font-size:12px;font-weight:600;color:var(--texto-tarjeta,#D5E3F1);line-height:1.3;}}
    .altium-ahorro-card .ahorro-valor {{
        font-size:clamp(20px,13cqw,30px);line-height:1.15;letter-spacing:-.7px;
        font-weight:700;color:var(--accent);margin-top:12px;white-space:nowrap;
        font-variant-numeric:tabular-nums;
    }}
    .altium-ahorro-card .ahorro-unidad {{
        font-size:13px;letter-spacing:0;margin-left:7px;font-weight:500;color:#ACBDCE;
    }}
    .altium-ahorro-card .ahorro-descripcion {{font-size:11px;color:var(--texto-detalle,#8FA9C1);margin-top:6px;line-height:1.3;}}
    </style>
    <div class="altium-ahorro-card" style="--accent:{color};--fondo:{fondo};--borde:{borde};{texto_estilo}" title="Comparado con la proyección sin abonos. Se actualiza al aplicar la simulación.">
        <div class="ahorro-encabezado">
            <span class="ahorro-icono" aria-hidden="true"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{icono}</svg></span>
            <span class="ahorro-titulo">{html.escape(titulo)}</span>
        </div>
        <div class="ahorro-valor">{contenido_valor}</div>
        <div class="ahorro-descripcion">{html.escape(descripcion)}</div>
    </div>''')


def _acciones_proyeccion(key, detalle, formulario=True):
    # El editor de la tabla confirma la celda al pulsar fuera, pero Streamlit
    # publica ese valor con retraso. Deja que llegue antes de enviar el formulario.
    components.html("""
        <script>
        const form = window.frameElement.closest('[data-testid="stForm"]');
        const page = form?.ownerDocument;
        if (page) {
            let pendingButton = null;
            let timer;
            function applyButton(event) {
                const button = event.target.closest('button');
                return button && form.contains(button) &&
                    button.textContent.trim() === 'Aplicar simulación' ? button : null;
            }
            function rememberEditor(event) {
                const button = applyButton(event);
                pendingButton = button && page.activeElement?.closest('.gdg-growing-entry')
                    ? button : null;
            }
            function waitForEdit(event) {
                const button = applyButton(event);
                if (!button || button !== pendingButton) return;
                pendingButton = null;
                event.preventDefault();
                event.stopImmediatePropagation();
                timer = window.setTimeout(() => {
                    if (button.isConnected) button.click();
                }, 250);
            }
            page.addEventListener('pointerdown', rememberEditor, true);
            page.addEventListener('click', waitForEdit, true);
            window.addEventListener('pagehide', () => {
                window.clearTimeout(timer);
                page.removeEventListener('pointerdown', rememberEditor, true);
                page.removeEventListener('click', waitForEdit, true);
            }, {once: true});
        }
        </script>
    """, height=0)
    aplicar_col, limpiar_col, csv_col, pdf_col = st.columns([1, 1, 1.5, 1])
    boton_aplicar = aplicar_col.form_submit_button if formulario else aplicar_col.button
    boton_limpiar = limpiar_col.form_submit_button if formulario else limpiar_col.button
    boton_pdf = pdf_col.form_submit_button if formulario else pdf_col.button
    opciones_boton = {} if formulario else {'key': key + '_aplicar_abonos'}
    aplicar = boton_aplicar('Aplicar simulación', type='primary', **opciones_boton,
                                             use_container_width=True)
    limpiar = boton_limpiar('Limpiar abonos', use_container_width=True, **({} if formulario else {'key': key + '_limpiar_abonos'}))
    csv = detalle.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    contenido = base64.b64encode(csv).decode('ascii')
    archivo = html.escape(key + '_proyeccion.csv', quote=True)
    # Streamlit 1.40 no admite download_button dentro de un formulario.
    csv_col.markdown(
        f'<a href="data:text/csv;base64,{contenido}" download="{archivo}" '
        'style="display:block;text-align:center;padding:.4rem .65rem;'
        'border:1px solid #64748b;border-radius:.5rem;color:inherit;text-decoration:none">'
        'Descargar tabla de proyección</a>', unsafe_allow_html=True)
    preparar_pdf = boton_pdf('Descargar PDF', use_container_width=True, **({} if formulario else {'key': key + '_preparar_pdf'}))
    return aplicar, limpiar, preparar_pdf


def _descargar_pdf(deuda, key, tabla, detalle, vista_grafico, tabla_base):
    from modules.report_pdf import generar_proyeccion_credito_pdf

    pdf = generar_proyeccion_credito_pdf(
        str(deuda.get('Nombre', 'Crédito')), tabla, detalle, vista_grafico,
        tabla_base=tabla_base, cuota_excel=cuota_total_registrada(deuda),
        pago_mensual=st.session_state.get(key + '_cuota_simulada_financiera',
            float(tabla.iloc[1]['Pago'] - tabla.iloc[1]['Abono extra'])) + sum(cargos_mensuales(deuda)))
    contenido = base64.b64encode(pdf).decode('ascii')
    archivo = html.escape(key + '_proyeccion.pdf', quote=True)
    components.html(f'''
        <a id="proyeccion" href="data:application/pdf;base64,{contenido}" download="{archivo}"></a>
        <script>document.getElementById('proyeccion').click();</script>
    ''', height=0)


def _mostrar_proyeccion_no_frances(deuda, key, metodo, nombre_metodo, constructor, ingles=False):
    st.markdown(f'#### Avance proyectado · amortización {nombre_metodo}')
    saldo = numero(deuda.get('Saldo'))
    tasa = numero(deuda.get('Interés'))
    if saldo is None or saldo <= 0:
        return
    if tasa is None or tasa < 0:
        st.info('Falta una tasa de interés mensual válida para proyectar este crédito.')
        return
    if tasa > 1:
        tasa /= 100

    sugeridas = cuotas_restantes_estimadas(deuda)
    if sugeridas is None:
        st.info('Registra un número entero de cuotas en Pasivos para proyectar el saldo de este crédito.')
        return
    fecha_inicio = pd.to_datetime(deuda.get('Inicio del crédito'), errors='coerce')
    firma = (metodo, float(saldo), float(tasa), numero(deuda.get('Cuotas totales')),
        None if pd.isna(fecha_inicio) else fecha_inicio.isoformat())
    clave_plazo = key + '_cuotas_restantes'
    if st.session_state.get(key + '_firma_plazo') != firma:
        st.session_state[clave_plazo] = int(sugeridas)
        st.session_state[key + '_firma_plazo'] = firma
    plazo = int(sugeridas)

    if ingles:
        m1, m2, m4 = st.columns(3)
        m3, m5 = st.columns([1, 2])
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
    clave_cuota = key + '_cuota_editable'
    firma_cuota = (metodo, saldo, tasa, int(plazo))
    cuota_recomendada = round(saldo * tasa + (0 if ingles else saldo / int(plazo)), 2)
    if (st.session_state.get(key + '_firma_cuota_editable') != firma_cuota
            or clave_cuota not in st.session_state
            or (st.session_state.get(clave_cuota, 0) == 0 and cuota_recomendada > 0)):
        st.session_state[clave_cuota] = cuota_recomendada
        st.session_state[key + '_firma_cuota_editable'] = firma_cuota
    selector_metodo = key + ('_vista_alemana_cuotas' if metodo == 'aleman' else '_vista_unificada')
    estilo_cuota = ''.join(c for c in key if c.isalnum() or c == '_') + '_tarjeta_cuota'
    st.markdown(f'''<style>
        .st-key-{estilo_cuota} {{
            background:linear-gradient(145deg,#10283c,#071322);
            border:1px solid #38bdf8 !important;border-radius:16px;
            box-shadow:0 4px 18px rgba(56,189,248,.10);
        }}
        .st-key-{estilo_cuota} [data-testid="stNumberInputContainer"] {{
            border:1px solid #345570;border-radius:10px;background:#071322;
        }}
        .st-key-{estilo_cuota} input {{
            color:#f0f9ff !important;font-size:22px !important;
            font-weight:700 !important;background:#071322 !important;
        }}
        .st-key-{estilo_cuota} [data-testid="stNumberInputContainer"]:focus-within {{
            border-color:#38bdf8;box-shadow:0 0 0 2px rgba(56,189,248,.18);
        }}
        .st-key-{selector_metodo} [role="radiogroup"] {{display:flex !important;flex-direction:row !important;flex-wrap:nowrap !important;gap:4px !important;justify-content:center !important;width:100% !important;}}
        .st-key-{selector_metodo} [role="radiogroup"] label {{white-space:nowrap !important;padding:3px 5px !important;margin:0 !important;gap:3px !important;}}
        .st-key-{selector_metodo} [role="radiogroup"] label p {{font-size:13px !important;line-height:1.2 !important;white-space:nowrap !important;}}
    </style>''', unsafe_allow_html=True)
    with m5.container(border=True, height=170, key=estilo_cuota):
        st.markdown('<div style="font-size:14px;font-weight:600;color:#e2e8f0;">Cuota mensual</div>'
            '<div style="font-size:12px;color:#93c5df;margin-top:2px;">Capital + intereses · valor en $</div>',
            unsafe_allow_html=True)
        cuota_editada = st.number_input('Cuota mensual de capital e intereses', min_value=0.0,
            step=10000.0, label_visibility='collapsed', format='%.2f', key=clave_cuota)
        vista_grafico = st.radio('Vista del gráfico', ['Saldo pendiente', 'Cuota mensual'],
            index=1 if ingles or metodo == 'aleman' else 0,
            horizontal=True, key=selector_metodo, label_visibility='collapsed')
    try:
        firma_abonos = (metodo, saldo, tasa, int(plazo))
        if st.session_state.get(key + '_firma_nuevos_abonos') != firma_abonos:
            st.session_state[key + '_nuevos_abonos'] = {}
            st.session_state[key + '_firma_nuevos_abonos'] = firma_abonos
            st.session_state[key + '_editor_version'] = st.session_state.get(key + '_editor_version', 0) + 1
        abonos = st.session_state.get(key + '_nuevos_abonos', {})
        tabla_base = constructor(saldo, tasa, int(plazo), cuota=cuota_editada)
        modo_abonos = st.session_state.get(key + '_nuevo_modo_abonos', 'plazo')
        tabla = constructor(saldo, tasa, int(plazo), abonos=abonos, cuota=cuota_editada) if ingles else constructor(
            saldo, tasa, int(plazo), abonos=abonos, reduccion=modo_abonos, cuota=cuota_editada)
    except ValueError as exc:
        st.info(str(exc))
        return
    cuota_mensual = float(tabla.iloc[1]['Pago'] - tabla.iloc[1]['Abono extra']) if len(tabla) > 1 else 0.0
    seguro, costos = cargos_mensuales(deuda)
    with m1.container(border=True, height=170):
        meses = len(tabla) - 1
        st.metric('Tiempo hasta terminar' if ingles else 'Cuotas restantes estimadas',
            _texto_plazo(meses) if ingles else meses)
    with m2.container(border=True, height=170):
        st.metric('Pago mensual inicial' if ingles else 'Cuota con seguro y cargos',
            ('$' + f'{cuota_mensual + seguro + costos:,.0f}'.replace(',', '.')) if ingles else f'${cuota_total_registrada(deuda):,.0f}',
            help='Primera cuota proyectada con seguro y cargos, sin abonos adicionales; si solo queda una cuota, incluye el cierre.' if ingles else 'Pago mensual total registrado en el Excel, incluido seguro y costos extra.')
    with m3.container(border=True, height=170):
        st.metric('Intereses futuros estimados', f"${tabla['Intereses'].sum():,.0f}")
    with m4.container(border=True, height=170):
        st.metric('Pago final estimado' if ingles else 'Total por pagar estimado',
            ('$' + f"{float(tabla.iloc[-1]['Pago']) + seguro + costos:,.0f}".replace(',', '.')) if ingles else f"${tabla['Pago'].sum():,.0f}",
            help='Última cuota de la simulación: capital, intereses, abono adicional, seguro y cargos.' if ingles else None)
    st.caption('La cuota cubre intereses y cualquier excedente reduce capital; la última incluye el saldo pendiente.' if ingles
        else 'Se muestra la primera cuota ordinaria de la proyección, sin abono extra. Las siguientes disminuyen al bajar los intereses.')

    fig = mejorar_tooltips_frances(crear_grafico_saldo(tabla), tabla)
    fig.update_layout(title=f"Proyección del saldo · {str(deuda.get('Nombre', 'Crédito'))}")
    panel = ''.join(c for c in key if c.isalnum() or c == '_') + '_panel_noche'
    st.markdown(f'''<style>
        .st-key-{panel} {{
            background:linear-gradient(155deg,#10243A 0%,#07111F 60%);
            border:1px solid #284562;border-top:2px solid #38BDF8;border-radius:20px;
            padding:12px 10px 2px;box-shadow:0 12px 32px rgba(0,0,0,.24);
            margin:12px 0;overflow:hidden;
        }}
    </style>''', unsafe_allow_html=True)
    if vista_grafico == 'Cuota mensual':
        constructor_grafico = crear_grafico_cuotas_ingles if ingles else crear_grafico_cuotas_aleman
        fig = constructor_grafico(tabla) if ingles else mejorar_tooltips_frances(constructor_grafico(tabla), tabla)
        if not ingles:
            fig.update_layout(title=f'Amortización {nombre_metodo} · composición de la cuota mensual')
    with st.container(key=panel):
        st.plotly_chart(fig, use_container_width=True, key=key + '_grafico', theme=None,
            config={'displaylogo': False, 'toImageButtonOptions': {
                'format': 'png', 'filename': key + '_proyeccion', 'width': 1400, 'height': 650, 'scale': 2}})
    if ingles:
        st.caption('El pago de cierre aparece a la derecha y usa su propia escala vertical. Los gráficos desglosan capital, intereses y abonos; el seguro y los cargos se incluyen en las tarjetas y en la tabla.')
        if vista_grafico == 'Cuota mensual':
            st.markdown('##### Así cambia lo que debes')
            st.plotly_chart(mejorar_tooltips_frances(crear_grafico_saldo(tabla), tabla),
                use_container_width=True, key=key + '_saldo_ingles', theme=None,
                config={'displaylogo': False})
    nota = ('La cuota cubre los intereses y cualquier excedente reduce capital; al vencimiento se paga el saldo restante.' if ingles
        else 'El capital ordinario por cuota es constante; al reducir cuota con un abono se recalcula para el plazo restante.')
    st.caption(nota + ' Se parte del saldo actual, con tasa mensual constante. El valor de la cuota incluye seguro y costos extra del Excel. El desembolso total agrega los abonos extraordinarios. El plazo se estima con las cuotas registradas y los meses completos desde Inicio del crédito.')
    st.markdown('##### Tabla de proyección')
    detalle = tabla_proyeccion(tabla, deuda)
    st.caption('Edita Abono extra y pulsa Aplicar simulación. Los ahorros se comparan con el mismo crédito sin abonos extra.')
    editable = detalle.set_index('Cuota número').reindex(range(1, max(len(tabla_base), len(tabla), max(abonos, default=0) + 1))).reset_index()
    editable['Abono extra'] = [f'{abonos[int(n)]:,.0f}'.replace(',', '.') if int(n) in abonos else '' for n in editable['Cuota número']]
    version = st.session_state.get(key + '_editor_version', 0)
    with st.form(key=key + '_nuevos_abonos_form', border=False, enter_to_submit=False):
        opciones, tarjeta_tiempo, tarjeta_dinero = st.columns([1.8, 1.1, 1.1])
        with opciones:
            if not ingles:
                objetivo_abonos = st.radio('Aplicar abonos para', ['Reducir tiempo', 'Reducir cuota'],
                    horizontal=True, key=key + '_nuevo_tipo_abono',
                    help='Reducir tiempo conserva el capital ordinario por cuota. Reducir cuota reparte el saldo posterior al abono entre las cuotas restantes y conserva el vencimiento, salvo pago total anticipado.')
            else:
                st.caption('Los abonos reducen el capital y los intereses futuros. El vencimiento se mantiene hasta que los abonos cancelen todo el capital; entonces también se ahorra tiempo.')
        meses_ahorrados = max(0, len(tabla_base) - len(tabla))
        dinero_ahorrado = max(0.0, float(tabla_base['Intereses'].sum() - tabla['Intereses'].sum()))
        with tarjeta_tiempo:
            mostrar_tarjeta_ahorro('Tiempo ahorrado', f'{meses_ahorrados} meses',
                'menos de crédito', meses_ahorrados > 0, 'tiempo', tono='rojo' if ingles else 'verde')
        with tarjeta_dinero:
            mostrar_tarjeta_ahorro('Dinero ahorrado', '$' + f'{dinero_ahorrado:,.0f}'.replace(',', '.'),
                'de ahorro en intereses', round(dinero_ahorrado) > 0, 'dinero', tono='rojo' if ingles else 'verde')
        edicion = st.data_editor(editable.style.format(formatear_importe_tabla,
            subset=[c for c in editable.columns if c not in {'Cuota número', 'Abono extra'}]),
            hide_index=True, use_container_width=True, num_rows='fixed',
            key=key + '_nuevos_editor_' + str(version),
            disabled=[c for c in editable.columns if c != 'Abono extra'],
            column_config={'Abono extra': st.column_config.TextColumn('Abono extra', help='Ejemplo: 1.000.000 o 1.000.000,50. Vacío elimina el abono.')})
        aplicar, limpiar, preparar_pdf = _acciones_proyeccion(key, detalle)
    if preparar_pdf:
        _descargar_pdf(deuda, key, tabla, detalle, vista_grafico, tabla_base)
    if aplicar or limpiar:
        try:
            nuevos = {}
            if not limpiar:
                for _, fila in edicion.iterrows():
                    n = int(fila['Cuota número'])
                    importe = interpretar_abono_tabla(fila['Abono extra'], abonos.get(n))
                    if importe > 0:
                        nuevos[n] = importe
            st.session_state[key + '_nuevos_abonos'] = nuevos
            if not ingles:
                st.session_state[key + '_nuevo_modo_abonos'] = 'cuota' if objetivo_abonos == 'Reducir cuota' else 'plazo'
            st.session_state[key + '_editor_version'] = version + 1
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.rerun()


def mostrar_proyeccion_credito(deuda, key):
    if texto(deuda.get('Hoja origen')) != 'pasivos':
        return
    if not st.session_state.get(key + '_mostrar_amortizacion', False):
        return
    sistema = texto(deuda.get('Sistema de amortización'))
    tipo = texto(deuda.get('Tipo'))
    etiquetas = {'frances', 'francesa', 'sistema frances', 'amortizacion francesa', 'credito frances'}
    sistema = sistema or tipo
    if sistema not in etiquetas:
        aleman = {'aleman', 'alemana', 'sistema aleman', 'amortizacion alemana', 'credito aleman'}
        ingles = {'ingles', 'inglesa', 'sistema ingles', 'amortizacion inglesa', 'credito ingles'}
        americano = {'americano', 'americana', 'sistema americano', 'amortizacion americana', 'credito americano'}
        if sistema in aleman:
            if st.session_state.get(key + '_mostrar_amortizacion', False):
                _mostrar_proyeccion_no_frances(deuda, key, 'aleman', 'alemana', proyectar_aleman)
        elif sistema in ingles:
            _mostrar_proyeccion_no_frances(deuda, key, 'ingles', 'inglesa', proyectar_ingles, ingles=True)
        elif sistema in americano:
            _mostrar_proyeccion_no_frances(deuda, key, 'americano', 'americana', proyectar_ingles, ingles=True)
        return
    saldo = numero(deuda.get('Saldo'))
    if saldo is None or saldo <= 0:
        return
    st.markdown('#### Avance proyectado · amortización francesa')
    selector_frances = key + '_vista_grafico_frances'
    st.markdown(f'''<style>
        .st-key-{selector_frances} [role="radiogroup"] {{
            display:flex !important;flex-direction:row !important;
            flex-wrap:nowrap !important;gap:4px !important;
            justify-content:center !important;width:100% !important;
        }}
        .st-key-{selector_frances} [role="radiogroup"] label {{
            white-space:nowrap !important;min-width:0 !important;
            padding:3px 5px !important;margin:0 !important;gap:3px !important;
        }}
        .st-key-{selector_frances} [role="radiogroup"] label p {{
            font-size:13px !important;line-height:1.2 !important;white-space:nowrap !important;
        }}
    </style>''', unsafe_allow_html=True)
    tasa = numero(deuda.get('Interés'))
    if tasa is None or tasa < 0:
        st.info('Falta una tasa de interés mensual válida para proyectar este crédito.')
        return
    if tasa > 1:
        tasa /= 100
    cuota = cuota_financiera_excel(deuda)
    selector_modo, opciones_derecha = st.columns([1, 3])
    with selector_modo:
        objetivo_abonos = st.radio('Aplicar abonos para', ['Reducir tiempo', 'Reducir cuota'],
            horizontal=True, key=key + '_tipo_abono')
    reducir_cuota = objetivo_abonos == 'Reducir cuota'
    pago_extra_mensual = 0.0
    compensar_cuota = False
    with opciones_derecha:
        if reducir_cuota:
            opciones_pago, campo_extra = st.columns([3, 1])
            with opciones_pago:
                opciones_anteriores = {
                    'Crédito normal sin extra mensual': 'Pagar la cuota mínima',
                    'Mantener la misma cuota': 'Mantener siempre el pago inicial',
                    'Misma cuota más extra': 'Pago inicial + extra mensual',
                }
                clave_opcion = key + '_pago_compensado'
                if st.session_state.get(clave_opcion) in opciones_anteriores:
                    st.session_state[clave_opcion] = opciones_anteriores[st.session_state[clave_opcion]]
                opcion = st.radio('¿Cuánto quieres pagar cada mes?',
                    ['Pagar la cuota mínima', 'Mantener siempre el pago inicial', 'Pago inicial + extra mensual'],
                    horizontal=True, key=key + '_pago_compensado')
            compensar_cuota = opcion != 'Pagar la cuota mínima'
            if opcion == 'Pago inicial + extra mensual':
                with campo_extra:
                    pago_extra_mensual = st.number_input('Extra mensual a capital', min_value=0.0,
                        value=0.0, step=50000.0, key=key + '_extra_compensado')
            if compensar_cuota:
                st.caption('Se mantiene como pago la cuota original del Excel más el extra indicado. La diferencia con la cuota reducida se abona automáticamente a capital.')
    st.session_state[key + '_compensar_cuota'] = compensar_cuota
    cuota_editable = True
    tarjetas = st.columns(5 if cuota_editable else 4)
    c1, c2, c3, c4 = tarjetas[:4]
    c5 = tarjetas[4] if cuota_editable else None
    if cuota_editable:
        cargos = sum(cargos_mensuales(deuda))
        plazo = cuotas_restantes_estimadas(deuda)
        sugerida = numero(deuda.get('Pago mensual')) if cuota and cuota > 0 else None
        if sugerida is None and plazo:
            financiera = saldo / plazo if tasa == 0 else saldo * tasa / (-math.expm1(-plazo * math.log1p(tasa)))
            sugerida = financiera + cargos
            st.caption(f'Cuota estimada para {plazo} pagos restantes, con los cargos mensuales registrados.')
        clave_total = key + '_cuota_total'
        firma_cuota_francesa = (saldo, tasa, plazo, sugerida, cargos)
        if st.session_state.get(key + '_firma_cuota_calculada') != firma_cuota_francesa or clave_total not in st.session_state:
            st.session_state[clave_total] = round(sugerida or 0.0, 2)
            st.session_state[key + '_firma_cuota_calculada'] = firma_cuota_francesa
        estilo_cuota = ''.join(c for c in key if c.isalnum() or c == '_') + '_tarjeta_cuota'
        st.markdown(f'''<style>
            .st-key-{estilo_cuota} {{
                background:linear-gradient(145deg,#10283c,#071322);
                border:1px solid #38bdf8 !important;
                border-radius:16px;
                box-shadow:0 4px 18px rgba(56,189,248,.10);
            }}
            .st-key-{estilo_cuota} [data-testid="stNumberInputContainer"] {{
                border:1px solid #345570;
                border-radius:10px;
                background:#071322;
            }}
            .st-key-{estilo_cuota} input {{
                color:#f0f9ff !important;
                font-size:22px !important;
                font-weight:700 !important;
                background:#071322 !important;
            }}
            .st-key-{estilo_cuota} [data-testid="stNumberInputContainer"]:focus-within {{
                border-color:#38bdf8;
                box-shadow:0 0 0 2px rgba(56,189,248,.18);
            }}
        </style>''', unsafe_allow_html=True)
        with c5.container(border=True, height=170, key=estilo_cuota):
            st.markdown('<div style="font-size:14px;font-weight:600;color:#e2e8f0;">Cuota mensual</div>'
                '<div style="font-size:12px;color:#93c5df;margin-top:2px;">Capital, intereses, seguro y cargos</div>',
                unsafe_allow_html=True)
            cuota_total = st.number_input('Cuota mensual a pagar', min_value=0.0,
                step=10000.0, key=clave_total, format='%.2f', disabled=reducir_cuota,
                label_visibility='collapsed',
                help='Ingresa el pago completo del extracto. Altium descuenta el seguro y los costos extra para amortizar.')
            vista_frances = st.radio('Vista del gráfico', ['Saldo pendiente', 'Cuota mensual'],
                key=key + '_vista_grafico_frances', label_visibility='collapsed', horizontal=True)
        cuota = round((sugerida + pago_extra_mensual if reducir_cuota else cuota_total) - cargos, 2)
        if cuota <= 0:
            st.caption('Introduce la cuota mensual para dibujar el saldo hasta terminar de pagar.')
            return
    try:
        tabla = proyectar_saldo(saldo, tasa, cuota)
    except ValueError as exc:
        st.info(str(exc))
        return
    tabla_base = referencia_pago_original(deuda, saldo, tasa, cuota)
    firma_abonos = (float(saldo), float(tasa), float(cuota))
    if st.session_state.get(key + '_firma_abonos') != firma_abonos:
        st.session_state[key + '_firma_abonos'] = firma_abonos
        st.session_state.setdefault(key + '_abonos_tabla', {})
        st.session_state[key + '_version_abonos'] = st.session_state.get(key + '_version_abonos', 0) + 1
    abonos = st.session_state.get(key + '_abonos_tabla', {})
    modo_abonos = 'cuota' if st.session_state.get(key + '_tipo_abono') == 'Reducir cuota' else 'plazo'
    st.session_state[key + '_modo_abonos'] = modo_abonos
    if reducir_cuota and compensar_cuota:
        tabla = proyectar_cuota_compensada(saldo, tasa, cuota_financiera_excel(deuda) or cuota, cuota, abonos)
    elif abonos:
        tabla = proyectar_saldo(saldo, tasa, cuota, abonos=abonos, reduccion=modo_abonos)
    st.session_state[key + '_cuota_simulada_financiera'] = cuota
    with c1.container(border=True, height=170):
        st.metric('Cuotas restantes estimadas', len(tabla) - 1)
    cuota_mostrada = cuota
    if abonos and modo_abonos == 'cuota':
        ultimo_abono = max(abonos, default=0)
        siguientes = tabla.loc[tabla['Cuota'].gt(ultimo_abono)]
        cuota_mostrada = float(siguientes.iloc[0]['Pago'] - siguientes.iloc[0]['Abono extra']) if not siguientes.empty else 0.0
    with c2.container(border=True, height=170):
        st.metric('Cuota con seguro y cargos', f'${cuota_total_registrada(deuda):,.0f}',
                  help='Pago mensual total registrado en el Excel, incluido seguro y costos extra.')
        if c5 is None:
            vista_frances = st.radio('Vista del gráfico', ['Saldo pendiente', 'Cuota mensual'],
                key=key + '_vista_grafico_frances', label_visibility='collapsed', horizontal=True)
    with c3.container(border=True, height=170):
        st.metric('Intereses futuros estimados', f"${tabla['Intereses'].sum():,.0f}")
    with c4.container(border=True, height=170):
        st.metric('Total por pagar estimado', f"${tabla['Pago'].sum():,.0f}")
    if vista_frances == 'Saldo pendiente':
        fig = crear_grafico_saldo(tabla)
        fig.update_layout(title=f"Proyección del saldo · {str(deuda.get('Nombre', 'Crédito'))}")
    else:
        fig = crear_grafico_cuotas_aleman(tabla)
        fig.update_layout(title='Amortización francesa · composición de la cuota mensual')
    fig = mejorar_tooltips_frances(fig, tabla)
    panel = ''.join(c for c in key if c.isalnum() or c == '_') + '_panel_noche'
    st.markdown(f'''<style>
        .st-key-{panel} {{
            background:linear-gradient(155deg,#10243A 0%,#07111F 60%);
            border:1px solid #284562;
            border-top:2px solid #38BDF8;
            border-radius:20px;
            padding:12px 10px 2px;
            box-shadow:0 12px 32px rgba(0,0,0,.24),0 0 18px rgba(56,189,248,.04);
            margin:12px 0;
            overflow:hidden;
        }}
    </style>''', unsafe_allow_html=True)
    with st.container(key=panel):
        st.plotly_chart(fig, use_container_width=True, key=key + '_grafico', theme=None,
            config={'displaylogo': False, 'toImageButtonOptions': {
                'format': 'png', 'filename': key + '_proyeccion', 'width': 1400, 'height': 650, 'scale': 2}})
    st.caption('Proyección desde el saldo registrado en el Excel, con tasa mensual constante y los abonos que selecciones. El valor de la cuota incluye seguro y costos extra del Excel. El desembolso total agrega los abonos extraordinarios. Cada barra combina el capital amortizado desde el saldo actual (verde) y el saldo pendiente (rojo). Cuota 0 = saldo actual; la última cuota se ajusta al importe restante. No representa pagos ya realizados. Usa la cámara del gráfico para descargar la imagen.')
    detalle = tabla_proyeccion(tabla, deuda)
    if reducir_cuota:
        st.caption('Valor cuota muestra la cuota requerida con seguro y cargos. Desembolso total muestra lo que pagas ese mes. Abono automático compensa la reducción y Abono extra permite añadir pagos puntuales.')
    st.markdown('##### Tabla de proyección')
    st.caption('Escribe abonos directamente en la columna «Abono extra» y pulsa «Aplicar simulación». Puedes completar varias cuotas o borrar importes. Elige si quieres reducir el tiempo o la cuota mensual. El Excel no se modifica.')
    # Filas estables para poder mover o borrar abonos después de acortar el plazo.
    editable = detalle.set_index('Cuota número').reindex(range(1, max(len(tabla_base), len(tabla), max(abonos, default=0) + 1)))
    editable.index.name = 'Cuota número'
    editable = editable.reset_index()
    editable['Abono extra'] = [f'{abonos[int(n)]:,.0f}'.replace(',', '.') if int(n) in abonos else '' for n in editable['Cuota número']]
    version_editor = st.session_state.get(key + '_version_abonos', 0)
    meses_ahorrados = max(0, len(tabla_base) - len(tabla))
    intereses_ahorrados = max(0.0, float(tabla_base['Intereses'].sum() - tabla['Intereses'].sum()))
    st.caption('El ahorro compara la simulación completa con el pago original del Excel. Los abonos se guardan al confirmar la celda.')
    prefijo_ahorro = ''.join(c for c in key if c.isalnum() or c == '_')
    # Cada edición se conserva en el estado del editor antes de cambiar de gráfica.
    # Aplicar sigue siendo explícito: editar no modifica la simulación activa.
    with st.container(key=key + '_formulario_abonos', border=False):
        opciones_abono, tarjeta_tiempo, tarjeta_dinero = st.columns([1.8, 1.1, 1.1])
        with opciones_abono:
            st.caption('Los abonos puntuales se suman al pago mensual seleccionado arriba.')
        with tarjeta_tiempo:
            mostrar_tarjeta_ahorro('Tiempo ahorrado', f'{meses_ahorrados} meses',
                'menos de crédito', meses_ahorrados > 0, 'tiempo')
        with tarjeta_dinero:
            mostrar_tarjeta_ahorro('Dinero ahorrado', '$' + f'{intereses_ahorrados:,.0f}'.replace(',', '.'),
                'de ahorro en intereses', round(intereses_ahorrados) > 0, 'dinero')
        presentacion = editable.style.format(formatear_importe_tabla,
            subset=[col for col in editable.columns if col not in {'Cuota número', 'Abono extra'}])
        edicion = st.data_editor(presentacion, hide_index=True, use_container_width=True,
            key=key + '_editor_abonos_' + str(version_editor), num_rows='fixed',
            on_change=conservar_edicion_abonos,
            args=(key, key + '_editor_abonos_' + str(version_editor), editable['Cuota número'].tolist()),
            disabled=[col for col in editable.columns if col != 'Abono extra'],
            column_config={'Cuota número': st.column_config.NumberColumn('Cuota número', format='%d'),
                'Abono extra': st.column_config.TextColumn('Abono extra',
                    help='Escribe 1.000.000 para un millón. Puedes usar coma para centavos, por ejemplo 1.000.000,50. Vacío significa sin abono.')})
        aplicar, limpiar, preparar_pdf = _acciones_proyeccion(key, detalle, formulario=False)
    if st.session_state.get(key + '_error_abono'):
        st.error(st.session_state[key + '_error_abono'])
    if preparar_pdf:
        _descargar_pdf(deuda, key, tabla, detalle, vista_frances, tabla_base)
    if aplicar or limpiar:
        try:
            nuevos = {}
            if not limpiar:
                for _, fila in edicion.iterrows():
                    n = int(fila['Cuota número'])
                    importe = interpretar_abono_tabla(fila['Abono extra'], abonos.get(n))
                    if importe > 0:
                        nuevos[n] = importe
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state[key + '_abonos_tabla'] = nuevos
            st.session_state[key + '_modo_abonos'] = 'cuota' if objetivo_abonos == 'Reducir cuota' else 'plazo'
            st.session_state[key + '_version_abonos'] = version_editor + 1
            st.rerun()
    if abonos:
        aplicado = float(tabla['Abono extra'].sum())
        ahorro = max(0.0, float(tabla_base['Intereses'].sum() - tabla['Intereses'].sum()))
        resultado_abonos = f'Cuota posterior: ${cuota_mostrada:,.0f}' if modo_abonos == 'cuota' else f'Cuotas ahorradas: {len(tabla_base) - len(tabla)}'
        st.success(f'Abonos aplicados: ${aplicado:,.0f} · {resultado_abonos} · Ahorro estimado en intereses: ${ahorro:,.0f}')
        st.caption('Las filas posteriores al pago total quedan sin proyección para que puedas reubicar los abonos. Los importes se limitan al capital pendiente; no se aplican después de cancelar la deuda.')
