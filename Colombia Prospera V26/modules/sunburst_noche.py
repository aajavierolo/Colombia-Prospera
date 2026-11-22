"""Sunburst de categorías con un centro total y paleta Altium Noche."""
from html import escape
import re
import textwrap
import plotly.graph_objects as go
from modules.categorias_noche import _identidad, _pesos


def _icono_blanco(icono):
    # Fuente de símbolos monocroma + presentación de texto (VS15).
    # El color de un emoji no cambia con textfont.color.
    simbolo = str(icono).replace("\ufe0f", "").replace("\ufe0e", "") + "\ufe0e"
    return ('<span style="font-family:Segoe UI Symbol,DejaVu Sans,sans-serif;'
            'color:#FFFFFF;font-size:32px">' + simbolo + '</span>')


def aplicar_sunburst_noche(original):
    if not original.data:
        return original
    origen = original.data[0]
    nodos = list(zip(origen.ids, origen.labels, origen.parents, origen.values, origen.customdata))
    categorias = [(n, nombre, valor) for n, nombre, padre, valor, _ in nodos if not padre]
    total = sum(v for _, _, v in categorias)
    raiz = "__altium_total_gastos__"
    while raiz in origen.ids:
        raiz += "_"
    estilos = {n: _identidad(nombre, i) for i, (n, nombre, _) in enumerate(categorias)}
    ids, nombres, padres, valores = [raiz], ["GASTO TOTAL"], [""], [total]
    colores = ["#10254A"]
    textos = [_icono_blanco("💼") + "<br>GASTO TOTAL<br><b>" + _pesos(total) + "</b>"]
    ayudas = ["💰 GASTO TOTAL: <b>" + _pesos(total) + "</b>"]
    for n, nombre, padre, valor, ayuda in nodos:
        icono, color = estilos[padre or n]
        ids.append(n)
        nombres.append(str(nombre).upper())
        padres.append(padre or raiz)
        valores.append(valor)
        if padre:
            rgb = [int(color[k:k+2], 16) for k in (1, 3, 5)]
            color = "#" + "".join(format(int(c*.79), "02x") for c in rgb)
        colores.append(color)
        titulo = escape(str(nombre).upper())
        textos.append(_icono_blanco(icono) + "<br><b>" + titulo + "</b>" if not padre else titulo)
        ayuda = re.sub(r"\$([\d,]+)", lambda m: "$" + m[1].replace(",", "."), str(ayuda))
        ayudas.append(re.sub(r"([+-]?\d+)\.(\d+)%", r"\1,\2%", ayuda))
    fig = go.Figure(go.Sunburst(
        ids=ids, labels=nombres, parents=padres, values=valores,
        branchvalues="total", text=textos, texttemplate="%{text}<br>%{percentEntry:.1%}",
        customdata=ayudas, hovertemplate="%{customdata}<br>📊 % DE LA VISTA ACTUAL: <b>%{percentEntry:.1%}</b><extra></extra>",
        sort=True, rotation=90, insidetextorientation="auto",
        marker=dict(colors=colores, line=dict(color="rgba(226,232,240,.55)", width=1)),
        textfont=dict(family="Arial, sans-serif", size=14, color="#FFFFFF"),
        hoverlabel=dict(bgcolor="#111F33", bordercolor="#284562",
                        font=dict(size=13, color="#F8FAFC"), align="left"),
    ))
    fig.update_layout(
        height=720, paper_bgcolor="#07152E", plot_bgcolor="#07152E",
        margin=dict(l=20, r=20, t=90, b=20), separators=",.",
        title=dict(text="<b>¿EN QUÉ CATEGORÍAS GASTO?</b><br>"
                        "<sup>DISTRIBUCIÓN POR CATEGORÍA Y SUBCATEGORÍA</sup>",
                   x=.025, y=.97, font=dict(size=19, color="#F8FAFC")),
        font=dict(family="Arial, sans-serif", color="#E2E8F0"),
        # Sin mínimo uniforme: Plotly puede reducir las letras de sectores estrechos.
        annotations=[],
    )
    # Lista completa dentro del panel: una porción pequeña nunca deja
    # una categoría sin nombre ni obliga a falsear el tamaño del sector.
    ordenadas = sorted(categorias, key=lambda item: item[2], reverse=True)
    alto = max(720, 125 + len(ordenadas) * 68)
    fig.update_layout(height=alto)
    fig.update_traces(domain=dict(x=[0, .73], y=[0, 1]))
    fig.add_annotation(x=.76, y=1, xref="paper", yref="paper", xanchor="left",
                       yanchor="top", showarrow=False, text="<b>TODAS LAS CATEGORÍAS</b><br><sup>% SOBRE EL GASTO TOTAL</sup>",
                       font=dict(size=12, color="#B4C9D9"))
    for i, (n, nombre, valor) in enumerate(ordenadas):
        _, color = estilos[n]
        nombre_lineas = "<br>".join(escape(linea) for linea in textwrap.wrap(str(nombre).upper(), width=23))
        pct = format(valor / total * 100 if total else 0, ".1f").replace(".", ",")
        fig.add_annotation(
            x=.76, y=.94 - i * (.91 / max(len(ordenadas), 1)),
            xref="paper", yref="paper", xanchor="left", yanchor="top",
            showarrow=False, align="left",
            text='<span style="color:' + color + '">●</span> <b>' + nombre_lineas
                 + '</b><br><span style="color:#B4C9D9">' + _pesos(valor) + ' · ' + pct + '%</span>',
            font=dict(size=12, color="#FFFFFF"),
        )
    return fig
