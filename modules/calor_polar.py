"""Calendario polar de gasto neto diario: un anillo por semana y celda por fecha."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go


def crear_calor_polar(gastos, desde, hasta):
    fechas = pd.date_range(pd.Timestamp(desde).normalize(), pd.Timestamp(hasta).normalize(), freq="D")
    datos = gastos.copy()
    datos["Fecha"] = pd.to_datetime(datos["GASTOS_FECHA"], errors="coerce").dt.normalize()
    datos["Monto"] = pd.to_numeric(datos["GASTOS_CANTIDAD"], errors="coerce")
    datos = datos.dropna(subset=["Fecha", "Monto"])
    grupos = datos.groupby("Fecha").Monto
    valores = grupos.sum().reindex(fechas, fill_value=0)
    conteos = grupos.size().reindex(fechas, fill_value=0)
    semanas_por_fecha = fechas - pd.to_timedelta(fechas.weekday, unit="D")
    semanas = semanas_por_fecha.unique()
    posicion = {semana: i + 1 for i, semana in enumerate(semanas)}
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    detalles = [[fecha.strftime("%d/%m/%Y"), dias[fecha.weekday()], int(n)]
                for fecha, n in zip(fechas, conteos)]
    promedio_diario = float(valores.mean()) if len(valores) else 0.0
    # El promedio incluye todos los días filtrados, también los de gasto cero.
    # Si es no positivo, cualquier gasto positivo supera la referencia.
    referencia = promedio_diario if promedio_diario > 0 else 1e-9
    limite = referencia * 2
    escala = [[0, "#16A34A"], [.25, "#84CC16"], [.5, "#FACC15"],
              [.75, "#FF7426"], [1, "#FF0033"]]
    fig = go.Figure(go.Barpolar(
        r=np.ones(len(fechas)), base=[posicion[semana] for semana in semanas_por_fecha],
        theta=fechas.weekday * 360 / 7, width=np.full(len(fechas), 360 / 7 * .94),
        customdata=detalles,
        marker=dict(color=valores.to_numpy(), colorscale=escala,
                    cmin=0, cmax=limite,
                    line=dict(color="#07111F", width=.7),
                    colorbar=dict(title="Gasto diario<br>Amarillo: promedio<br>Rojo: superior", tickmode="array",
                        tickvals=[0, referencia, limite],
                        ticktext=["$0", "Prom. $" + format(max(promedio_diario, 0), ",.0f").replace(",", "."),
                                  "≥ $" + format(max(promedio_diario, 0)*2, ",.0f").replace(",", ".")], thickness=12, orientation="v", x=1.02, y=.5, len=.80, xanchor="left", yanchor="middle")),
        # No usar r como importe: todas las fechas ocupan una celda comparable.
        text=valores.to_numpy(),
        hovertemplate="<b>📅 %{customdata[0]} · %{customdata[1]}</b><br>"
                      "💰 Gasto neto: <b>$%{text:,.0f}</b><br>"
                      "🧾 Movimientos: %{customdata[2]}<extra></extra>",
    ))
    columnas_fechas = 2 if len(semanas) > 24 else 1
    filas_fechas = max(1, int(np.ceil(len(semanas) / columnas_fechas)))
    paso_etiquetas = max(1, int(np.ceil(len(semanas) / 14)))
    indices_etiquetas = list(range(0, len(semanas), paso_etiquetas))
    if len(semanas) and len(semanas)-1 not in indices_etiquetas:
        indices_etiquetas.append(len(semanas)-1)
    fig.update_layout(
        height=max(640, 145 + filas_fechas * 39),
        paper_bgcolor="#07111F", plot_bgcolor="#07111F", separators=",.", showlegend=False,
        margin=dict(t=60, b=55, l=55, r=165), font=dict(color="#E2E8F0"),
        hoverlabel=dict(bgcolor="#111F33", bordercolor="#284562", font=dict(color="#F8FAFC")),
        polar=dict(bgcolor="#07111F", domain=dict(x=[0, .59 if columnas_fechas == 2 else .69], y=[.06, .97]),
            angularaxis=dict(rotation=90, direction="clockwise", tickmode="array",
                tickvals=[i * 360 / 7 for i in range(7)], ticktext=dias,
                tickfont=dict(size=12), gridcolor="#213C58", linecolor="#284562"),
            radialaxis=dict(range=[0, len(semanas) + 1.1], tickmode="array",
                tickvals=[i + 1.5 for i in indices_etiquetas],
                ticktext=[f"S{i+1:02d}" for i in indices_etiquetas],
                tickfont=dict(size=10, color="#B4C9D9"), angle=180,
                showline=False, showgrid=False, ticks="")),
        bargap=.08,
    )
    inicio_leyenda = .63 if columnas_fechas == 2 else .74
    for columna in range(columnas_fechas):
        fig.add_annotation(x=inicio_leyenda + columna*.195, y=1.02, xref="paper", yref="paper",
                           xanchor="left", showarrow=False, text="<b>SEMANA · FECHAS</b>",
                           font=dict(size=12, color="#F8FAFC"))
    for indice, semana in enumerate(semanas):
        primero = max(pd.Timestamp(semana), fechas[0])
        ultimo = min(pd.Timestamp(semana) + pd.Timedelta(days=6), fechas[-1])
        columna, fila = divmod(indice, filas_fechas)
        etiqueta = f"<b>S{indice+1:02d}</b> · {primero:%d/%m/%Y}<br>　　　 {ultimo:%d/%m/%Y}"
        fig.add_annotation(x=inicio_leyenda + columna*.195,
                           y=.96-fila*(.91/max(filas_fechas, 1)), xref="paper", yref="paper",
                           xanchor="left", yanchor="top", align="left", showarrow=False,
                           text=etiqueta, font=dict(size=11, color="#B4C9D9"))
    return fig
