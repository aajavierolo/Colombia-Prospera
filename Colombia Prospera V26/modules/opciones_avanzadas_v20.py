"""Vistas descriptivas adicionales sobre datos filtrados."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

AZUL, VERDE, ROJO, VIOLETA = "#38BDF8", "#00D99B", "#FF526E", "#A78BFA"


def construir_opciones(gastos, ingresos, desde, hasta):
    g = gastos.copy()
    g["GASTOS_FECHA"] = pd.to_datetime(g["GASTOS_FECHA"], errors="coerce").dt.normalize()
    g["GASTOS_CANTIDAD"] = pd.to_numeric(g["GASTOS_CANTIDAD"], errors="coerce")
    g = g.dropna(subset=["GASTOS_FECHA", "GASTOS_CANTIDAD"])
    g["Categoria"] = g["GASTOS_CATEGORIA"].fillna("Sin categoría").astype(str)
    g["Subcategoria"] = g.get("GASTOS_SUBCATEGORIA", pd.Series("Sin subcategoría", index=g.index)).fillna("Sin subcategoría").astype(str)
    g["Mes"] = g.GASTOS_FECHA.dt.to_period("M").astype(str)
    fechas = pd.date_range(pd.Timestamp(desde).normalize(), pd.Timestamp(hasta).normalize(), freq="D")
    if len(fechas) == 0:
        return []
    g = g[g.GASTOS_FECHA.between(fechas[0], fechas[-1])]
    positivos = g[g.GASTOS_CANTIDAD.gt(0)].copy()
    diario = g.groupby("GASTOS_FECHA").GASTOS_CANTIDAD.sum().reindex(fechas, fill_value=0)
    pagos = positivos.groupby("GASTOS_FECHA").GASTOS_CANTIDAD.sum().reindex(fechas, fill_value=0)
    conteo = positivos.groupby("GASTOS_FECHA").size().reindex(fechas, fill_value=0)
    entradas = pd.Series(0., index=fechas)
    if not ingresos.empty and {"INGRESOS_FECHA", "INGRESOS_CANTIDAD"}.issubset(ingresos.columns):
        i = ingresos.copy()
        i["Fecha"] = pd.to_datetime(i.INGRESOS_FECHA, errors="coerce").dt.normalize()
        i["Valor"] = pd.to_numeric(i.INGRESOS_CANTIDAD, errors="coerce")
        entradas = i.dropna(subset=["Fecha", "Valor"]).groupby("Fecha").Valor.sum().reindex(fechas, fill_value=0)
    periodos = pd.period_range(fechas[0], fechas[-1], freq="M").astype(str)
    tabla = positivos.pivot_table(index="Mes", columns="Categoria", values="GASTOS_CANTIDAD", aggfunc="sum", fill_value=0).reindex(periodos, fill_value=0)
    opciones = []
    def add(nombre, ayuda, fig):
        fig.update_layout(template="plotly_dark", paper_bgcolor="#07111F", plot_bgcolor="#111F33",
                          separators=",.", height=470, margin=dict(t=35,b=65,l=65,r=30),
                          font=dict(color="#E2E8F0"), hoverlabel=dict(bgcolor="#111F33", bordercolor="#284562"),
                          legend=dict(orientation="h", y=1.12))
        opciones.append((nombre, ayuda, fig))
    def linea(series, nombre="Valor", color=AZUL):
        return go.Scatter(x=series.index, y=series.values, name=nombre, mode="lines", line=dict(color=color,width=2.5),
                          hovertemplate="%{x}<br>"+nombre+": %{y:,.2f}<extra></extra>")
    def barras(x,y,color=AZUL):
        return go.Figure(go.Bar(x=x,y=y,marker=dict(color=color,cornerradius="20%")))

    cal = pd.DataFrame({"Fecha":fechas,"Gasto":diario.values})
    cal["Semana"] = ((cal.Fecha-fechas[0]+pd.Timedelta(days=fechas[0].weekday())).dt.days//7)
    cal["Dia"] = cal.Fecha.dt.weekday
    z=cal.pivot(index="Dia",columns="Semana",values="Gasto").reindex(range(7))
    add("Calendario diario del gasto", "Detecta días intensos y semanas tranquilas. Incluye días sin registros como cero; fuera del periodo queda vacío. Colores en COP netos.",
        go.Figure(go.Heatmap(z=z.values,x=z.columns,y=["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"],colorscale="Blues",colorbar=dict(title="COP"),hoverongaps=False)))

    f=go.Figure()
    for mes, serie in diario.groupby(diario.index.to_period("M")):
        f.add_trace(go.Scatter(x=serie.index.day,y=serie.cumsum(),mode="lines",name=str(mes)))
    f.update_xaxes(title="Día del mes");f.update_yaxes(title="COP acumulados")
    add("Carrera del gasto dentro del mes", "Compara a qué velocidad se acumula el gasto en cada mes. Los meses parciales solo muestran los días incluidos en tus filtros.", f)

    f=go.Figure()
    for mes, serie in pagos.groupby(pagos.index.to_period("M")):
        if serie.sum()>0:
            f.add_trace(go.Scatter(x=serie.index.day/serie.index.days_in_month*100,y=serie.cumsum()/serie.sum()*100,name=str(mes),mode="lines"))
    f.add_trace(go.Scatter(x=[0,100],y=[0,100],name="Ritmo uniforme",line=dict(dash="dot",color="#94A3B8")))
    f.update_xaxes(title="Día transcurrido del mes (%)");f.update_yaxes(title="Gasto positivo del periodo mensual (%)")
    add("Curva de anticipación del gasto", "Muestra si concentras pagos al inicio o al final del mes. La referencia diagonal es un reparto uniforme, no un presupuesto. En meses parciales el total es solo el observado.",f)

    perfil=diario.groupby(diario.index.day).mean()
    f=go.Figure(linea(perfil,"Promedio diario COP"));f.update_xaxes(title="Día del mes")
    add("Huella del día de pago", "Busca concentraciones habituales cerca de ciertos días del mes. Es un promedio descriptivo; no identifica automáticamente tu fecha de salario.",f)
    fin=diario.index.weekday>=5
    add("Fin de semana frente a días hábiles", "Compara gasto neto POR DÍA en cada grupo, incluyendo días sin gasto. Si un grupo no aparece en el filtro, queda sin valor.",barras(["Lunes a viernes","Sábado y domingo"],[diario[~fin].mean(),diario[fin].mean()],[AZUL,VIOLETA]))

    dias_activos=conteo[conteo.gt(0)].index
    gaps=pd.Series(dias_activos).diff().dt.days.dropna()
    f=go.Figure(go.Histogram(x=gaps,xbins=dict(size=1),marker_color=VIOLETA))
    f.update_xaxes(title="Días entre fechas con pagos positivos");f.update_yaxes(title="Intervalos observados")
    add("Tiempo entre días de compra", "Distribución de días entre fechas con pagos positivos. Varios pagos el mismo día cuentan como una fecha; requiere al menos dos días activos.",f)

    flujo=(entradas-diario).cumsum()
    f=go.Figure(linea(flujo,"Flujo acumulado COP",VERDE));f.add_hline(y=0,line_color="#64748B")
    add("Trayectoria diaria del flujo", "Acumula ingresos menos gastos netos desde cero al inicio del filtro. No es el saldo bancario: no incluye capital inicial ni movimientos fuera de los registros.",f)
    caida=flujo-flujo.cummax().clip(lower=0)
    f=go.Figure(linea(caida,"Caída desde máximo COP",ROJO));f.update_traces(fill="tozeroy")
    add("Caídas del flujo acumulado", "Distancia en COP frente al máximo acumulado anterior, incluyendo el inicio en cero. Ayuda a ubicar tensiones de caja; no mide pérdidas de inversión.",f)
    f=go.Figure(go.Scatter(x=entradas,y=diario,mode="markers",text=fechas.strftime("%d/%m/%Y"),marker=dict(color=VIOLETA,size=8),hovertemplate="%{text}<br>Ingresos: $%{x:,.0f}<br>Gastos: $%{y:,.0f}<extra></extra>"))
    f.update_xaxes(title="Ingresos diarios COP");f.update_yaxes(title="Gastos diarios netos COP")
    add("Cuadrante diario de caja", "Cada punto es un día del periodo. Distingue días financiados con ingresos del mismo día de días que consumen disponibilidad previa.",f)

    rachas=[];r=0
    for n in conteo:
        r=r+1 if n==0 else 0;rachas.append(r)
    f=go.Figure(linea(pd.Series(rachas,index=fechas),"Días seguidos sin pagos",VERDE))
    add("Rachas sin compras registradas", "Cuenta días consecutivos sin pagos positivos dentro del filtro. Un día sin registro no demuestra que no hayas gastado por otros medios.",f)
    f=go.Figure(linea(diario.rolling(14,min_periods=7).std(),"Desviación diaria 14 días COP",VIOLETA))
    add("Volatilidad móvil del gasto", "Desviación estándar de gastos diarios en ventanas de 14 días; se requieren siete observaciones. Valores altos señalan un gasto menos regular.",f)
    f=go.Figure(linea(diario,"Gasto diario COP"))
    if len(diario)>1:
        media=diario.mean();sd=diario.std()
        for y,color in [(media,VERDE),(media+3*sd,ROJO),(media-3*sd,ROJO)]:f.add_hline(y=y,line_dash="dot",line_color=color)
    add("Banda de revisión de gastos diarios", "Compara cada día con la media y media ± tres desviaciones del filtro. Es una señal descriptiva, no una prueba de fraude ni un intervalo predictivo.",f)
    roll=diario.rolling(14,min_periods=7)
    f=go.Figure(linea(roll.quantile(.25),"Percentil 25",AZUL))
    f.add_trace(linea(roll.quantile(.75),"Percentil 75",AZUL));f.data[-1].update(fill="tonexty",fillcolor="rgba(56,189,248,.16)")
    f.add_trace(linea(roll.median(),"Mediana",VERDE))
    add("Corredor del gasto habitual", "Mediana y percentiles 25–75 de gastos diarios en los últimos 14 días. La banda representa dispersión observada, no certeza sobre gastos futuros.",f)

    ranks=tabla.rank(axis=1,ascending=False,method="min").where(tabla.gt(0))
    f=go.Figure()
    for cat in tabla.sum().nlargest(10).index:f.add_trace(go.Scatter(x=ranks.index,y=ranks[cat],name=str(cat),mode="lines+markers"))
    f.update_yaxes(autorange="reversed",title="Puesto por gasto positivo");f.update_xaxes(type="category")
    add("Bump chart de prioridades", "Muestra cómo cambia el puesto de las diez categorías de mayor gasto global. Empates comparten puesto y una categoría sin pagos ese mes queda sin posición.",f)
    shares=tabla.div(tabla.sum(axis=1).replace(0,np.nan),axis=0)*100
    f=go.Figure()
    for cat in shares:f.add_trace(go.Scatter(x=shares.index,y=shares[cat],name=str(cat),stackgroup="mix",mode="lines"))
    f.update_yaxes(title="Participación del gasto positivo (%)")
    add("Paisaje del gasto mensual", "Áreas apiladas al 100 % que muestran cambios en la mezcla de categorías. Un mes sin gasto positivo queda sin composición; no significa presupuesto cero.",f)
    hhi=(shares.fillna(0).div(100)**2).sum(axis=1).where(tabla.sum(axis=1).gt(0))
    add("Índice de concentración mensual", "HHI de 0 a 1: cerca de 1 indica concentración en pocas categorías. Se calcula sobre pagos positivos; concentración no implica por sí sola un problema.",go.Figure(linea(hhi,"HHI",VIOLETA)))
    probs=shares.div(100);entropia=-(probs.where(probs.gt(0))*np.log(probs.where(probs.gt(0)))).sum(axis=1)
    efectivas=np.exp(entropia).where(tabla.sum(axis=1).gt(0))
    add("Número efectivo de categorías", "Exponencial de la entropía: cuántas categorías con igual peso darían una diversidad similar. Ayuda a distinguir repartir gasto de añadir categorías insignificantes.",go.Figure(linea(efectivas,"Categorías equivalentes",VERDE)))
    conjuntos={m:set(zip(t.Categoria,t.Subcategoria)) for m,t in positivos.groupby("Mes")}
    similitud=[]
    for ant,act in zip(periodos[:-1],periodos[1:]):
        a,b=conjuntos.get(ant,set()),conjuntos.get(act,set());union=a|b
        similitud.append(len(a&b)/len(union)*100 if union else np.nan)
    add("Persistencia de tus subcategorías", "Índice Jaccard entre meses consecutivos: porcentaje de pares categoría/subcategoría compartidos respecto a la unión. Describe continuidad de uso, no obligaciones recurrentes confirmadas.",barras(periodos[1:],similitud))

    f=go.Figure()
    if len(periodos)>=2:
        a=positivos[positivos.Mes.eq(periodos[0])].GASTOS_CANTIDAD;b=positivos[positivos.Mes.eq(periodos[-1])].GASTOS_CANTIDAD
        if len(a) and len(b):
            frecuencia=(len(b)-len(a))*(a.mean()+b.mean())/2
            ticket=(b.mean()-a.mean())*(len(a)+len(b))/2
            f.add_trace(go.Waterfall(x=[str(periodos[0]),"Efecto frecuencia","Efecto monto medio",str(periodos[-1])],measure=["absolute","relative","relative","total"],y=[a.sum(),frecuencia,ticket,0],increasing=dict(marker=dict(color=ROJO)),decreasing=dict(marker=dict(color=VERDE))))
    add("Puente de frecuencia y monto medio", "Descompone exactamente el cambio de gasto positivo entre primer y último mes: número de pagos y monto medio, con reparto simétrico del efecto conjunto. Requiere pagos en ambos meses; periodos parciales no se ajustan.",f)
    resumen=positivos.groupby("Categoria").GASTOS_CANTIDAD.agg(["mean","median","count"])
    f=go.Figure(go.Scatter(x=resumen['median'],y=resumen['mean'],text=resumen.index,mode="markers+text",textposition="top center",marker=dict(size=12,color=VIOLETA)))
    f.update_xaxes(title="Mediana del pago COP");f.update_yaxes(title="Media del pago COP")
    add("Media frente a mediana del pago", "Categorías muy por encima de la diagonal implícita media=mediana pueden estar influidas por pagos grandes. Ambas medidas usan solo pagos positivos.",f)
    coberturas=[]
    for _,row in tabla.iterrows():
        vals=row[row.gt(0)].sort_values(ascending=False)
        coberturas.append(int((vals.cumsum()/vals.sum()<.8).sum()+1) if len(vals) else np.nan)
    add("Categorías que explican el 80 %", "Número mínimo de categorías necesario para alcanzar al menos el 80 % del gasto positivo de cada mes. Un valor pequeño indica alta concentración.",barras(tabla.index,coberturas))
    vals=np.sort(positivos.GASTOS_CANTIDAD.to_numpy());f=go.Figure()
    if len(vals):f.add_trace(go.Scatter(x=np.r_[0,np.arange(1,len(vals)+1)/len(vals)*100],y=np.r_[0,vals.cumsum()/vals.sum()*100],name="Pagos ordenados",fill="tozeroy",line=dict(color=VIOLETA)))
    f.add_trace(go.Scatter(x=[0,100],y=[0,100],name="Reparto igual",line=dict(dash="dot",color="#94A3B8")))
    f.update_xaxes(title="Pagos acumulados de menor a mayor (%)");f.update_yaxes(title="Dinero acumulado (%)")
    add("Curva de Lorenz de tus pagos", "Mide cuánto del dinero está concentrado en unos pocos pagos grandes. Ordena TODOS los pagos positivos por monto, sin agruparlos por categoría.",f)
    semanal=cal.assign(Mes=cal.Fecha.dt.to_period("M").astype(str),Tramo=((cal.Fecha.dt.day-1)//7+1))
    z=semanal.pivot_table(index="Mes",columns="Tramo",values="Gasto",aggfunc="mean").reindex(columns=range(1,6))
    add("Ritmo por tramos del mes", "Mapa del gasto diario medio en días 1–7, 8–14, 15–21, 22–28 y 29–31. Promedia días observados, incluidos ceros; el último tramo suele contener menos días.",go.Figure(go.Heatmap(z=z.values,x=["1–7","8–14","15–21","22–28","29–31"],y=z.index,colorscale="Blues",hoverongaps=False,colorbar=dict(title="COP/día"))))
    bruto=positivos.groupby("Mes").GASTOS_CANTIDAD.sum().reindex(periodos,fill_value=0)
    ajustes=g[g.GASTOS_CANTIDAD.lt(0)].groupby("Mes").GASTOS_CANTIDAD.sum().reindex(periodos,fill_value=0)
    f=go.Figure(go.Bar(x=periodos,y=bruto,name="Pagos positivos",marker_color=AZUL))
    f.add_trace(go.Bar(x=periodos,y=ajustes,name="Ajustes negativos",marker_color=VERDE))
    f.add_trace(go.Scatter(x=periodos,y=bruto+ajustes,name="Gasto neto",mode="lines+markers",line=dict(color=VIOLETA)))
    f.update_layout(barmode="relative")
    add("Pagos, ajustes y gasto neto", "Separa pagos positivos y movimientos negativos, y reconcilia su suma con el gasto neto. Un valor negativo se etiqueta como ajuste: no se asume que siempre sea una devolución.",f)
    return opciones


def mostrar_opciones(gastos, ingresos, desde, hasta):
    st.markdown("## 🔬 Análisis avanzado · 24 opciones")
    st.write("Explora otras maneras de leer tus gastos y tu flujo. Todas usan los filtros actuales. Las vistas de compras usan importes positivos; las de caja incluyen ajustes. No son proyecciones.")
    opciones=construir_opciones(gastos, ingresos, desde, hasta)
    if not opciones:
        st.info("Selecciona un periodo válido para explorar las opciones.")
        return
    for numero, (nombre, ayuda, fig) in enumerate(opciones, 1):
        st.markdown(f"### {numero}. {nombre}")
        st.write(ayuda)
        if not fig.data:
            st.info("Este gráfico necesita más datos en el periodo seleccionado.")
        else:
            st.plotly_chart(fig, use_container_width=True,
                            key=f"opcion_avanzada_fig_v20_{numero}",
                            config={"displaylogo": False})
        if numero < len(opciones):
            st.divider()
