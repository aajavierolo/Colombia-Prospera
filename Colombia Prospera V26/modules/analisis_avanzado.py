"""Análisis descriptivo con los mismos datos filtrados del panel."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def acabado(fig, titulo, altura=480):
    fig.update_layout(template="plotly_dark", title=titulo, height=altura,
        paper_bgcolor="#000000", plot_bgcolor="#000000", separators=",.",
        margin=dict(t=75,b=65,l=65,r=45),
        hoverlabel=dict(bgcolor="#0F172A",bordercolor="#38BDF8",align="left",font=dict(size=13)),
        legend=dict(orientation="h",y=1.12))
    return fig


def gastos_validos(gastos):
    df=gastos.copy()
    df["GASTOS_FECHA"]=pd.to_datetime(df["GASTOS_FECHA"],errors="coerce")
    df["GASTOS_CANTIDAD"]=pd.to_numeric(df["GASTOS_CANTIDAD"],errors="coerce")
    df=df.dropna(subset=["GASTOS_FECHA","GASTOS_CANTIDAD"])
    df["GASTOS_CATEGORIA"]=df["GASTOS_CATEGORIA"].fillna("Sin categoría").astype(str)
    df["Periodo"]=df["GASTOS_FECHA"].dt.to_period("M").astype(str)
    return df


def comparacion(gastos, anterior, actual):
    df=gastos_validos(gastos)
    tabla=df.loc[df.Periodo.isin([anterior,actual])].pivot_table(index="GASTOS_CATEGORIA",columns="Periodo",values="GASTOS_CANTIDAD",aggfunc="sum",fill_value=0)
    tabla=tabla.reindex(columns=[anterior,actual],fill_value=0)
    tabla["Cambio"]=tabla[actual]-tabla[anterior]
    return tabla.sort_values("Cambio",key=lambda x:x.abs(),ascending=False)


def grafico_dumbbell(tabla, anterior, actual):
    fig=go.Figure()
    for nombre,fila in tabla.iterrows():
        fig.add_trace(go.Scatter(x=[fila[anterior],fila[actual]],y=[nombre,nombre],mode="lines",
            line=dict(color="#FF3030" if fila.Cambio>0 else "#00E676",width=3),showlegend=False,hoverinfo="skip"))
    for periodo,color in [(anterior,"#38BDF8"),(actual,"#FBBF24")]:
        fig.add_trace(go.Scatter(x=tabla[periodo],y=tabla.index,mode="markers",name=periodo,
            marker=dict(size=12,color=color,line=dict(color="white",width=1)),customdata=tabla[[anterior,actual,"Cambio"]],
            hovertemplate="<b>🏷️ %{y}</b><br>📅 "+periodo+"<br>💰 Gasto: $%{x:,.0f}<br>🔄 Cambio entre períodos: $%{customdata[2]:+,.0f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed",automargin=True)
    fig.update_xaxes(title="Gasto registrado (COP)",tickprefix="$",tickformat=",.0f")
    return acabado(fig,"Comparación de períodos · Dumbbell",max(420,85+len(tabla)*40))


def grafico_slope(flujo, anterior, actual):
    seleccion=flujo.loc[flujo.Periodo.isin([anterior,actual])].set_index("Periodo").reindex([anterior,actual]).fillna(0)
    fig=go.Figure()
    for campo,color in [("Ingresos","#00E676"),("Gastos","#FF3030"),("Balance","#38BDF8")]:
        vals=seleccion[campo].to_numpy()
        fig.add_trace(go.Scatter(x=[anterior,actual],y=vals,mode="lines+markers",name=campo,
            line=dict(color=color,width=3),marker=dict(size=12),
            hovertemplate="<b>"+campo+"</b><br>📅 %{x}<br>💰 $%{y:,.0f}<extra></extra>"))
    fig.update_yaxes(tickprefix="$",tickformat=",.0f",title="Total mensual (COP)")
    fig.update_xaxes(type="category",categoryorder="array",categoryarray=[anterior,actual])
    return acabado(fig,"Cambio financiero entre dos meses · Slope Chart")


def matriz_mensual(gastos,ingresos,trabajos,desde,hasta):
    indices=pd.period_range(pd.Timestamp(desde),pd.Timestamp(hasta),freq="M")
    datos=pd.DataFrame(index=indices)
    g=gastos_validos(gastos)
    datos["Gastos"]=g.groupby(pd.to_datetime(g.GASTOS_FECHA).dt.to_period("M"))["GASTOS_CANTIDAD"].sum().reindex(indices,fill_value=0)
    if not ingresos.empty:
        i=ingresos.copy();i["Fecha"]=pd.to_datetime(i.INGRESOS_FECHA,errors="coerce")
        datos["Ingresos"]=i.groupby(i.Fecha.dt.to_period("M"))["INGRESOS_CANTIDAD"].sum().reindex(indices,fill_value=0)
    if not trabajos.empty and {"FECHA","HORAS"}.issubset(trabajos.columns):
        t=trabajos.copy();t["Fecha"]=pd.to_datetime(t.FECHA,errors="coerce")
        t["Horas"]=pd.to_numeric(t.HORAS,errors="coerce")
        datos["Horas trabajadas"]=t.groupby(t.Fecha.dt.to_period("M"))["Horas"].sum().reindex(indices,fill_value=0)
    return datos


def grafico_correlacion(datos):
    variables=datos.loc[:,datos.nunique()>1]
    if len(variables)<4 or len(variables.columns)<2:
        return None
    matriz=variables.corr(method="pearson",min_periods=4)
    texto=[[f"{v:.2f}".replace(".",",") if pd.notna(v) else "Sin datos" for v in fila] for fila in matriz.to_numpy()]
    fig=go.Figure(go.Heatmap(z=matriz.to_numpy(),x=matriz.columns,y=matriz.index,
        zmin=-1,zmax=1,zmid=0,colorscale=[[0,"#168BFF"],[.5,"#172033"],[1,"#FF3030"]],
        text=texto,texttemplate="%{text}",colorbar=dict(title="Pearson r"),
        hovertemplate="<b>🔗 %{y} / %{x}</b><br>Correlación: %{z:.2f}<br>Meses: "+str(len(datos))+"<extra></extra>"))
    return acabado(fig,"Relación entre variables mensuales")


def datos_pareto(gastos):
    df=gastos_validos(gastos)
    tabla=df.groupby("GASTOS_CATEGORIA")["GASTOS_CANTIDAD"].sum().sort_values(ascending=False)
    tabla=tabla[tabla>0].to_frame("Monto")
    tabla["Acumulado %"]=tabla.Monto.cumsum()/tabla.Monto.sum()*100 if not tabla.empty else 0
    return tabla


def grafico_pareto(tabla):
    total=float(tabla.Monto.sum())
    detalle=np.column_stack([
        tabla.Monto.to_numpy(),
        tabla.Monto.to_numpy()/total*100 if total>0 else np.zeros(len(tabla)),
        tabla["Acumulado %"].to_numpy(),
    ])
    tooltip=(
        "<b>🏷️ %{x}</b><br><br>"
        "💰 Gasto de la categoría: <b>$%{customdata[0]:,.0f}</b><br>"
        "📊 Participación de la categoría: <b>%{customdata[1]:.2f}%</b><br>"
        "📈 Porcentaje acumulado: <b>%{customdata[2]:.2f}%</b><br>"
        + f"🏦 Total analizado: ${total:,.0f}".replace(",", ".")+
        "<extra></extra>"
    )
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=tabla.index,y=tabla.Monto,name="Gasto",marker_color="#38BDF8",
        customdata=detalle,hovertemplate=tooltip),secondary_y=False)
    fig.add_trace(go.Scatter(x=tabla.index,y=tabla["Acumulado %"],mode="lines+markers",name="Acumulado",
        line=dict(color="#FBBF24",width=3),customdata=detalle,hovertemplate=tooltip),secondary_y=True)
    fig.add_hline(y=80,line_dash="dot",line_color="#FF3030",secondary_y=True)
    fig.update_yaxes(title_text="Gasto (COP)",tickprefix="$",tickformat=",.0f",secondary_y=False)
    fig.update_yaxes(title_text="Acumulado (%)",range=[0,105],secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    return acabado(fig,"Pareto · ¿Dónde se concentra el 80 % del gasto?",520)


def calcular_kde(valores):
    x=np.asarray(valores,dtype=float);x=x[np.isfinite(x)&(x>0)]
    if len(x)<5 or np.unique(x).size<2:return None
    # KDE sobre log(monto), con corrección del jacobiano al volver a pesos.
    log=np.log(x);dispersion=min(log.std(ddof=1),(np.percentile(log,75)-np.percentile(log,25))/1.34)
    if dispersion<=0:dispersion=log.std(ddof=1)
    h=max(.9*dispersion*len(x)**(-.2),.03)
    eje_log=np.linspace(log.min()-3*h,log.max()+3*h,300)
    densidad=np.zeros_like(eje_log)
    for bloque in np.array_split(log,max(1,int(np.ceil(len(log)/1000)))):
        densidad+=np.exp(-.5*((eje_log[:,None]-bloque[None,:])/h)**2).sum(axis=1)
    eje=np.exp(eje_log);densidad=densidad/(len(x)*h*np.sqrt(2*np.pi))/eje
    return eje,densidad


def grafico_swarm(gastos):
    datos=gastos_validos(gastos);datos=datos.loc[datos.GASTOS_CANTIDAD.gt(0)].copy()
    top=datos.groupby("GASTOS_CATEGORIA").GASTOS_CANTIDAD.sum().nlargest(8).index.tolist()
    datos=datos.loc[datos.GASTOS_CATEGORIA.isin(top)].sort_values(["GASTOS_FECHA","GASTOS_CANTIDAD"])
    total=len(datos)
    if total>800:datos=datos.iloc[np.linspace(0,total-1,800,dtype=int)].copy()
    if datos.empty:return None,total,0
    q1,q3=np.percentile(gastos_validos(gastos).loc[lambda d:d.GASTOS_CANTIDAD.gt(0),"GASTOS_CANTIDAD"],[25,75]);limite=q3+1.5*(q3-q1)
    xs=np.log10(datos.GASTOS_CANTIDAD.to_numpy());amplitud=max(xs.max()-xs.min(),1)
    posiciones=np.zeros(len(datos));ocupadas={}
    # Posiciones deterministas para separar marcadores vecinos en escala logarítmica.
    for k,(_,fila) in enumerate(datos.iterrows()):
        grupo=top.index(fila.GASTOS_CATEGORIA);vecinos=ocupadas.setdefault(grupo,[])
        candidatos=[0]+[v for j in range(1,9) for v in [j*.045,-j*.045]]
        pos=next((v for v in candidatos if all(abs(xs[k]-px)>amplitud*.012 or abs(v-py)>.043 for px,py in vecinos)),candidatos[-1])
        posiciones[k]=grupo+pos;vecinos.append((xs[k],pos))
    custom=[[str(fila.GASTOS_CATEGORIA),str(fila.GASTOS_FECHA.date()),str(fila.get("GASTOS_DESCRIPCION","")),"Atípico alto" if fila.GASTOS_CANTIDAD>limite else "Dentro del umbral"] for _,fila in datos.iterrows()]
    fig=go.Figure(go.Scatter(x=datos.GASTOS_CANTIDAD,y=posiciones,mode="markers",customdata=custom,
        marker=dict(size=7,opacity=.75,color=np.where(datos.GASTOS_CANTIDAD.gt(limite),"#FF3030","#38BDF8")),
        hovertemplate="<b>🏷️ %{customdata[0]}</b><br>📅 %{customdata[1]}<br>💰 $%{x:,.0f}<br>%{customdata[2]}<br>🔎 %{customdata[3]}<extra></extra>"))
    fig.update_yaxes(tickvals=list(range(len(top))),ticktext=top,autorange="reversed")
    fig.update_xaxes(type="log",title="Monto (COP) · escala logarítmica",tickprefix="$")
    return acabado(fig,"Gastos individuales y atípicos · Swarm",max(460,len(top)*65)),total,len(datos)


def mostrar_pareto(gastos):
    st.markdown("### 🎯 Pareto del gasto")
    st.caption("Por qué sirve: identifica las categorías que explican la mayor parte del gasto para priorizar qué revisar. La línea muestra el porcentaje acumulado; el 80 % es una referencia, no una regla que los datos deban cumplir.")
    tabla=datos_pareto(gastos)
    if tabla.empty:st.info("No hay categorías con gasto neto positivo para construir Pareto.");return
    st.plotly_chart(grafico_pareto(tabla),use_container_width=True,key="gastos_pareto_v20")
    cantidad=int((tabla["Acumulado %"]<80).sum()+1)
    st.caption(f"Las primeras {cantidad} categorías explican al menos el 80 % del gasto neto positivo. Categorías con total cero o negativo se excluyen de esta distribución.")


def mostrar_analisis(gastos,ingresos,trabajos,flujo,desde,hasta):
    st.markdown("## 🔬 Análisis avanzado")
    st.caption("Análisis descriptivo de los filtros activos. Los meses sin movimientos cuentan como cero; un mes parcial solo contiene sus días seleccionados. Cero significa ausencia de registros, no prueba de que no hubo actividad.")
    periodos=[str(p) for p in pd.period_range(pd.Timestamp(desde),pd.Timestamp(hasta),freq="M")]
    st.markdown("### 1. Comparación de períodos · Dumbbell")
    st.write("**Por qué sirve:** compara dos meses por categoría y permite ver simultáneamente el monto anterior, el actual y la distancia entre ambos. Rojo indica aumento del gasto; verde, reducción.")
    if len(periodos)<2:
        st.info("Selecciona al menos dos meses para las comparaciones Dumbbell y Slope.")
    else:
        c1,c2=st.columns(2)
        anterior=c1.selectbox("Mes de referencia",periodos,index=0,key="analisis_mes_base_v20")
        actual=c2.selectbox("Mes a comparar",[p for p in periodos if p!=anterior],index=len(periodos)-2,key="analisis_mes_actual_v20")
        tabla=comparacion(gastos,anterior,actual)
        if tabla.empty:st.info("No hay gastos en los dos meses elegidos.")
        else:
            st.plotly_chart(grafico_dumbbell(tabla.head(15),anterior,actual),use_container_width=True,key="analisis_dumbbell_v20")
            st.caption("Hasta 15 categorías con mayor cambio absoluto. Una categoría sin movimientos en uno de los meses se representa con cero.")
            with st.expander("Ver comparación completa",expanded=False):st.dataframe(tabla,use_container_width=True)
        st.markdown("### 2. Cambio financiero · Slope Chart")
        st.write("**Por qué sirve:** muestra si ingresos, gastos y balance mejoraron o empeoraron entre los mismos dos meses. Subir es favorable para ingresos y balance; bajar es favorable para gastos. Une los extremos: no describe los meses intermedios.")
        mensual=matriz_mensual(gastos,ingresos,trabajos,desde,hasta)
        mensual["Balance"]=mensual.get("Ingresos",0)-mensual.Gastos
        if "Ingresos" not in mensual:mensual["Ingresos"]=0
        mensual["Periodo"]=mensual.index.astype(str)
        st.plotly_chart(grafico_slope(mensual,anterior,actual),use_container_width=True,key="analisis_slope_v20")
    st.markdown("### 3. Relación entre variables · Matriz de correlación")
    st.write("**Por qué sirve:** explora si ingresos, gastos y horas trabajadas se mueven juntos mes a mes. Un valor cercano a +1 indica relación en el mismo sentido; cerca de −1, en sentidos opuestos; cerca de cero, poca relación lineal. Correlación no implica causalidad.")
    mensual=matriz_mensual(gastos,ingresos,trabajos,desde,hasta)
    fig=grafico_correlacion(mensual)
    if fig is None:st.info("Se requieren al menos cuatro meses y dos variables con variación. Las variables constantes se omiten.")
    else:
        st.plotly_chart(fig,use_container_width=True,key="analisis_correlacion_v20")
        st.caption(f"Base: {len(mensual)} meses. Con pocos meses, resultados inestables; los meses sin registros y los períodos parciales pueden distorsionar las relaciones. El balance se excluye porque se calcula directamente a partir de ingresos y gastos.")
    st.markdown("### 4. Distribución de montos · KDE")
    st.write("**Por qué sirve:** muestra dónde se concentran los tamaños de tus pagos, suavizando el histograma. Los picos indican montos frecuentes; la altura es densidad, no dinero gastado ni un porcentaje directo.")
    valores=gastos_validos(gastos).GASTOS_CANTIDAD
    resultado=calcular_kde(valores)
    if resultado is None:st.info("Se necesitan al menos cinco gastos positivos y dos montos distintos para estimar la distribución.")
    else:
        eje,densidad=resultado
        fig=go.Figure(go.Scatter(x=eje,y=densidad,mode="lines",fill="tozeroy",line=dict(color="#38BDF8",width=3),
            hovertemplate="💰 Monto: $%{x:,.0f}<br>📊 Densidad: %{y:.3e}<extra></extra>"))
        fig.update_xaxes(type="log",title="Monto del gasto (COP) · escala logarítmica")
        fig.update_yaxes(title="Densidad por peso")
        st.plotly_chart(acabado(fig,"Distribución suavizada de gastos positivos"),use_container_width=True,key="analisis_kde_v20")
        st.caption(f"Base: {int(valores.gt(0).sum())} pagos positivos. Se excluyen ceros, devoluciones y ajustes negativos. Estimación gaussiana sobre log(monto), reconvertida a densidad por peso; no pronostica gastos futuros.")
    from modules.galeria_avanzada import mostrar_galeria
    mostrar_galeria(gastos, ingresos, trabajos, desde, hasta)


def mostrar_swarm_gastos(gastos):
    st.markdown("#### Gastos atípicos · Swarm Plot")
    st.write("**Por qué sirve:** permite ver cada movimiento y descubrir pagos inusualmente altos que los totales mensuales ocultan. Rojo: monto superior a Q3 + 1,5 × rango intercuartílico de los gastos positivos filtrados. Es una señal para revisar, no un error confirmado.")
    fig,total,mostrados=grafico_swarm(gastos)
    if fig is None:st.info("No hay gastos positivos para mostrar.")
    else:
        # Cambia solamente la presentación de Gastos; la galería reutiliza
        # el constructor horizontal sin esta transformación.
        traza=fig.data[0]
        montos=list(traza.x)
        posiciones=list(traza.y)
        nombres=list(fig.layout.yaxis.ticktext)
        marcas=list(fig.layout.yaxis.tickvals)
        traza.x=posiciones
        traza.y=montos
        traza.hovertemplate="<b>🏷️ %{customdata[0]}</b><br>📅 %{customdata[1]}<br>💰 $%{y:,.0f}<br>%{customdata[2]}<br>🔎 %{customdata[3]}<extra></extra>"
        fig.layout.xaxis=go.layout.XAxis(
            title="Categoría",type="linear",tickmode="array",tickvals=marcas,
            ticktext=nombres,tickangle=-30,range=[-.5,len(nombres)-.5],automargin=True,
        )
        fig.layout.yaxis=go.layout.YAxis(
            title="Monto (COP) · escala logarítmica",type="log",tickprefix="$",automargin=True,
        )
        fig.update_layout(height=580,margin=dict(t=75,b=120,l=85,r=35))
        st.plotly_chart(fig,use_container_width=True,key="gastos_swarm_v20")
        st.caption(f"{mostrados} de {total} movimientos de las ocho categorías de mayor gasto positivo. Máximo 800 puntos repartidos por el historial. El monto se lee en el eje vertical logarítmico; la separación horizontal de los puntos evita superposiciones y no representa otra variable.")
