"""Barras mensuales Altium Noche sin modificar las agregaciones del panel."""
import numpy as np
import plotly.graph_objects as go


def crear_ingresos_mensuales(tabla):
    valores = tabla["INGRESOS_CANTIDAD"].astype(float)
    total = float(valores.sum())
    partes = valores / total * 100 if total > 0 else valores * 0
    fig = go.Figure(go.Bar(
        x=tabla["MES"], y=valores, customdata=partes,
        marker=dict(color=valores, colorscale=[[0,"#2863BD"],[.5,"#38BDF8"],[1,"#00E5A0"]],
                    showscale=False, cornerradius="28%",
                    line=dict(color="rgba(125,211,252,.7)", width=1)),
        text=["$" + format(v, ",.0f").replace(",", ".") for v in valores],
        texttemplate="%{text}", textposition="outside", cliponaxis=False,
        textfont=dict(color="#F8FAFC", size=12),
        hovertemplate="<b>📅 %{x}</b><br>📥 Ingresos: <b>$%{y:,.0f}</b><br>"
                      + ("📊 Del ingreso neto del periodo: %{customdata:.1f}%" if total > 0 else "Sin ingreso neto positivo para calcular participación")
                      + "<extra></extra>",
    ))
    minimo = min(float(valores.min()), 0) if len(valores) else 0
    maximo = max(float(valores.max()), 0) if len(valores) else 0
    margen = max(maximo-minimo, 1)*.25
    fig.update_layout(
        height=540, paper_bgcolor="#07152E", plot_bgcolor="#0A1B34", separators=",.",
        margin=dict(t=100,b=70,l=65,r=25), showlegend=False, bargap=.42,
        title=dict(text="<b>INGRESOS MENSUALES</b><br><sup>EVOLUCIÓN DEL PERIODO FILTRADO</sup>",
                   x=.045,y=.96,font=dict(size=18,color="#F8FAFC")),
        font=dict(family="Arial, sans-serif",color="#B4C9D9"),
        hoverlabel=dict(bgcolor="#111F33",bordercolor="#38BDF8",align="left",font=dict(color="#F8FAFC",size=13)),
        xaxis=dict(title=None,type="category",categoryorder="array",categoryarray=tabla["MES"].tolist(),
                   showgrid=False,linecolor="#284562",tickfont=dict(size=12),automargin=True),
        yaxis=dict(title="Ingresos (COP)",tickprefix="$",tickformat=",.0f",nticks=6,
                   gridcolor="rgba(148,163,184,.12)",zerolinecolor="#64748B",automargin=True,
                   range=[minimo-margen if minimo<0 else 0,maximo+margen]),
    )
    return fig



def crear_ranking_y_tipos(fuentes, tipos):
    fuentes=fuentes.sort_values('INGRESOS_CANTIDAD',ascending=False).copy()
    tipos=tipos.copy()
    figuras=[]
    for es_ranking,tabla,campo,titulo in [
        (True,fuentes,'INGRESOS_FUENTE','RANKING DE FUENTES DE INGRESO'),
        (False,tipos,'TIPO_INGRESO','INGRESOS POR TIPO DE FUENTE')]:
        valores=tabla.INGRESOS_CANTIDAD.astype(float)
        total=float(valores.sum())
        porcentajes=valores/total*100 if total>0 else valores*0
        colores=valores if es_ranking else [
            {'Laborales':'#00E5A0','Residuales':'#38BDF8','Sin clasificar':'#A78BFA'}.get(str(c),'#A78BFA')
            for c in tabla[campo]
        ]
        marker=dict(color=colores,cornerradius='28%',line=dict(color='rgba(125,211,252,.55)',width=1))
        if es_ranking:marker.update(colorscale=[[0,'#2863BD'],[.5,'#38BDF8'],[1,'#00E5A0']],showscale=False)
        fig=go.Figure(go.Bar(
            x=valores if es_ranking else tabla[campo],
            y=tabla[campo] if es_ranking else valores,
            orientation='h' if es_ranking else 'v',marker=marker,customdata=porcentajes,
            text=['$'+format(v,',.0f').replace(',','.') for v in valores],
            texttemplate='%{text}',textposition='outside',cliponaxis=False,
            textfont=dict(color='#F8FAFC',size=11),
            hovertemplate=('<b>🏦 %{y}</b><br>📥 Ingreso: <b>$%{x:,.0f}</b>' if es_ranking else
                           '<b>🧭 %{x}</b><br>📥 Ingreso: <b>$%{y:,.0f}</b>')
                          + ('<br>📊 Del total: <b>%{customdata:.2f}%</b>' if total>0 else '<br>Sin total positivo para calcular participación')
                          + '<extra></extra>',
        ))
        altura=max(510,150+len(fuentes)*40)
        fig.update_layout(
            height=altura,paper_bgcolor='#07152E',plot_bgcolor='#0A1B34',separators=',.',
            margin=dict(t=90,b=65,l=135 if es_ranking else 65,r=85 if es_ranking else 30),
            title=dict(text='<b>'+titulo+'</b>',x=.04,y=.96,font=dict(size=16,color='#F8FAFC')),
            font=dict(family='Arial, sans-serif',color='#B4C9D9'),showlegend=False,bargap=.38,
            hoverlabel=dict(bgcolor='#111F33',bordercolor='#38BDF8',align='left',font=dict(color='#F8FAFC',size=13)),
        )
        eje_monto=fig.update_xaxes if es_ranking else fig.update_yaxes
        lo=min(float(valores.min()),0) if len(valores) else 0
        hi=max(float(valores.max()),0) if len(valores) else 0
        espacio=max(hi-lo,1)*.30
        eje_monto(title='Ingresos (COP)',tickprefix='$',tickformat=',.0f',nticks=5,
                  gridcolor='rgba(148,163,184,.12)',zerolinecolor='#64748B',automargin=True,
                  range=[lo-espacio if lo<0 else 0,hi+espacio])
        eje_nombre=fig.update_yaxes if es_ranking else fig.update_xaxes
        eje_nombre(title=None,type='category',categoryorder='array',categoryarray=tabla[campo].tolist(),
                   showgrid=False,automargin=True)
        if es_ranking:fig.update_yaxes(autorange='reversed')
        figuras.append(fig)
    return tuple(figuras)



def estilizar_mapa_ingresos(fig):
    import re
    from modules.sunburst_noche import _icono_blanco
    from html import escape
    if not fig.data:
        return fig
    tr=fig.data[0]
    paleta={'#00FF88':'#00BE85','#00B7FF':'#168BFF','#B026FF':'#9254E8','#111827':'#111F33'}
    textos=[]
    for nombre,padre in zip(tr.labels,tr.parents):
        es_tipo=str(padre)=='Ingresos'
        icono=_icono_blanco('💼' if str(nombre)=='Laborales' else '🏦')
        textos.append((icono+'<br>' if es_tipo else '')+'<b>'+escape(str(nombre).upper())+'</b>')
    ayudas=[]
    for texto in tr.customdata:
        texto=re.sub(r'\$([\d,]+)',lambda m:'$'+m[1].replace(',','.'),str(texto))
        texto=re.sub(r'(\d+)\.(\d+)%',r'\1,\2%',texto)
        ayudas.append(texto)
    fig.update_traces(
        text=textos,texttemplate='%{text}<br>$%{value:,.0f}<br>%{percentEntry:.1%}',
        customdata=ayudas,sort=True,tiling=dict(pad=5,packing='squarify'),
        textfont=dict(size=15,color='#F8FAFC',family='Arial, sans-serif'),
        marker=dict(colors=[paleta.get(c,c) for c in tr.marker.colors],line=dict(color='#07152E',width=3)),
        root=dict(color='#111F33'),pathbar=dict(visible=True,thickness=32,textfont=dict(size=13)),
        hoverlabel=dict(bgcolor='#111F33',bordercolor='#38BDF8',align='left',font=dict(size=13,color='#F8FAFC')),
    )
    fig.update_layout(
        height=620,paper_bgcolor='#07152E',plot_bgcolor='#07152E',separators=',.',
        margin=dict(t=90,b=18,l=14,r=14),font=dict(family='Arial, sans-serif',color='#E2E8F0'),
        title=dict(text='<b>MAPA DE INGRESOS</b><br><sup>TIPO DE FUENTE → FUENTE</sup>',x=.025,y=.97,
                   font=dict(size=19,color='#F8FAFC')),
        uniformtext=dict(minsize=9,mode='hide'),
    )
    return fig



def crear_mapa_fuentes_tarjetas(fig):
    from modules.categorias_tarjetas import crear_mapa_tarjetas
    if not fig.data:
        return "", 770
    tr=fig.data[0]
    raices={n for n,padre in zip(tr.ids,tr.parents) if not padre}
    nodos=[(n,nombre,"" if padre in raices else padre,valor,ayuda)
           for n,nombre,padre,valor,ayuda in zip(tr.ids,tr.labels,tr.parents,tr.values,tr.customdata)
           if n not in raices]
    if not nodos:
        return "",770
    ids,labels,parents,values,tips=zip(*nodos)
    mapa=go.Figure(go.Treemap(ids=ids,labels=labels,parents=parents,values=values,
                              customdata=tips,branchvalues="total"))
    return crear_mapa_tarjetas(mapa,ingresos=True)
