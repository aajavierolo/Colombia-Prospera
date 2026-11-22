"""Vistas imprimibles del Resumen V22; reciben resultados ya calculados por la app."""
from io import BytesIO
import textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Polygon, PathPatch, FancyBboxPatch
from matplotlib.path import Path
from matplotlib.ticker import FuncFormatter, MaxNLocator

FONDO='#07111F'
TEXTO='#E2E8F0'
MUTED='#B4C9D9'
PALETA=['#A855F7','#00D9C5','#1685FF','#FF526E','#FFE600','#58D3FF','#B585FF','#55FF0A','#EC4899']

def pesos(v):
    return ('$ ' if v>=0 else '-$ ')+f'{abs(v):,.0f}'.replace(',','.')

def _guardar(fig):
    buff=BytesIO()
    fig.savefig(buff,format='png',dpi=190,facecolor=FONDO)
    plt.close(fig);buff.seek(0)
    return buff

def _panel(ax,titulo):
    ax.set_facecolor('#111F33')
    ax.set_title(titulo,color=TEXTO,fontsize=14,fontweight='bold',loc='left',pad=18)
    ax.tick_params(colors=MUTED,labelsize=9)
    ax.xaxis.label.set_color(MUTED);ax.yaxis.label.set_color(MUTED)
    for borde in ax.spines.values():borde.set_color('#284562')
    ax.grid(alpha=.09,color=MUTED);ax.set_axisbelow(True)

def _mensaje(ax,mensaje):
    ax.text(.5,.5,textwrap.fill(str(mensaje),48),transform=ax.transAxes,ha='center',va='center',color=MUTED,fontsize=11)
    ax.set_xticks([]);ax.set_yticks([])

def graficos_diario_mapa(datos):
    fig,(ax,mapa)=plt.subplots(1,2,figsize=(14,6),gridspec_kw={'width_ratios':[1.15,1]})
    fig.patch.set_facecolor(FONDO)
    fig.subplots_adjust(left=.095,right=.98,bottom=.19,top=.84,wspace=.30)
    _panel(ax,'Flujo de caja acumulado')
    diario=datos['diario']
    x=pd.to_datetime(diario['Fecha']);y=diario['Acumulado'].map(float).to_numpy()
    ax.plot(x,y,color='#C4A1FF',lw=2.1)
    ax.fill_between(x,y,0,color='#A855F7',alpha=.24)
    ax.axhline(0,color='#A78BFA',alpha=.45,lw=.8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:pesos(v)))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3,maxticks=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.set_xlabel('Fecha');ax.set_ylabel('COP')
    if len(x)==1:ax.set_xlim(x.iloc[0]-pd.Timedelta(days=1),x.iloc[0]+pd.Timedelta(days=1))
    else:ax.set_xlim(x.iloc[0],x.iloc[-1])
    ax.text(0,1.025,'Día a día · Acumulado: '+pesos(y[-1])+' COP',transform=ax.transAxes,color='#C4A1FF',fontsize=10)
    destacados=sorted(datos.get('eventos',[]),key=lambda e:e['importe'],reverse=True)[:3]
    por_fecha=diario.set_index('Fecha')['Acumulado']
    for evento in destacados:
        ax.scatter([evento['fecha']],[float(por_fecha.loc[evento['fecha']])],s=28,color='#55FF0A' if evento['tipo']=='Ingreso' else '#FF526E',edgecolor=FONDO,zorder=4)
    ax.text(0,-.22,'Parte de cero al inicio del filtro; no es el saldo bancario.',transform=ax.transAxes,color=MUTED,fontsize=9)
    _panel(mapa,'Mapa de gastos por categoría')
    mapa.axis('off')
    items=datos.get('mapa_items',[]);poligonos=datos.get('mapa_poligonos',[])
    if not items:
        _mensaje(mapa,datos.get('mapa_error','Sin categorías con gasto neto positivo.'))
    else:
        total=sum(float(v) for _,v in items)
        mapa.set_xlim(-.015,1.015);mapa.set_ylim(-.015,.565);mapa.set_aspect('equal')
        for i,((nombre,valor),vertices) in enumerate(zip(items,poligonos)):
            pol=np.asarray(vertices);color=PALETA[i%len(PALETA)]
            patch=Polygon(pol,closed=True,facecolor=color,edgecolor='#D7E6FA',linewidth=1.1,alpha=.65)
            mapa.add_patch(patch)
            cross=pol[:,0]*np.roll(pol[:,1],-1)-np.roll(pol[:,0],-1)*pol[:,1]
            area=cross.sum()/2
            centro=((pol+np.roll(pol,-1,axis=0))*cross[:,None]).sum(axis=0)/(6*area) if abs(area)>1e-12 else pol.mean(axis=0)
            radio=min(abs((b-a)[0]*(centro-a)[1]-(b-a)[1]*(centro-a)[0])/max(np.linalg.norm(b-a),1e-12) for a,b in zip(pol,np.roll(pol,-1,axis=0)))
            porcentaje=float(valor)/total*100
            etiqueta='\n'.join(textwrap.wrap(str(nombre).title(),14))+'\n'+pesos(valor)+'\n'+f'{porcentaje:.1f} %'.replace('.',',')
            if radio>.045:
                fuente=min(11,max(6,radio*85))
                texto=mapa.text(*centro,etiqueta,ha='center',va='center',fontsize=fuente,color='white',fontweight='bold',clip_on=True)
                # Ajuste con las métricas reales del texto; mantiene el bloque en la celda.
                fig.canvas.draw();bb=texto.get_window_extent(fig.canvas.get_renderer())
                xy=mapa.transData.transform(centro);rx=np.linalg.norm(mapa.transData.transform(centro+[radio*.86,0])-xy)
                escala=min(1,rx/max(np.hypot(bb.width/2,bb.height/2),1))
                texto.set_fontsize(fuente*escala)
            else:
                mapa.text(*centro,str(i+1),ha='center',va='center',fontsize=7,color='white',clip_on=True)
        mapa.set_xlim(-.015,1.015);mapa.set_ylim(-.015,.565);mapa.set_aspect('equal')
        tabla=datos['mapa_tabla'];neto=tabla['Gasto neto'].sum()
        mapa.text(.5,-.12,'Gasto neto del filtro: '+pesos(neto)+' COP',transform=mapa.transAxes,ha='center',color='#4ADDD2',fontsize=10,fontweight='bold')
    return _guardar(fig)

def graficos_momentum_escudos(datos):
    fig=plt.figure(figsize=(14,6.1),facecolor=FONDO)
    ax=fig.add_axes([.08,.22,.49,.61]);esc=fig.add_axes([.63,.12,.35,.73])
    _panel(ax,'Momentum de gastos')
    ax.set_title('',loc='left')
    fig.text(.08,.95,'Momentum de gastos',fontsize=14,color=TEXTO,weight='bold')
    tabla=datos.get('momentum_tabla')
    if tabla is None:
        _mensaje(ax,datos.get('momentum_error','Sin datos para comparar.'))
    else:
        comp=tabla.loc[tabla['Estado'].eq('Comparable')]
        if comp.empty:
            _mensaje(ax,'Sin base anterior positiva para calcular la variación.')
        else:
            x=comp['Gasto actual'].map(float).to_numpy();y=comp['Variación %'].astype(float).to_numpy();umbral=float(np.median(x))
            xmax=max(max(x)*1.3,umbral*1.8,1);xmin=-xmax*.12
            margen=max(12.,max(float(y.max()-y.min()),40)*.18)
            ymin=min(-30.,min(y)-margen);ymax=max(30.,max(y)+margen)
            for x0,x1,y0,y1,color in [(xmin,umbral,0,ymax,'#FFE600'),(umbral,xmax,0,ymax,'#FF1744'),(xmin,umbral,ymin,0,'#00F5A0'),(umbral,xmax,ymin,0,'#1685FF')]:
                ax.fill_between([x0,x1],y0,y1,color=color,alpha=.15,lw=0)
            colores=['#FFE600' if a<umbral and b>0 else '#FF1744' if a>=umbral and b>0 else '#00F5A0' if a<umbral else '#1685FF' for a,b in zip(x,y)]
            tamanos=np.maximum(x/max(max(x),1)*550,30)
            ax.scatter(x,y,s=tamanos*1.5,c=colores,alpha=.12,lw=0)
            ax.scatter(x,y,s=tamanos,c=colores,edgecolor='#D7E6FA',linewidth=.7,zorder=3)
            ax.axhline(0,color=MUTED,ls=':',lw=.9);ax.axvline(umbral,color=MUTED,ls=':',lw=.9)
            ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax)
            fig.canvas.draw()
            renderer=fig.canvas.get_renderer();ocupados=[]
            for nombre,a,b in zip(comp['Categoría'],x,y):
                for dx,dy,ha,va in [(6,15,'left','bottom'),(6,-17,'left','top'),(-6,15,'right','bottom'),(-6,-17,'right','top'),(0,35,'center','bottom'),(0,-36,'center','top')]:
                    etiqueta=ax.annotate(textwrap.fill(str(nombre).title(),15),(a,b),xytext=(dx,dy),textcoords='offset points',ha=ha,va=va,color=TEXTO,fontsize=8,clip_on=True)
                    caja=etiqueta.get_window_extent(renderer).expanded(1.08,1.15)
                    dentro=ax.bbox.contains(caja.x0,caja.y0) and ax.bbox.contains(caja.x1,caja.y1)
                    if dentro and not any(caja.overlaps(otra) for otra in ocupados):
                        ocupados.append(caja);break
                    etiqueta.remove()
                else:
                    etiqueta=ax.annotate(textwrap.fill(str(nombre).title(),15),(a,b),xytext=(8,25),textcoords='offset points',color=TEXTO,fontsize=7,clip_on=True)
                    ocupados.append(etiqueta.get_window_extent(renderer))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:('$ '+f'{v/1e6:.1f}'.replace('.',',')+' M') if abs(v)>=1e6 else pesos(v)))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:g} %'))
            ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(5))
            ax.set_xlabel('Gasto del período (COP)');ax.set_ylabel('Variación (%)')
            for texto,xx,yy,ha,va,color in [('Vigilar\nBajo gasto · aumenta',.02,.98,'left','top','#FFE600'),('Controlar\nAlto gasto · aumenta',.98,.98,'right','top','#FF526E'),('Oportunidad\nBajo gasto · no crece',.02,.02,'left','bottom','#00F5A0'),('Estable\nAlto gasto · no crece',.98,.02,'right','bottom','#38BDF8')]:
                ax.text(xx,yy,texto,transform=ax.transAxes,ha=ha,va=va,color=color,fontsize=9,bbox=dict(facecolor=FONDO,alpha=.8,edgecolor='none',pad=4))
        ma,mb,pa,pb=datos['momentum_fechas']
        fig.text(.08,.90,f'{ma:%d/%m/%Y}-{mb:%d/%m/%Y} vs. {pa:%d/%m/%Y}-{pb:%d/%m/%Y}',fontsize=9,color=MUTED)
        if datos.get('momentum_nota','').startswith('Sin historial'):
            fig.text(.08,.04,'Comparación por mitades del historial disponible dentro del filtro.',fontsize=9,color=MUTED)
    _panel(esc,'Escudo de estado');esc.set_title('',loc='left');fig.text(.63,.95,'Escudo de estado',fontsize=14,color=TEXTO,weight='bold');esc.axis('off');esc.set_xlim(0,3);esc.set_ylim(0,4)
    for i,r in enumerate(datos.get('escudos',[])):
        color='#55FF0A' if r['estado'] in ['DENTRO','META','SUPERADA'] else '#FF3131' if r['estado']=='EXCEDIDO' else '#FFE600' if r['estado']=='PENDIENTE' else '#94A3B8'
        centro=i+.5
        verts=[(centro,3.45),(i+.91,3.12),(i+.91,2.30),(centro,1.72),(i+.09,2.30),(i+.09,3.12),(centro,3.45)]
        esc.add_patch(Polygon(verts,facecolor=color,alpha=.17,edgecolor='none'))
        esc.add_patch(Polygon(verts,fill=False,edgecolor=color,lw=2))
        esc.text(centro,3.72,r['grupo'],color=TEXTO,fontsize=10,ha='center',weight='bold')
        valor=f"{r['porcentaje']:.1f} %".replace('.',',') if r['porcentaje'] is not None else 'Sin base'
        esc.text(centro,2.73,valor,color='white',fontsize=16,ha='center',weight='bold')
        objetivo=('≥ ' if r['grupo']=='Ahorro' else '≤ ')+str(r['objetivo'])+' %'
        esc.text(centro,2.38,objetivo,color=TEXTO,fontsize=11,ha='center')
        esc.add_patch(FancyBboxPatch((i+.06,.76),.88,.65,boxstyle='round,pad=0.02,rounding_size=0.08',facecolor=color,edgecolor=color,alpha=.25))
        esc.text(centro,1.16,r['estado'],ha='center',color=color,fontsize=9,weight='bold')
        delta=f"{r['diferencia']:+.1f} pp".replace('.',',') if r['diferencia'] is not None else 'Sin base'
        esc.text(centro,.90,delta,ha='center',color=TEXTO,fontsize=9)
        monto=pesos(r['monto']) if r['monto'] is not None else 'Sin dato'
        esc.text(centro,.4,monto,ha='center',color=TEXTO,fontsize=8,weight='bold')
    fig.text(.63,.90,f"{datos['desde']:%d/%m/%Y}-{datos['hasta']:%d/%m/%Y}",fontsize=9,color=MUTED)
    return _guardar(fig)
