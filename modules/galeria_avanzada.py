"""Galería de evaluación: se muestra únicamente en Análisis avanzado."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from modules.analisis_avanzado import (
    acabado, gastos_validos, grafico_swarm, datos_pareto, grafico_pareto,
    comparacion, matriz_mensual,
)


def titulo(numero,nombre,explicacion):
    st.markdown(f"### {numero}. {nombre}")
    st.write(explicacion)


def pintar(fig,nombre):
    st.plotly_chart(acabado(fig,nombre),use_container_width=True,key="galeria_"+nombre)


def construir_sankey(gastos):
    datos=gastos_validos(gastos)
    datos=datos.loc[datos.GASTOS_CANTIDAD.gt(0)].copy()
    if datos.empty:return None
    datos["GASTOS_SUBCATEGORIA"]=datos.get("GASTOS_SUBCATEGORIA",pd.Series("Sin subcategoría",index=datos.index)).fillna("Sin subcategoría").astype(str)
    tabla=datos.groupby(["GASTOS_CATEGORIA","GASTOS_SUBCATEGORIA"]).GASTOS_CANTIDAD.sum()
    categorias=datos.groupby("GASTOS_CATEGORIA").GASTOS_CANTIDAD.sum().sort_values(ascending=False)
    total=float(categorias.sum())
    etiquetas=["Gastos positivos"]
    colores=["#38BDF8"]
    origen=[];destino=[];valores=[];detalles=[];colores_enlaces=[]
    paleta=px.colors.qualitative.Set2
    for i,(categoria,monto) in enumerate(categorias.items()):
        color=paleta[i%len(paleta)];nodo=len(etiquetas)
        etiquetas.append(str(categoria));colores.append(color)
        origen.append(0);destino.append(nodo);valores.append(float(monto))
        detalles.append([monto/total*100,100.,str(categoria)])
        colores_enlaces.append(color)
        sub=tabla.loc[categoria].sort_values(ascending=False)
        ramas=[(str(nombre),float(valor)) for nombre,valor in sub.iloc[:6].items()]
        if len(sub)>6:ramas.append(("Otras subcategorías",float(sub.iloc[6:].sum())))
        for nombre,valor in ramas:
            hijo=len(etiquetas);etiquetas.append(nombre);colores.append(color)
            origen.append(nodo);destino.append(hijo);valores.append(valor)
            detalles.append([valor/total*100,valor/float(monto)*100,str(categoria)])
            colores_enlaces.append(color)
    figura=go.Figure(go.Sankey(arrangement="snap",
        node=dict(label=etiquetas,color=colores,pad=20,thickness=18,line=dict(color="#0F172A",width=1),
            hovertemplate="<b>🏷️ %{label}</b><br>💰 Flujo: $%{value:,.0f}<extra></extra>"),
        link=dict(source=origen,target=destino,value=valores,color=colores_enlaces,customdata=detalles,
            hovertemplate="<b>%{source.label} → %{target.label}</b><br>💰 $%{value:,.0f}<br>📊 Del gasto total: %{customdata[0]:.2f}%<br>📂 Dentro de %{customdata[2]}: %{customdata[1]:.2f}%<extra></extra>")))
    figura=acabado(figura,"Flujo del gasto · Total → categoría → subcategoría",max(650,min(1500,len(etiquetas)*23)))
    figura.update_layout(font=dict(size=12,color="#F8FAFC"),margin=dict(t=80,b=40,l=25,r=100))
    return figura


def mostrar_sankey(gastos, ingresos=None):
    from modules.sankey_financiero import mostrar_sankey_financiero
    mostrar_sankey_financiero(gastos, ingresos)


def mostrar_galeria(gastos,ingresos,trabajos,desde,hasta):
    datos=gastos_validos(gastos)
    positivos=datos.loc[datos.GASTOS_CANTIDAD.gt(0)].copy()
    categorias=positivos.groupby("GASTOS_CATEGORIA").GASTOS_CANTIDAD.sum().nlargest(10).index
    titulo(5,"Gastos individuales · Swarm","**Para qué sirve:** distinguir pagos habituales y excepcionalmente altos. La posición horizontal representa el monto y la vertical separa los puntos. Rojo marca importes sobre Q3 + 1,5 IQR: una señal para revisar, no un error confirmado.")
    fig,total,n=grafico_swarm(gastos)
    if fig is None:st.info("No hay pagos positivos.")
    else:
        st.plotly_chart(fig,use_container_width=True,key="galeria_swarm")
        st.caption(f"{n} de {total} pagos de las ocho categorías de mayor gasto positivo; máximo 800 puntos, seleccionados de forma repartida. Escala logarítmica; separación vertical sin significado financiero.")

    titulo(6,"Porcentaje acumulado de pagos · ECDF","**Para qué sirve:** responder qué porcentaje de compras está por debajo de un monto. La curva es escalonada y cuenta pagos, no dinero: un pago grande y uno pequeño pesan lo mismo.")
    if positivos.empty:st.info("No hay pagos positivos.")
    else:
        conteo=positivos.GASTOS_CANTIDAD.value_counts().sort_index()
        x=np.r_[0,conteo.index.to_numpy()];y=np.r_[0,conteo.cumsum().to_numpy()/conteo.sum()*100]
        fig=go.Figure(go.Scatter(x=x,y=y,line=dict(shape="hv",color="#00D99B",width=3),fill="tozeroy",
            hovertemplate="💰 Hasta $%{x:,.0f}<br>📊 %{y:.2f}% de pagos<extra></extra>"))
        fig.update_yaxes(range=[0,105],title="Pagos acumulados (%)");fig.update_xaxes(title="Monto (COP)",tickprefix="$",tickformat=",.0f")
        pintar(fig,"ECDF de gastos positivos")
        st.caption(f"Base: {len(positivos)} pagos. Se excluyen ceros y ajustes negativos; la curva no representa proporción del gasto total.")

    titulo(7,"Mediana y dispersión · Boxplot","**Para qué sirve:** comparar el tamaño típico de los pagos por categoría. La línea central es la mediana; la caja contiene el 50 % central. Los bigotes usan 1,5 IQR; los puntos fuera son atípicos estadísticos.")
    if positivos.empty:st.info("No hay pagos positivos.")
    else:
        fig=go.Figure()
        for categoria in categorias:
            grupo=positivos.loc[positivos.GASTOS_CATEGORIA.eq(categoria)]
            fig.add_trace(go.Box(x=grupo.GASTOS_CANTIDAD,name=categoria,orientation="h",boxpoints="outliers",quartilemethod="linear",marker_color="#38BDF8",showlegend=False))
        fig.update_xaxes(type="log",title="Monto por pago (COP) · escala logarítmica");fig.update_yaxes(autorange="reversed")
        pintar(fig,"Boxplot por categoría")
        st.caption("Diez categorías de mayor gasto positivo. Con pocos pagos, la caja no describe un patrón estable.")

    titulo(8,"Forma de la distribución · Violín","**Para qué sirve:** ver si una categoría tiene uno o varios montos habituales. El ancho representa densidad de pagos, no dinero gastado. Complementa la mediana del boxplot mostrando la forma de la distribución.")
    fig=go.Figure();incluidas=[]
    for categoria in categorias[:8]:
        valores=positivos.loc[positivos.GASTOS_CATEGORIA.eq(categoria),"GASTOS_CANTIDAD"]
        if len(valores)>=5 and valores.nunique()>1:
            incluidas.append(categoria)
            fig.add_trace(go.Violin(x=np.log10(valores),name=categoria,orientation="h",box_visible=True,
                meanline_visible=True,points=False,spanmode="hard",scalemode="width",showlegend=False,
                line_color="#A78BFA"))
    if not incluidas:st.info("Se necesitan al menos cinco pagos positivos y dos montos distintos por categoría.")
    else:
        valores=positivos.loc[positivos.GASTOS_CATEGORIA.isin(incluidas),"GASTOS_CANTIDAD"]
        potencias=np.arange(int(np.floor(np.log10(valores.min()))),int(np.ceil(np.log10(valores.max())))+1)
        fig.update_xaxes(title="Monto por pago (COP) · transformación log10",tickvals=potencias,ticktext=[f"${10.**p:,.0f}".replace(",",".") for p in potencias])
        fig.update_yaxes(autorange="reversed");pintar(fig,"Violín de tamaños de pago")
        st.caption("Distribución suavizada sobre log10(monto); solo categorías con datos suficientes. Todas tienen el mismo ancho máximo: el ancho no compara número de pagos. Los valores emergentes del violín están en log10, según el eje.")

    titulo(9,"Concentración del gasto · Pareto","**Para qué sirve:** identificar las categorías que explican la mayor parte del gasto. Barras: monto por categoría. Línea: porcentaje acumulado. El 80 % es una referencia para priorizar, no una ley que los datos deban cumplir.")
    tabla=datos_pareto(gastos)
    if tabla.empty:st.info("No hay categorías con gasto neto positivo.")
    else:st.plotly_chart(grafico_pareto(tabla),use_container_width=True,key="galeria_pareto")
    st.caption("Usa categorías con total neto positivo; excluye categorías cuyo total es cero o negativo. Esta copia está aquí para evaluar su utilidad.")

    titulo(10,"Ranking compacto · Lollipop","**Para qué sirve:** comparar las categorías de mayor gasto con menos peso visual que una barra. El punto marca el monto; el tallo permite medirlo desde cero.")
    ranking=datos_pareto(gastos).head(12).sort_values("Monto")
    if ranking.empty:st.info("No hay categorías con gasto neto positivo.")
    else:
        fig=go.Figure()
        for nombre,fila in ranking.iterrows():
            fig.add_trace(go.Scatter(x=[0,fila.Monto],y=[nombre,nombre],mode="lines",line=dict(color="#64748B",width=3),hoverinfo="skip",showlegend=False))
        fig.add_trace(go.Scatter(x=ranking.Monto,y=ranking.index,mode="markers",marker=dict(size=14,color=ranking.Monto,colorscale="Blues"),showlegend=False,
            hovertemplate="<b>🏷️ %{y}</b><br>💰 $%{x:,.0f}<extra></extra>"))
        fig.update_xaxes(title="Gasto neto positivo por categoría (COP)",tickprefix="$",tickformat=",.0f")
        pintar(fig,"Lollipop de categorías")

    titulo(11,"Qué explica el cambio · Cascada","**Para qué sirve:** conectar el gasto de un mes con el del otro sumando los aumentos y restando las reducciones por categoría. Usa los mismos meses del Dumbbell. Rojo aumenta gasto; verde lo reduce.")
    periodos=[str(p) for p in pd.period_range(pd.Timestamp(desde),pd.Timestamp(hasta),freq="M")]
    if len(periodos)<2:st.info("Selecciona al menos dos meses.")
    else:
        anterior=st.session_state.get("analisis_mes_base_v20",periodos[0]);actual=st.session_state.get("analisis_mes_actual_v20",periodos[-1])
        cambios=comparacion(gastos,anterior,actual)
        if cambios.empty:st.info("No hay gastos en los meses elegidos.")
        else:
            fig=go.Figure(go.Waterfall(x=[anterior]+cambios.index.tolist()+[actual],
                y=[cambios[anterior].sum()]+cambios.Cambio.tolist()+[0],measure=["absolute"]+["relative"]*len(cambios)+["total"],
                increasing=dict(marker=dict(color="#FF3030")),decreasing=dict(marker=dict(color="#00E676")),totals=dict(marker=dict(color="#38BDF8")),
                hovertemplate="<b>%{x}</b><br>💰 Valor o cambio: $%{y:,.0f}<extra></extra>"))
            fig.update_xaxes(tickangle=-30);fig.update_yaxes(tickprefix="$",tickformat=",.0f")
            pintar(fig,"Cascada del cambio mensual")
            st.caption("Incluye todas las categorías: el total final concilia con el segundo mes. Los meses parciales incluyen solo días seleccionados.")

    titulo(12,"Jerarquía del gasto · Sunburst","**Para qué sirve:** explorar del total a la categoría y luego a la subcategoría. El área de cada sector representa dinero; pulsa un sector para ampliar su rama.")
    if positivos.empty:st.info("No hay pagos positivos.")
    else:
        base=positivos.copy();base["GASTOS_SUBCATEGORIA"]=base.get("GASTOS_SUBCATEGORIA",pd.Series("Sin subcategoría",index=base.index)).fillna("Sin subcategoría")
        fig=px.sunburst(base,path=[px.Constant("Gastos positivos"),"GASTOS_CATEGORIA","GASTOS_SUBCATEGORIA"],values="GASTOS_CANTIDAD",color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(hovertemplate="<b>%{label}</b><br>💰 $%{value:,.0f}<br>📊 Parte de su rama: %{percentParent:.1%}<extra></extra>")
        pintar(fig,"Sunburst de categorías y subcategorías")
        st.caption("Usa pagos positivos, excluyendo ceros y ajustes negativos. El porcentaje emergente corresponde a la rama superior, no siempre al gasto total.")

    titulo(13,"Patrón semanal de pagos · Mapa día/hora","**Para qué sirve:** localizar en qué días y horas registras más pagos. El color mide número de movimientos, no monto. Puede reflejar cuándo registras los gastos, más que cuándo compras.")
    if datos.empty:st.info("No hay fechas válidas.")
    elif datos.GASTOS_FECHA.dt.hour.eq(0).all():st.info("Todas las fechas están a medianoche. Falta información horaria real para mostrar este mapa sin inventar un patrón.")
    else:
        conteos=pd.crosstab(datos.GASTOS_FECHA.dt.dayofweek,datos.GASTOS_FECHA.dt.hour).reindex(index=range(7),columns=range(24),fill_value=0)
        fig=go.Figure(go.Heatmap(z=conteos.to_numpy(),x=list(range(24)),y=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"],colorscale="Blues",
            hovertemplate="📅 %{y}, %{x}:00–%{x}:59<br>🧾 %{z:.0f} movimientos<extra></extra>"))
        fig.update_xaxes(title="Hora registrada");pintar(fig,"Frecuencia de registros por día y hora")
        st.caption("Incluye movimientos de importe cero y ajustes negativos. Si algunas filas no tienen hora y aparecen a las 00:00, esa columna puede estar sobrerrepresentada.")

    titulo(14,"Cambio del ritmo de gasto · Media móvil","**Para qué sirve:** suavizar los picos diarios para comparar el gasto de cada día con su promedio móvil de siete días. Sirve para detectar aumentos persistentes sin confundirlos con un pago aislado.")
    dias=pd.date_range(pd.Timestamp(desde).normalize(),pd.Timestamp(hasta).normalize(),freq="D")
    diario=datos.groupby(datos.GASTOS_FECHA.dt.normalize()).GASTOS_CANTIDAD.sum().reindex(dias,fill_value=0)
    if len(diario)<7:st.info("Selecciona al menos siete días para la media móvil.")
    else:
        movil=diario.rolling(7,min_periods=7).mean()
        fig=go.Figure(go.Bar(x=diario.index,y=diario,name="Gasto diario",marker_color="#334155",hovertemplate="📅 %{x|%d/%m/%Y}<br>💰 Gasto: $%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=movil.index,y=movil,name="Promedio móvil 7 días",line=dict(color="#FBBF24",width=3),hovertemplate="📅 %{x|%d/%m/%Y}<br>📊 Promedio diario de 7 días: $%{y:,.0f}<extra></extra>"))
        fig.update_yaxes(tickprefix="$",tickformat=",.0f");pintar(fig,"Ritmo diario y media móvil")
        st.caption("Incluye días sin movimientos como cero y ajustes negativos. La media comienza al completar siete días. No es un pronóstico.")

    titulo(15,"Resistencia financiera · Mapa de escenarios","**Para qué sirve:** explorar cuánto saldo quedaría si tus ingresos bajaran y tus gastos subieran. Los cambios son supuestos ajustables, no probabilidades ni predicciones.")
    mensual=matriz_mensual(gastos,ingresos,trabajos,desde,hasta)
    if "Ingresos" not in mensual or mensual.Ingresos.sum()<=0 or mensual.Gastos.sum()<0:
        st.info("Se necesitan ingresos positivos y gastos netos no negativos.");return
    ingreso=float(mensual.Ingresos.mean());gasto=float(mensual.Gastos.mean())
    c1,c2=st.columns(2)
    caida=c1.slider("Caída máxima de ingresos (%)",0,80,40,5,key="galeria_caida")
    subida=c2.slider("Aumento máximo de gastos (%)",0,80,40,5,key="galeria_subida")
    x=np.linspace(0,caida,9) if caida else np.array([0.]);y=np.linspace(0,subida,9) if subida else np.array([0.])
    saldo=ingreso*(1-x[None,:]/100)-gasto*(1+y[:,None]/100);limite=max(float(np.abs(saldo).max()),1)
    fig=go.Figure(go.Heatmap(x=x,y=y,z=saldo,zmin=-limite,zmax=limite,zmid=0,
        colorscale=[[0,"#FF3030"],[.5,"#172033"],[1,"#00D99B"]],colorbar=dict(title="Saldo COP"),
        hovertemplate="📉 Menos ingresos: %{x:.1f}%<br>📈 Más gastos: %{y:.1f}%<br>💰 Saldo: $%{z:,.0f}<extra></extra>"))
    fig.update_xaxes(title="Caída de ingresos (%)");fig.update_yaxes(title="Aumento de gastos (%)")
    pintar(fig,"Saldo mensual en escenarios")
    st.caption(f"Base filtrada: ingresos ${ingreso:,.0f}/mes; gastos ${gasto:,.0f}/mes; {len(mensual)} meses, incluidos ceros y meses parciales. Saldo = ingreso × (1 − caída) − gasto × (1 + aumento). Rojo: déficit; verde: superávit. No incorpora deuda nueva ni retiros de ahorro.")
