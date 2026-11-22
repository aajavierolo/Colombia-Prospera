"""Presentación Altium Noche del mapa de categorías, sin alterar sus importes."""
from html import escape
import re
import unicodedata


def _clave(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).upper())
                   if unicodedata.category(c) != "Mn")


def _identidad(nombre, indice):
    estilos = [
        ("IMPUEST", "🏛️", "#E91687"),
        ("ALIMENT", "🛒", "#8238F4"),
        ("HIJ", "👤", "#E63279"),
        ("CREDIT", "💳", "#1678EE"),
        ("DEUDA", "💳", "#1678EE"),
        ("VIVIEN", "🏠", "#00BE85"),
        ("CARRO", "🚘", "#08A8CB"),
        ("MOTO", "🛵", "#F18B13"),
        ("EDUC", "🎓", "#7652E8"),
        ("SALUD", "🛡️", "#24A8EC"),
        ("GUST", "✨", "#B750DD"),
        ("TRANSP", "🚍", "#F18B13"),
    ]
    for prefijo, icono, color in estilos:
        if prefijo in _clave(nombre):
            return icono, color
    paleta = ["#2863BD", "#17AB78", "#8238F4", "#E91687", "#08A8CB", "#F18B13"]
    return "◆", paleta[indice % len(paleta)]


def _pesos(valor):
    return "$ " + format(valor, ",.0f").replace(",", ".")


def aplicar_categorias_noche(fig):
    if not fig.data:
        return fig
    traza = fig.data[0]
    raices = [(n, etiqueta, valor) for n, etiqueta, padre, valor
              in zip(traza.ids, traza.labels, traza.parents, traza.values) if not padre]
    total = sum(valor for _, _, valor in raices)
    estilos = {n: _identidad(etiqueta, i) for i, (n, etiqueta, _) in enumerate(raices)}
    etiquetas, colores, textos, ayudas = [], [], [], []
    for n, etiqueta, padre, valor, ayuda in zip(
            traza.ids, traza.labels, traza.parents, traza.values, traza.customdata):
        icono, color = estilos[padre or n]
        nombre = escape(str(etiqueta))
        etiquetas.append((icono + " " if not padre else "") + nombre)
        colores.append(color)
        porcentaje = (valor / total * 100) if total else 0
        textos.append("<b>" + etiquetas[-1] + "</b><br>" + _pesos(valor)
                      + " · " + format(porcentaje, ".1f").replace(".", ",") + "%")
        ayuda = re.sub(r"\$([\d,]+)", lambda m: "$" + m[1].replace(",", "."), str(ayuda))
        ayuda = re.sub(r"([+-]?\d+)\.(\d+)%", r"\1,\2%", ayuda)
        ayudas.append(ayuda.replace("Gasto:", "💰 Gasto:")
                      .replace("Transacciones:", "🧾 Transacciones:"))
    traza.update(
        labels=etiquetas, text=textos, texttemplate="%{text}", customdata=ayudas,
        textfont=dict(color="#FFFFFF", size=14), textposition="top left",
        marker=dict(colors=colores, line=dict(color="#07111F", width=3)),
        tiling=dict(pad=5, packing="squarify"), sort=True,
        pathbar=dict(visible=True, thickness=27, textfont=dict(size=13)),
        root=dict(color="#111F33"),
        hoverlabel=dict(bgcolor="#111F33", bordercolor="#284562",
                        font=dict(size=13, color="#F8FAFC"), align="left"),
    )
    fig.update_layout(
        height=740, paper_bgcolor="#07111F", plot_bgcolor="#07111F",
        margin=dict(t=100, b=15, l=12, r=12), separators=",.",
        font=dict(family="Arial, sans-serif", color="#E2E8F0"),
        uniformtext=dict(minsize=10, mode="hide"),
        title=dict(text="<b>🗂️ Así se distribuye tu gasto</b>", x=0.025,
                   y=0.97, font=dict(size=19, color="#F8FAFC")),
        annotations=[dict(x=1, y=1.11, xref="paper", yref="paper", xanchor="right",
                          yanchor="middle", showarrow=False, align="right",
                          bgcolor="#111F33", bordercolor="#284562", borderwidth=1,
                          borderpad=10, text="💰 Gasto total filtrado<br><b>" + _pesos(total) + "</b>",
                          font=dict(size=15, color="#F8FAFC"))],
    )
    return fig
