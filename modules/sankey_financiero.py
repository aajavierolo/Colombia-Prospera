"""Sankey de fuentes, utilización de ingresos y destinos del gasto."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import html
import unicodedata
from modules.analisis_avanzado import gastos_validos, acabado

PALETA=["#168BFF","#9B6DFF","#00B985","#F5B731","#22B7C7","#F97367","#8496B0"]


def icono_flujo(nombre,fuente=False):
    texto=''.join(c for c in unicodedata.normalize('NFD',str(nombre).upper()) if unicodedata.category(c)!='Mn')
    reglas=[(('VIVIENDA','ARRIENDO','INMUEBLE'),'🏠'),(('ALIMENT','MERCADO'),'🛒'),
            (('TRANSP','CARRO','MOTO'),'🚗'),(('EDUC','UNIVERS','COLEG','SED','UNAL','ANDINA'),'🎓'),
            (('SALUD','MEDIC'),'💚'),(('GUST','RESTAUR','ENTRETEN'),'🎉'),
            (('AHOR','INVER','FONDO'),'🐷'),(('CREDIT','DEUDA'),'💳'),
            (('HIJO','FAMIL'),'👥'),(('SERVIC','INTERNET'),'💡'),(('IMPUEST',),'🧾')]
    for palabras,icono in reglas:
        if any(p in texto for p in palabras):return icono
    return '🏢' if fuente else '📦'


def tarjeta_flujo(destino,nombre,valor,color,icono,detalle=''):
    monto=f"${valor:,.0f}".replace(',','.')
    destino.markdown(
        f'<div style="border:1px solid {color}66;border-left:4px solid {color};'
        f'border-radius:13px;padding:11px 12px;margin:0 0 10px;'
        f'background:linear-gradient(120deg,{color}22,#0F172A);min-height:86px;box-sizing:border-box;">'
        f'<div style="display:flex;gap:8px;align-items:center;">'
        f'<span style="font-size:23px;line-height:1.2">{icono}</span>'
        f'<span style="color:#E2E8F0;font-size:12px;font-weight:650;overflow-wrap:anywhere">{html.escape(str(nombre))}</span></div>'
        f'<div style="color:{color};font-size:17px;font-weight:800;margin-top:5px;overflow-wrap:anywhere">{monto}</div>'
        f'<div style="color:#94A3B8;font-size:11px;margin-top:3px">{html.escape(detalle)}</div></div>',
        unsafe_allow_html=True,
    )


def preparar_flujos(gastos,ingresos):
    g=gastos_validos(gastos)
    g=g.loc[g.GASTOS_CANTIDAD.gt(0)]
    destinos=g.groupby("GASTOS_CATEGORIA").GASTOS_CANTIDAD.sum().sort_values(ascending=False)
    if ingresos is None or ingresos.empty:fuentes=pd.Series(dtype=float)
    else:
        i=ingresos.copy();i["Monto"]=pd.to_numeric(i.INGRESOS_CANTIDAD,errors="coerce")
        i=i.loc[i.Monto.gt(0)]
        i["Fuente"]=i.get("INGRESOS_FUENTE",pd.Series("Sin fuente",index=i.index)).fillna("Sin fuente").astype(str).str.strip().replace("","Sin fuente")
        fuentes=i.groupby("Fuente").Monto.sum().sort_values(ascending=False)
    return fuentes,destinos


def construir_diagrama(gastos,ingresos):
    fuentes,destinos=preparar_flujos(gastos,ingresos)
    total_i=float(fuentes.sum());total_g=float(destinos.sum())
    if max(total_i,total_g)<=0:return None
    disponible=max(total_i-total_g,0);deficit=max(total_g-total_i,0);base=max(total_i,total_g)
    labels=[];colors=[];xs=[];ys=[];custom=[]
    source=[];target=[];values=[];links=[];linkdata=[]
    dinero=lambda v:f"${v:,.0f}".replace(",",".")
    def nodo(nombre,valor,color,x,y,nota=""):
        k=len(labels);labels.append(f"{nombre}<br><b>{dinero(valor)}</b>");colors.append(color);xs.append(x);ys.append(y)
        custom.append([nombre,valor,nota]);return k
    def enlace(a,b,valor,color):
        if valor<=0:return
        source.append(a);target.append(b);values.append(valor);links.append(color)
        linkdata.append([valor/total_i*100 if total_i>0 else 0])
    central=nodo("📥 Ingresos totales",total_i,"#2863BD",.36,.45,"Ingresos positivos registrados en el período")
    salida=nodo("🛒 Gastos totales",total_g,"#F04464",.64,.36,"Pagos positivos registrados en el período")
    acumulado=0
    for j,(nombre,valor) in enumerate(fuentes.items()):
        y=.03+.90*(acumulado+valor/2)/base;acumulado+=valor
        k=nodo(icono_flujo(nombre,True)+' '+str(nombre),float(valor),PALETA[j%len(PALETA)],.015,y,"Fuente de ingreso registrada")
        enlace(k,central,float(valor),PALETA[j%len(PALETA)])
    enlace(central,salida,min(total_i,total_g),"rgba(240,68,100,.48)")
    if disponible>0:
        ahorro=nodo("🐷 Disponible",disponible,"#16B979",.64,.89,"Saldo de estos flujos; no equivale a ahorro realizado")
        enlace(central,ahorro,disponible,"rgba(22,185,121,.48)")
    if deficit>0:
        falta=nodo("⚠️ Déficit por financiar",deficit,"#F59E0B",.36,.92,"Diferencia sin fuente identificada; no es un ingreso registrado")
        enlace(falta,salida,deficit,"rgba(245,158,11,.55)")
    acumulado=0
    for j,(nombre,valor) in enumerate(destinos.items()):
        y=.03+.90*(acumulado+valor/2)/max(total_g,1);acumulado+=valor
        k=nodo(icono_flujo(nombre)+' '+str(nombre),float(valor),PALETA[j%len(PALETA)],.985,y,"Destino del gasto por categoría")
        enlace(salida,k,float(valor),PALETA[j%len(PALETA)])
    fig=go.Figure(go.Sankey(arrangement="snap",orientation="h",valueformat=",.0f",valuesuffix=" COP",
        node=dict(label=labels,color=colors,x=xs,y=ys,pad=22,thickness=22,customdata=custom,
            line=dict(color="rgba(255,255,255,.5)",width=.6),
            hovertemplate="<b>%{customdata[0]}</b><br>💰 $%{customdata[1]:,.0f}<br>%{customdata[2]}<extra></extra>"),
        link=dict(source=source,target=target,value=values,color=links,customdata=linkdata,
            hovertemplate="💰 Flujo: <b>$%{value:,.0f}</b><br>📊 Respecto a ingresos: %{customdata[0]:.2f}%<extra></extra>")))
    fig=acabado(fig,"Fuentes de ingreso → distribución del dinero → destinos del gasto",max(620,min(1600,110+max(len(fuentes),len(destinos))*57)))
    fig.update_layout(font=dict(size=12,color="#E2E8F0"),margin=dict(t=100,b=45,l=20,r=20))
    fig.add_annotation(x=0,y=1.12,xref="paper",yref="paper",text="FUENTES DE INGRESO",showarrow=False,xanchor="left",font=dict(size=12,color="#94A3B8"))
    fig.add_annotation(x=1,y=1.12,xref="paper",yref="paper",text="DESTINOS DEL GASTO",showarrow=False,xanchor="right",font=dict(size=12,color="#94A3B8"))
    return fig


def mostrar_sankey_financiero(gastos,ingresos):
    st.markdown("### 🌊 Flujo general de tu dinero")
    st.write("**Para qué sirve:** ver de dónde proviene el dinero, qué parte se gasta y en qué categorías termina. El ancho de cada conexión representa el monto; los niveles muestran el mismo dinero y no deben sumarse entre sí.")
    fuentes,destinos=preparar_flujos(gastos,ingresos)
    ingreso=float(fuentes.sum());gasto=float(destinos.sum());saldo=ingreso-gasto
    from modules.sankey_moderno import crear_sankey_html
    import streamlit.components.v1 as components
    contenido,altura=crear_sankey_html(gastos,ingresos)
    if not contenido:
        st.info("No hay ingresos ni gastos positivos para construir el flujo.")
    else:
        # La proporción del iframe sigue la del SVG incluso si la pantalla
        # supera los 1180 px de diseño. No depende del mensaje de redimensionado.
        st.markdown(
            f'<style>.st-key-sankey_resumen_completo_v20 iframe {{'
            f'width:100% !important;height:auto !important;'
            f'aspect-ratio:1180 / {altura};display:block;border:0;'
            f'max-height:none !important;}}</style>',
            unsafe_allow_html=True,
        )
        with st.container(key="sankey_resumen_completo_v20"):
            components.html(contenido,height=altura,scrolling=False)
    st.caption("Usa los movimientos positivos de los filtros activos; se excluyen devoluciones y ajustes negativos. Por eso puede diferir de los totales netos de otras secciones. Disponible es saldo de estos flujos, no ahorro confirmado. Déficit por financiar muestra una diferencia sin atribuirla a préstamos o ahorros. Las tarjetas están integradas al gráfico y sus posiciones quedan fijas para mantenerlas alineadas con los flujos.")
