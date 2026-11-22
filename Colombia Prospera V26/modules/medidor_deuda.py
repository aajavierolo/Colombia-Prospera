"""Medidor semicircular de deuda con centro legible y referencia explícita."""
import numpy as np
import plotly.graph_objects as go


def crear_medidor_deuda(porcentaje, valido=True):
    fig=go.Figure()
    maximo=max(100,int(np.ceil(max(porcentaje,0)/10))*10)
    tramos=[(0,10,"#00D99B"),(10,30,"#38BDF8"),(30,40,"#F59E0B"),(40,maximo,"#FF526E")]
    color="#00D99B" if porcentaje<=10 else "#38BDF8" if porcentaje<=30 else "#F59E0B" if porcentaje<=40 else "#FF526E"
    def arco(inicio,fin,tono,grosor,opacidad=1,hover=None):
        angulos=np.linspace(np.pi*(1-inicio/maximo),np.pi*(1-fin/maximo),120)
        fig.add_trace(go.Scatter(x=np.cos(angulos),y=np.sin(angulos),mode="lines",
            line=dict(color=tono,width=grosor),opacity=opacidad,showlegend=False,
            hovertemplate=hover or None,hoverinfo=None if hover else "skip"))
    # Aro de fondo y bisel, en la misma paleta que el Sankey.
    arco(0,maximo,"#14263D",25)
    angulos_bisel=np.linspace(np.pi,0,160)
    fig.add_trace(go.Scatter(x=1.10*np.cos(angulos_bisel),y=1.10*np.sin(angulos_bisel),
        mode="lines",line=dict(color="#284562",width=2),showlegend=False,hoverinfo="skip"))
    for inicio,fin,tono in tramos:
        arco(inicio+.45,fin-.45,tono,18,.22,
             f"Referencia visual: {inicio:g}–{fin:g} %<extra></extra>")
    if valido:
        arco(0,min(porcentaje,maximo),color,26,.10)
        arco(0,min(porcentaje,maximo),color,12,1,
             f"💳 Ingresos destinados a deuda: {porcentaje:.2f} %".replace('.',',')+"<extra></extra>")
        angulo=np.pi*(1-min(porcentaje,maximo)/maximo)
        fig.add_trace(go.Scatter(x=[0,.83*np.cos(angulo)],y=[0,.83*np.sin(angulo)],mode="lines",
            line=dict(color="#CFE4F6",width=3),showlegend=False,hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",marker=dict(size=13,color="#07111F",
            line=dict(color=color,width=3)),showlegend=False,hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[np.cos(angulo)],y=[np.sin(angulo)],mode="markers",
            marker=dict(size=12,color=color,line=dict(color="#F8FAFC",width=2)),showlegend=False,hoverinfo="skip"))
        estado="Hasta el 10 %" if porcentaje<=10 else "Dentro de la referencia" if porcentaje<=30 else "Sobre la referencia" if porcentaje<=40 else "Compromiso elevado"
        valor=f"{porcentaje:.2f} %".replace('.',',')
    else:
        valor="Sin datos";estado="Faltan ingresos positivos";color="#94A3B8"
    referencia=np.pi*(1-30/maximo)
    fig.add_shape(type="line",x0=.89*np.cos(referencia),y0=.89*np.sin(referencia),
                  x1=1.09*np.cos(referencia),y1=1.09*np.sin(referencia),
                  line=dict(color="#F8FAFC",width=2))
    for x,y,texto,tamano,tono in [
        (0,-.28,valor,30,color),(0,-.52,estado,11,"#B4C9D9"),
        (-1.08,-.10,"0 %",10,"#94A3B8"),(1.08,-.10,f"{maximo} %",10,"#94A3B8"),
        (0,-.76,"Referencia: 30 %",11,"#94A3B8"),
    ]:
        fig.add_annotation(x=x,y=y,text=f"<b>{texto}</b>" if tamano>20 else texto,showarrow=False,
            xanchor="center",yanchor="middle",font=dict(size=tamano,color=tono))
    fig.add_shape(type="path",xref="paper",yref="paper",layer="below",
        path="M 0.06,0 L 0.94,0 Q 1,0 1,0.06 L 1,0.94 Q 1,1 0.94,1 L 0.06,1 Q 0,1 0,0.94 L 0,0.06 Q 0,0 0.06,0 Z",
        fillcolor="#07111F",line=dict(color="#213C58",width=1))
    fig.add_shape(type="path",layer="below",
        path="M -0.56,-0.43 L 0.56,-0.43 Q 0.64,-0.43 0.64,-0.35 L 0.64,-0.20 Q 0.64,-0.12 0.56,-0.12 L -0.56,-0.12 Q -0.64,-0.12 -0.64,-0.20 L -0.64,-0.35 Q -0.64,-0.43 -0.56,-0.43 Z",
        fillcolor="#111F33",line=dict(color="#284562",width=1))
    fig.update_layout(template="plotly_dark",height=360,separators=",.",
        paper_bgcolor="#07111F",plot_bgcolor="#07111F",showlegend=False,
        title=dict(text="💳 Ingresos destinados a deudas",x=.5,xanchor="center",font=dict(size=15,color="#E2E8F0")),
        margin=dict(t=60,b=15,l=15,r=15),
        hoverlabel=dict(bgcolor="#0F172A",bordercolor=color,font=dict(size=12,color="#F8FAFC")))
    fig.update_xaxes(visible=False,range=[-1.25,1.25],fixedrange=True)
    fig.update_yaxes(visible=False,range=[-.93,1.27],scaleanchor="x",scaleratio=1,fixedrange=True)
    return fig


def crear_medidor_ahorro(balance, ingresos):
    porcentaje=balance/ingresos*100 if ingresos else 0
    minimo=min(-100,int(np.floor(porcentaje/10))*10)
    maximo=max(100,int(np.ceil(porcentaje/10))*10)
    color="#FF526E" if porcentaje<0 else "#F59E0B" if porcentaje<20 else "#00D99B"
    fig=go.Figure()
    def angulo(valor):return np.pi*(1-(valor-minimo)/(maximo-minimo))
    for inicio,fin,tono in [(minimo,0,"#FF526E"),(0,20,"#F59E0B"),(20,maximo,"#00D99B")]:
        a=np.linspace(angulo(inicio+.5),angulo(fin-.5),100)
        fig.add_trace(go.Scatter(x=np.cos(a),y=np.sin(a),mode="lines",line=dict(color=tono,width=18),opacity=.25,
            showlegend=False,hovertemplate=f"Rango: {inicio:g} a {fin:g} %<extra></extra>"))
    bisel=np.linspace(np.pi,0,150)
    fig.add_trace(go.Scatter(x=1.1*np.cos(bisel),y=1.1*np.sin(bisel),mode="lines",line=dict(color="#284562",width=2),showlegend=False,hoverinfo="skip"))
    valido=ingresos>0
    if valido:
        a=np.linspace(angulo(min(0,porcentaje)),angulo(max(0,porcentaje)),120)
        detalle=(f"💰 Balance: ${balance:,.0f}<br>📥 Ingresos: ${ingresos:,.0f}<br>".replace(',','.')
                 + f"📊 Capacidad de ahorro: {porcentaje:.2f} %".replace('.',',')+"<br>Balance ÷ ingresos × 100<extra></extra>")
        for ancho,opacidad in [(26,.1),(12,1)]:
            fig.add_trace(go.Scatter(x=np.cos(a),y=np.sin(a),mode="lines",line=dict(color=color,width=ancho),
                opacity=opacidad,showlegend=False,hovertemplate=detalle))
        a=angulo(porcentaje)
        fig.add_trace(go.Scatter(x=[0,.83*np.cos(a)],y=[0,.83*np.sin(a)],mode="lines",line=dict(color="#CFE4F6",width=3),showlegend=False,hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[np.cos(a),0],y=[np.sin(a),0],mode="markers",marker=dict(size=[12,10],color=color,line=dict(color="#F8FAFC",width=2)),showlegend=False,hovertemplate=detalle))
    meta=angulo(20)
    fig.add_shape(type="line",x0=.89*np.cos(meta),y0=.89*np.sin(meta),x1=1.09*np.cos(meta),y1=1.09*np.sin(meta),line=dict(color="#F8FAFC",width=2))
    valor=f"{porcentaje:.2f} %".replace('.',',') if valido else "Sin datos"
    estado="Déficit" if porcentaje<0 else "Bajo la meta" if porcentaje<20 else "Meta alcanzada"
    if not valido:estado="Faltan ingresos positivos";color="#94A3B8"
    diferencia=f"{porcentaje-20:+.2f} puntos porcentuales frente al 20 %".replace('.',',') if valido else "Meta de referencia: 20 %"
    for x,y,texto,tamano,tono in [(0,-.28,valor,30,color),(0,-.52,estado,12,"#B4C9D9"),
        (-1.08,-.10,f"{minimo:g} %",10,"#94A3B8"),(1.08,-.10,f"{maximo:g} %",10,"#94A3B8"),
        (0,-.76,diferencia,10,"#94A3B8")]:
        fig.add_annotation(x=x,y=y,text=f"<b>{texto}</b>" if tamano>20 else texto,showarrow=False,xanchor="center",yanchor="middle",font=dict(size=tamano,color=tono))
    fig.add_shape(type="path",xref="paper",yref="paper",layer="below",
        path="M 0.06,0 L 0.94,0 Q 1,0 1,0.06 L 1,0.94 Q 1,1 0.94,1 L 0.06,1 Q 0,1 0,0.94 L 0,0.06 Q 0,0 0.06,0 Z",
        fillcolor="#07111F",line=dict(color="#213C58",width=1))
    fig.add_shape(type="path",layer="below",
        path="M -0.56,-0.43 L 0.56,-0.43 Q 0.64,-0.43 0.64,-0.35 L 0.64,-0.20 Q 0.64,-0.12 0.56,-0.12 L -0.56,-0.12 Q -0.64,-0.12 -0.64,-0.20 L -0.64,-0.35 Q -0.64,-0.43 -0.56,-0.43 Z",
        fillcolor="#111F33",line=dict(color="#284562",width=1))
    fig.update_layout(template="plotly_dark",height=360,separators=",.",paper_bgcolor="#07111F",plot_bgcolor="#07111F",showlegend=False,
        title=dict(text="🐷 Capacidad de ahorro / balance",x=.5,xanchor="center",font=dict(size=15,color="#E2E8F0")),
        margin=dict(t=60,b=15,l=15,r=15),hoverlabel=dict(bgcolor="#111F33",bordercolor=color,font=dict(size=12,color="#F8FAFC")))
    fig.update_xaxes(visible=False,range=[-1.25,1.25],fixedrange=True)
    fig.update_yaxes(visible=False,range=[-.93,1.27],scaleanchor="x",scaleratio=1,fixedrange=True)
    return fig
