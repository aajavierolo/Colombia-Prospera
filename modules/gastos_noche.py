"""Barras mensuales por naturaleza del gasto con estilo Altium Noche."""
import plotly.graph_objects as go


def modernizar_gastos_tipo(original, tabla):
    fig = go.Figure(original)
    colores = {"Fijo":"#38BDF8", "Variable":"#FF526E",
               "Extraordinario":"#FACC15", "Prescindible":"#A78BFA"}
    totales = tabla.groupby("MES")["GASTOS_CANTIDAD"].sum()
    def compacto(valor):
        if abs(valor) >= 1e6:
            return "$" + format(valor/1e6, ".2f").replace(".", ",") + " M"
        if abs(valor) >= 1000:
            return "$" + format(valor/1000, ".0f").replace(".", ",") + " mil"
        return "$" + format(valor, ",.0f").replace(",", ".")
    for tr in fig.data:
        tr.update(
            marker=dict(color=colores.get(tr.name,"#38BDF8"), cornerradius="25%",
                        line=dict(color="rgba(226,232,240,.30)",width=1)),
            text=[compacto(v) for v in tr.y],texttemplate="%{text}",
            textfont=dict(size=10,color="#F8FAFC"),textposition="outside",cliponaxis=False,
            customdata=[[float(totales.get(m,0))] for m in tr.x],
            hovertemplate="<b>📅 %{x} · %{fullData.name}</b><br>💰 Gasto: <b>$%{y:,.0f}</b>"
                          "<br>🧾 Total neto del mes: $%{customdata[0]:,.0f}<extra></extra>",
        )
    montos = tabla["GASTOS_CANTIDAD"]
    minimo = min(float(montos.min()),0) if len(montos) else 0
    maximo = max(float(montos.max()),0) if len(montos) else 0
    espacio = max(maximo-minimo,1)*.23
    fig.update_layout(
        height=540,paper_bgcolor="#07152E",plot_bgcolor="#0A1B34",separators=",.",
        title=dict(text="<b>GASTOS POR TIPO</b><br><sup>COMPARACIÓN MENSUAL</sup>",x=.04,y=.97,
                   font=dict(size=18,color="#F8FAFC")),
        font=dict(family="Arial, sans-serif",color="#B4C9D9"),
        margin=dict(t=115,b=65,l=75,r=30),barmode="group",bargap=.28,bargroupgap=.10,
        legend=dict(orientation="h",x=0,y=1.02,yanchor="bottom",title_text="",font=dict(size=11)),
        hoverlabel=dict(bgcolor="#111F33",bordercolor="#38BDF8",align="left",font=dict(size=13,color="#F8FAFC")),
    )
    fig.update_xaxes(title=None,showgrid=False,automargin=True)
    fig.update_yaxes(title="Gasto (COP)",tickprefix="$",tickformat=",.0f",nticks=6,automargin=True,
                     gridcolor="rgba(148,163,184,.12)",zerolinecolor="#64748B",
                     range=[minimo-espacio if minimo<0 else 0,maximo+espacio])
    return fig
