"""Promedio por día de la semana, incluidos días sin movimientos."""
import pandas as pd
import plotly.graph_objects as go


def crear_perfil_semanal(gastos, desde, hasta):
    fechas = pd.date_range(pd.Timestamp(desde).normalize(), pd.Timestamp(hasta).normalize(), freq="D")
    datos = gastos.copy()
    datos["Fecha"] = pd.to_datetime(datos.GASTOS_FECHA, errors="coerce").dt.normalize()
    datos["Monto"] = pd.to_numeric(datos.GASTOS_CANTIDAD, errors="coerce")
    diario = datos.dropna(subset=["Fecha", "Monto"]).groupby("Fecha").Monto.sum().reindex(fechas, fill_value=0)
    grupos = diario.groupby(diario.index.weekday)
    media = grupos.mean().reindex(range(7))
    cuenta = grupos.size().reindex(range(7), fill_value=0)
    total = grupos.sum().reindex(range(7), fill_value=0)
    fig = go.Figure(go.Bar(
        x=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"], y=media,
        customdata=list(zip(total, cuenta)), marker=dict(color=["#38BDF8"]*5+["#A78BFA"]*2, cornerradius="25%"),
        text=media, texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False,
        hovertemplate="<b>📅 %{x}</b><br>💰 Promedio: <b>$%{y:,.0f}</b><br>🧾 Gasto neto acumulado: $%{customdata[0]:,.0f}<br>🗓️ Días incluidos: %{customdata[1]}<br>Promedio = gasto acumulado ÷ días incluidos<extra></extra>",
    ))
    fig.update_layout(height=440, paper_bgcolor="#07111F", plot_bgcolor="#111F33",
                      separators=",.", showlegend=False, margin=dict(t=55,b=50,l=65,r=25),
                      font=dict(color="#E2E8F0"), bargap=.38,
                      hoverlabel=dict(bgcolor="#111F33",bordercolor="#284562"))
    fig.update_yaxes(title="Gasto neto medio por día (COP)",tickprefix="$",tickformat=",.0f",gridcolor="rgba(148,163,184,.12)")
    fig.update_xaxes(showgrid=False)
    return fig
