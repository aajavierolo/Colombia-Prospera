"""Adaptación de los indicadores patrimoniales al anillo moderno."""
import plotly.graph_objects as go


def preparar_indicador_patrimonio(original):
    fig=go.Figure(original)
    if not fig.data:
        return fig
    tr=fig.data[0]
    total=sum(tr.values)
    ayudas=[]
    for i,(nombre,valor) in enumerate(zip(tr.labels,tr.values)):
        ayuda=str(tr.hovertemplate or '')
        ayuda=ayuda.replace('%{label}',str(nombre))
        ayuda=ayuda.replace('%{value:,.0f}',format(valor,',.0f').replace(',','.'))
        ayuda=ayuda.replace('%{percent:.1%}',format(valor/total*100 if total else 0,'.1f').replace('.',',')+'%')
        if tr.customdata is not None:
            ayuda=ayuda.replace('%{customdata[0]}',str(tr.customdata[i][0]))
        ayuda=ayuda.replace('<extra></extra>','')
        ayudas.append(ayuda)
    tr.hovertext=ayudas
    return fig



def modernizar_monedas(original,titulo,colores_vivos=False):
    from html import escape
    import re
    fig=go.Figure(original)
    if not fig.data:return fig
    tr=fig.data[0]
    raiz=next((n for n,p in zip(tr.ids,tr.parents) if not p),None)
    total=next((v for n,v in zip(tr.ids,tr.values) if n==raiz),0)
    simbolos={'COP':'$','USD':'US$','EUR':'€','GBP':'£'}
    colores_moneda={'COP':'#00D9A6','USD':'#A78BFA','EUR':'#38BDF8','GBP':'#FBBF24'}
    if colores_vivos:
        colores_moneda={'COP':'#00FF88','USD':'#A855FF','EUR':'#00DFFF','GBP':'#FFE600'}
    monedas=[];textos=[];plantillas=[];colores=[]
    color_nodos={}
    for n,nombre,padre,valor in zip(tr.ids,tr.labels,tr.parents,tr.values):
        if n==raiz:
            textos.append('<b>'+escape(str(nombre).upper())+'</b><br>$'+format(valor,',.0f').replace(',','.')+'<br><sup>EQUIVALENTE COP</sup>')
            plantillas.append('%{text}');color='#10254A'
        elif padre==raiz:
            codigo=re.search(r'\(([A-Z]{3})\)',str(nombre))
            codigo=codigo[1] if codigo else str(nombre)
            color=colores_moneda.get(codigo,'#38BDF8')
            textos.append('<b>'+escape(simbolos.get(codigo,'◈'))+'<br>'+escape(codigo)+'</b>')
            plantillas.append('%{text}<br>%{percentEntry:.1%}')
            monedas.append((codigo,valor,color))
        else:
            color=color_nodos.get(padre,'#38BDF8')
            textos.append(escape(str(nombre)))
            plantillas.append('%{text}<br>%{percentEntry:.1%}')
        color_nodos[n]=color;colores.append(color)
    tr.update(text=textos,texttemplate=plantillas,sort=True,maxdepth=2,
              domain=dict(x=[0,.73],y=[.06,.98]),insidetextorientation='auto',
              textfont=dict(size=14,color='#F8FAFC',family='Arial, sans-serif'),
              marker=dict(colors=colores,line=dict(color='#07152E',width=2)),
              hoverlabel=dict(bgcolor='#111F33',bordercolor='#38BDF8',align='left',font=dict(size=13,color='#F8FAFC')))
    if colores_vivos:
        tr.update(leaf=dict(opacity=1), textfont=dict(color=['#07111F' if c in {'#00FF88','#00DFFF','#FFE600'} else '#F8FAFC' for c in colores]))
    fig.layout.annotations=()
    fig.update_layout(height=540,paper_bgcolor='#07152E',plot_bgcolor='#07152E',separators=',.',
                      margin=dict(t=85,b=25,l=15,r=20),font=dict(family='Arial, sans-serif',color='#E2E8F0'),
                      title=dict(text='<b>'+titulo+'</b>',x=.03,y=.97,font=dict(size=16,color='#F8FAFC')))
    for i,(codigo,valor,color) in enumerate(sorted(monedas,key=lambda t:t[1],reverse=True)):
        pct=valor/total*100 if total>0 else 0
        fig.add_annotation(x=.76,y=.84-i*.16,xref='paper',yref='paper',showarrow=False,
                           xanchor='left',yanchor='top',align='left',
                           text='<span style="color:'+color+'">●</span> <b>'+escape(codigo)+'</b><br>$'
                                +format(valor,',.0f').replace(',','.')+' COP<br>'
                                +format(pct,'.2f').replace('.',',')+'% DEL TOTAL',
                           font=dict(size=12,color='#E2E8F0'))
    return fig



def modernizar_mapa_patrimonio(original):
    from html import escape
    from modules.categorias_noche import _clave
    import re
    fig=go.Figure(original)
    if not fig.data:return fig
    tr=fig.data[0]
    nodos={n:(nombre,padre) for n,nombre,padre in zip(tr.ids,tr.labels,tr.parents)}
    raices={n for n,(_,padre) in nodos.items() if not padre}
    tipos={n for n,(_,padre) in nodos.items() if padre in raices}
    categorias=[n for n,(_,padre) in nodos.items() if padre in tipos]
    paleta=['#00A982','#168BCE','#7551D6','#0E94A4','#2588A4','#548DC4']
    colores_categorias={n:paleta[i%len(paleta)] for i,n in enumerate(categorias)}
    colores=[]
    for n,nombre,padre in zip(tr.ids,tr.labels,tr.parents):
        ruta=[];actual=n
        while actual in nodos:
            ruta.append(actual);actual=nodos[actual][1]
        pasivo=any(_clave(nodos[k][0])=='PASIVO' for k in ruta)
        categoria=next((k for k in ruta if k in colores_categorias),None)
        if n in raices:color='#111F33'
        elif n in tipos:color='#A62C50' if pasivo else '#176F75'
        elif pasivo:color='#CF365E'
        else:color=colores_categorias.get(categoria,'#168BCE')
        colores.append(color)
    ayudas=[]
    for tip in tr.customdata:
        tip=re.sub(r'\$(-?[\d,]+)',lambda m:'$'+m[1].replace(',','.'),str(tip))
        ayudas.append(re.sub(r'(\d+)\.(\d+)%',r'\1,\2%',tip))
    tr.update(labels=[str(n).upper() for n in tr.labels],customdata=ayudas,
              texttemplate='<b>%{label}</b><br>$%{text:,.0f}',
              textfont=dict(size=14,color='#FFFFFF',family='Arial, sans-serif'),
              sort=True,tiling=dict(pad=6,packing='squarify'),
              marker=dict(colors=colores,line=dict(color='#07152E',width=3)),
              root=dict(color='#111F33'),pathbar=dict(visible=True,thickness=34,textfont=dict(size=13)),
              hoverlabel=dict(bgcolor='#111F33',bordercolor='#38BDF8',align='left',font=dict(color='#F8FAFC',size=13)))
    fig.update_layout(height=730,paper_bgcolor='#07152E',plot_bgcolor='#07152E',separators=',.',
                      margin=dict(t=85,b=20,l=14,r=14),font=dict(family='Arial, sans-serif',color='#E2E8F0'),
                      title=dict(text='<b>MAPA DEL PATRIMONIO</b><br><sup>ACTIVOS Y PASIVOS · CATEGORÍA → ACTIVO</sup>',
                                 x=.025,y=.97,font=dict(size=19,color='#F8FAFC')),
                      uniformtext=dict(minsize=9,mode='hide'))
    return fig



def crear_tarjetas_patrimonio(original):
    from modules.categorias_tarjetas import crear_mapa_tarjetas
    if not original.data:return "",770
    tr=original.data[0]
    nodos={n:(nombre,padre,v,neto,tip) for n,nombre,padre,v,neto,tip in zip(tr.ids,tr.labels,tr.parents,tr.values,tr.text,tr.customdata)}
    raices={n for n,t in nodos.items() if not t[1]}
    tipos={n for n,t in nodos.items() if t[1] in raices}
    categorias=[n for n,t in nodos.items() if t[1] in tipos]
    padres_con_hijos={t[1] for t in nodos.values()}
    ids=[];labels=[];parents=[];values=[];tips=[];netos={}
    for cat in categorias:
        nombre,padre,valor,neto,tip=nodos[cat]
        ids.append(cat);labels.append(str(nodos[padre][0])+" · "+str(nombre));parents.append("");values.append(valor);tips.append(tip);netos[cat]=neto
    for n,(nombre,padre,valor,neto,tip) in nodos.items():
        if n in padres_con_hijos:continue
        actual=padre
        while actual in nodos and actual not in categorias:
            actual=nodos[actual][1]
        if actual not in categorias:continue
        ids.append(n);labels.append(nombre);parents.append(actual);values.append(valor);tips.append(tip);netos[n]=neto
    mapa=go.Figure(go.Treemap(ids=ids,labels=labels,parents=parents,values=values,customdata=tips))
    return crear_mapa_tarjetas(mapa,patrimonio=True,montos_netos=netos)
