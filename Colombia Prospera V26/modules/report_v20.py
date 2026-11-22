"""Gráficos imprimibles Altium Noche; no requiere navegador ni dependencias nuevas."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path
from matplotlib.ticker import FuncFormatter
import textwrap
from modules.analisis_avanzado import gastos_validos, comparacion, matriz_mensual, calcular_kde, datos_pareto, grafico_swarm
from modules.sankey_financiero import preparar_flujos, PALETA

FONDO='#07111F'
AZUL='#38BDF8'
VERDE='#00D99B'
ROJO='#FF526E'
VIOLETA='#A78BFA'
AMBAR='#F59E0B'


def dinero(v):return f'${v:,.0f}'.replace(',','.')


def figura(titulo):
    fig,ax=plt.subplots(figsize=(11.2,5.4))
    fig.patch.set_facecolor(FONDO);ax.set_facecolor(FONDO)
    ax.set_title(titulo,fontsize=12,pad=18,color='#E2E8F0',fontweight='bold')
    ax.tick_params(labelsize=8,colors='#B4C9D9')
    ax.grid(alpha=.12,color='#94A3B8');ax.set_axisbelow(True)
    for borde in ax.spines.values():borde.set_color('#284562')
    ax.xaxis.label.set_color('#B4C9D9');ax.yaxis.label.set_color('#B4C9D9')
    fig.subplots_adjust(left=.16,right=.95,top=.86,bottom=.2)
    return fig,ax


def resumen_noche(gastos,ingreso,balance):
    from modules.core import agregar_tipo_gasto, normalizar
    tipos=agregar_tipo_gasto(gastos)
    fijos=float(tipos.loc[tipos.TIPO_GASTO.eq('Fijo'),'GASTOS_CANTIDAD'].sum())
    variables=float(tipos.loc[tipos.TIPO_GASTO.eq('Variable'),'GASTOS_CANTIDAD'].sum())
    textos=pd.Series('',index=gastos.index)
    for col in ['GASTOS_CATEGORIA','GASTOS_SUBCATEGORIA','GASTOS_SUBCATEGORIA_2','GASTOS_DESCRIPCION']:
        textos += ' '+gastos.get(col,pd.Series('',index=gastos.index)).astype(str).map(normalizar)
    pagos=float(gastos.loc[textos.str.contains('DEUDA|CREDITO|PRESTAMO|CUOTA|HIPOTECA|TARJETA|LIBRANZA',regex=True),'GASTOS_CANTIDAD'].sum())
    fig,cuadricula=plt.subplots(2,2,figsize=(11.2,6.8))
    axes=cuadricula.ravel()
    for ax in axes:ax.set_facecolor(FONDO)
    if fijos>=0 and variables>=0 and fijos+variables>0:
        axes[0].pie([fijos,variables],colors=[AZUL,VIOLETA],startangle=55,
            wedgeprops=dict(width=.28,edgecolor=FONDO,linewidth=3),autopct=lambda p:f'{p:.1f}%'.replace('.',','),pctdistance=.85,
            textprops=dict(color='white',fontsize=8))
        axes[0].text(0,.08,'TOTAL REGISTRADO',ha='center',color='#94A3B8',fontsize=7)
        axes[0].text(0,-.13,dinero(gastos.GASTOS_CANTIDAD.sum()),ha='center',color='white',fontsize=11,fontweight='bold')
        axes[0].legend(['Fijos','Variables'],loc='lower center',bbox_to_anchor=(.5,-.2),ncol=2,frameon=False,fontsize=8)
    else:axes[0].text(.5,.5,'Sin base positiva',transform=axes[0].transAxes,ha='center')
    axes[0].set_title('Gastos fijos y variables',color='white',fontsize=10,pad=18)
    for ax,valor,limites,meta,titulo in [
        (axes[1],pagos/ingreso*100 if ingreso>0 else None,(0,max(100,np.ceil(max(pagos/ingreso*100 if ingreso>0 else 0,0)/10)*10)),30,'Ingresos destinados a deudas'),
        (axes[2],balance/ingreso*100 if ingreso>0 else None,(min(-100,np.floor((balance/ingreso*100 if ingreso>0 else 0)/10)*10),100),20,'Capacidad de ahorro / balance')]:
        ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-1.2,1.2);ax.set_ylim(-.85,1.25)
        ax.set_title(titulo,color='white',fontsize=10,pad=18)
        lo,hi=limites
        if valor is not None:hi=max(hi,valor)
        def ang(v):return np.pi*(1-(v-lo)/(hi-lo))
        intervalos=[(0,10,VERDE),(10,30,AZUL),(30,40,AMBAR),(40,hi,ROJO)] if meta==30 else [(lo,0,ROJO),(0,20,AMBAR),(20,hi,VERDE)]
        for a,b,c in intervalos:
            t=np.linspace(ang(a+.5),ang(b-.5),100);ax.plot(np.cos(t),np.sin(t),color=c,lw=13,alpha=.27,solid_capstyle='round')
        if valor is not None:
            color=(VERDE if valor<=10 else AZUL if valor<=30 else AMBAR if valor<=40 else ROJO) if meta==30 else (ROJO if valor<0 else AMBAR if valor<20 else VERDE)
            t=np.linspace(ang(min(0,valor)),ang(max(0,valor)),100);ax.plot(np.cos(t),np.sin(t),color=color,lw=8,solid_capstyle='round')
            t=ang(valor);ax.plot([0,.82*np.cos(t)],[0,.82*np.sin(t)],color='#CFE4F6',lw=2)
            ax.scatter([0,np.cos(t)],[0,np.sin(t)],s=[25,50],color=color,zorder=5)
            ax.text(0,-.35,f'{valor:.2f} %'.replace('.',','),ha='center',color=color,fontsize=18,fontweight='bold')
        else:ax.text(0,-.35,'Sin datos',ha='center',color='#94A3B8',fontsize=15)
        t=ang(meta);ax.plot([.9*np.cos(t),1.1*np.cos(t)],[.9*np.sin(t),1.1*np.sin(t)],color='white',lw=1.5)
        ax.text(0,-.64,f'Referencia: {meta} %',ha='center',color='#94A3B8',fontsize=8)
    total=float(gastos.GASTOS_CANTIDAD.sum())
    valores=[balance/ingreso*100 if ingreso else 0,fijos/total*100 if total else 0,
             variables/total*100 if total else 0,pagos/ingreso*100 if ingreso else 0,
             max(ingreso*.3-pagos,0)/ingreso*100 if ingreso else 0]
    ax=axes[3]
    colores=[VERDE if valores[0]>=0 else ROJO,AZUL,VIOLETA,AMBAR,'#2863BD']
    ax.barh(range(5),valores,color=colores,height=.5)
    ax.set_yticks(range(5));ax.set_yticklabels(['Ahorro','Fijos','Variables','Deudas','Capacidad deuda'],fontsize=8)
    ax.invert_yaxis();ax.set_title('Indicadores porcentuales clave',fontsize=10,pad=18,color='white')
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:.0f}%'))
    for k,v in enumerate(valores):ax.annotate(f'{v:.2f}%'.replace('.',','),(v,k),xytext=(5 if v>=0 else -5,0),textcoords='offset points',ha='left' if v>=0 else 'right',va='center',fontsize=8,color='white')
    ax.margins(x=.3);ax.grid(axis='x',alpha=.12);ax.tick_params(labelsize=8)
    fig.subplots_adjust(left=.09,right=.96,top=.9,bottom=.08,wspace=.37,hspace=.65)
    return fig


def sankey_noche(gastos,ingresos):
    fuentes,destinos=preparar_flujos(gastos,ingresos)
    entrada=float(fuentes.sum());salida=float(destinos.sum());base=max(entrada,salida)
    if base<=0:return None
    escala=240/base
    def filas(serie):
        cursor=55;items=[]
        for n,v in serie.items():
            h=max(68,v*escala);items.append((str(n),float(v),cursor+h/2,h));cursor+=h+12
        return items,cursor
    izq,alto_i=filas(fuentes);der,alto_g=filas(destinos)
    alto=max(600,alto_i+35,alto_g+35);centro=alto/2
    fig,ax=plt.subplots(figsize=(11.2,6.8));ax.set_xlim(0,1180);ax.set_ylim(alto,0);ax.axis('off')
    def cinta(x,y,xx,yy,h,color):
        if h<=0:return
        medio=(x+xx)/2
        vertices=[(x,y),(medio,y),(medio,yy),(xx,yy),(xx,yy+h),(medio,yy+h),(medio,y+h),(x,y+h),(x,y)]
        ax.add_patch(PathPatch(Path(vertices,[Path.MOVETO]+[Path.CURVE4]*3+[Path.LINETO]+[Path.CURVE4]*3+[Path.CLOSEPOLY]),facecolor=color,edgecolor='none',alpha=.48))
    iy=centro-entrada*escala/2;gy=centro-salida*escala/2
    cursor=iy
    for j,(nombre,v,y,h) in enumerate(izq):cinta(255,y-v*escala/2,425,cursor,v*escala,PALETA[j%len(PALETA)]);cursor+=v*escala
    cinta(480,iy,690,gy,min(entrada,salida)*escala,'#F04464')
    cursor=gy
    for j,(nombre,v,y,h) in enumerate(der):cinta(745,cursor,925,y-v*escala/2,v*escala,PALETA[j%len(PALETA)]);cursor+=v*escala
    disponible=max(entrada-salida,0);deficit=max(salida-entrada,0)
    dy=centro+salida*escala/2+45
    if disponible:cinta(480,iy+salida*escala,690,dy,disponible*escala,VERDE)
    if deficit:cinta(560,gy+salida*escala+65,690,gy+entrada*escala,deficit*escala,AMBAR)
    for items,x,total in [(izq,20,entrada),(der,925,salida)]:
        for j,(nombre,v,y,h) in enumerate(items):
            ax.add_patch(FancyBboxPatch((x,y-h/2),235,h,boxstyle='round,pad=0,rounding_size=10',facecolor='#111F33',edgecolor=PALETA[j%len(PALETA)],lw=.7))
            ax.text(x+14,y-15,'\n'.join(textwrap.wrap(nombre,24)[:2]),fontsize=7,fontweight='bold',va='center',color='white')
            ax.text(x+14,y+9,dinero(v),fontsize=9,fontweight='bold',color='white')
            ax.text(x+14,y+27,f'{v/total*100:.1f}%'.replace('.',','),fontsize=7,color=PALETA[j%len(PALETA)])
    def nodo(x,y,h,color,nombre,v):
        if h<=0:return
        ax.add_patch(FancyBboxPatch((x,y),55,h,boxstyle='round,pad=0,rounding_size=8',facecolor=color,edgecolor='none'))
        ax.add_patch(FancyBboxPatch((x-35,y+h/2-40),125,80,boxstyle='round,pad=0,rounding_size=10',facecolor=color,edgecolor='none'))
        ax.text(x+27,y+h/2-7,nombre,ha='center',fontsize=8,color='white',fontweight='bold')
        ax.text(x+27,y+h/2+14,dinero(v),ha='center',fontsize=9,color='white',fontweight='bold')
    nodo(425,iy,entrada*escala,'#2863BD','Ingresos',entrada);nodo(690,gy,salida*escala,'#F04464','Gastos',salida)
    if disponible:nodo(690,dy,max(disponible*escala,1),VERDE,'Disponible',disponible)
    if deficit:nodo(505,gy+salida*escala+65,max(deficit*escala,1),AMBAR,'Déficit',deficit)
    ax.text(20,25,'FUENTES DE INGRESO',fontsize=9,color='#94A3B8',fontweight='bold')
    ax.text(1160,25,'DESTINOS DEL GASTO',fontsize=9,color='#94A3B8',ha='right',fontweight='bold')
    fig.subplots_adjust(left=.01,right=.99,bottom=.03,top=.98)
    return fig


def distribucion_noche(gastos,promedios,panel=None):
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.8))
    axes[0].bar(['Diario','Semanal','Mensual'],promedios,color=[AZUL,VIOLETA,VERDE],width=.5)
    axes[0].set_title('Promedios de gasto',fontsize=11,pad=20)
    for k,v in enumerate(promedios):axes[0].annotate(dinero(v),(k,v),xytext=(0,7 if v>=0 else -12),textcoords='offset points',ha='center',fontsize=9,color='white')
    axes[0].margins(y=.3);axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,p:dinero(v)))
    vals=pd.to_numeric(gastos.GASTOS_CANTIDAD,errors='coerce');vals=vals.loc[vals.gt(0)]
    axes[1].set_title('Distribución logarítmica de montos',fontsize=11,pad=20)
    if not vals.empty:
        bins=np.geomspace(vals.min(),vals.max(),min(24,max(8,int(np.sqrt(len(vals)))))+1) if vals.max()>vals.min() else np.array([vals.min()/np.sqrt(2),vals.max()*np.sqrt(2)])
        axes[1].hist(vals,bins=bins,color=AZUL,edgecolor='#7DD3FC',rwidth=.94)
        axes[1].set_xscale('log');axes[1].set_xlabel('Monto (COP) · escala logarítmica');axes[1].set_ylabel('Número de pagos')
        from matplotlib.ticker import FixedLocator, NullLocator
        marcas=sorted(set(float(f'{v:.2g}') for v in np.geomspace(bins[0],bins[-1],6)))
        axes[1].xaxis.set_major_locator(FixedLocator(marcas));axes[1].xaxis.set_minor_locator(NullLocator())
        axes[1].xaxis.set_major_formatter(FuncFormatter(lambda v,p:dinero(v)))
        axes[1].tick_params(axis='x',rotation=35)
    else:axes[1].text(.5,.5,'Sin gastos positivos',transform=axes[1].transAxes,ha='center')
    for ax in axes:ax.grid(alpha=.1);ax.set_axisbelow(True);ax.tick_params(labelsize=8)
    fig.subplots_adjust(left=.12,right=.98,top=.84,bottom=.2,wspace=.38)
    if panel in (0,1):
        fig.delaxes(axes[1-panel])
        axes[panel].set_position([.13,.23,.83,.59])
    return fig


def frecuencia_noche(gastos):
    d=gastos_validos(gastos)
    if 'GASTOS_SUBCATEGORIA' not in d or d.empty:return None
    t=d.groupby('GASTOS_SUBCATEGORIA',dropna=False).GASTOS_CANTIDAD.agg(['sum','count','mean'])
    t=t.loc[t['sum'].gt(0)]
    if t.empty:return None
    fig,ax=figura('Frecuencia frente a monto por subcategoría')
    tamanos=230*t['sum']/max(t['sum'].max(),1)
    ax.scatter(t['count'],t['sum'],s=tamanos,c=np.log10(t['sum']),cmap='viridis',edgecolors='#7DD3FC',lw=.7,alpha=.8)
    for nombre,fila in t.nlargest(5,'sum').iterrows():
        ax.annotate(str(nombre),(fila['count'],fila['sum']),xytext=(5,6),textcoords='offset points',fontsize=7)
    ax.set_xscale('log');ax.set_yscale('log');ax.set_xlabel('Número de pagos · escala logarítmica');ax.set_ylabel('Monto total COP · escala logarítmica')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:dinero(v)))
    return fig


def galeria_pdf(gastos,ingresos,trabajos,desde,hasta,opciones):
    """Devuelve los quince gráficos y sus notas; mismos filtros y métodos del panel."""
    datos=gastos_validos(gastos);pos=datos.loc[datos.GASTOS_CANTIDAD.gt(0)]
    mensual=matriz_mensual(gastos,ingresos,trabajos,desde,hasta)
    periodos=list(mensual.index.astype(str));anterior=opciones.get('mes_base') or periodos[0];actual=opciones.get('mes_actual') or periodos[-1]
    if anterior not in periodos:anterior=periodos[0]
    if actual not in periodos:actual=periodos[-1]
    tabla=comparacion(gastos,anterior,actual) if anterior!=actual else pd.DataFrame()
    top=pos.groupby('GASTOS_CATEGORIA').GASTOS_CANTIDAD.sum().nlargest(10).index
    def aviso(ax,texto):ax.text(.5,.5,texto,transform=ax.transAxes,ha='center',wrap=True);ax.axis('off')
    for n,nombre in enumerate(['Dumbbell','Slope Chart','Matriz de correlación','KDE','Swarm','ECDF','Boxplot','Violín','Pareto','Lollipop','Cascada','Sunburst','Mapa día/hora','Media móvil','Resistencia financiera'],1):
        fig,ax=figura(f'{n}. {nombre}');nota=''
        if n==1:
            nota=f'Compara gastos por categoría entre {anterior} y {actual}. Hasta 15 categorías con mayor cambio. Rojo: aumento; verde: reducción.'
            if tabla.empty:aviso(ax,'Selecciona dos meses con movimientos.')
            else:
                t=tabla.head(15).iloc[::-1];y=np.arange(len(t))
                ax.hlines(y,t[anterior],t[actual],color=[ROJO if v>0 else VERDE for v in t.Cambio],lw=3)
                ax.scatter(t[anterior],y,color=AZUL,label=anterior);ax.scatter(t[actual],y,color=AMBAR,label=actual)
                ax.set_yticks(y);ax.set_yticklabels(t.index,fontsize=7);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)));ax.legend(fontsize=8)
                fig.subplots_adjust(left=.27)
        elif n==2:
            nota='Conecta los extremos de dos meses; no representa la trayectoria intermedia. Balance = ingresos menos gastos.'
            if anterior==actual:aviso(ax,'Se requieren dos meses.')
            else:
                m=mensual.copy();m['Balance']=m.get('Ingresos',0)-m.Gastos
                for campo,c in [('Ingresos',VERDE),('Gastos',ROJO),('Balance',AZUL)]:
                    if campo in m:ax.plot([anterior,actual],[m.loc[pd.Period(anterior),campo],m.loc[pd.Period(actual),campo]],marker='o',lw=3,color=c,label=campo)
                ax.legend(fontsize=8);ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)))
        elif n==3:
            nota=f'Correlación de Pearson de variables mensuales no constantes. Base: {len(mensual)} meses. Mínimo cuatro meses; correlación no implica causalidad.'
            m=mensual.loc[:,mensual.nunique()>1]
            if len(m)<4 or len(m.columns)<2:aviso(ax,'Datos insuficientes para correlación.')
            else:
                corr=m.corr();im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm');ax.set_xticks(range(len(corr)));ax.set_xticklabels(corr.columns);ax.set_yticks(range(len(corr)));ax.set_yticklabels(corr.columns)
                for i in range(len(corr)):
                    for j in range(len(corr)):ax.text(j,i,f'{corr.iloc[i,j]:.2f}'.replace('.',','),ha='center',va='center')
                fig.colorbar(im,ax=ax)
        elif n==4:
            nota='Densidad estimada de pagos positivos sobre log(monto), reconvertida a pesos. La altura no representa dinero ni un porcentaje directo.'
            r=calcular_kde(pos.GASTOS_CANTIDAD)
            if r is None:aviso(ax,'Se requieren cinco pagos positivos y dos montos distintos.')
            else:ax.plot(r[0],r[1],color=AZUL,lw=3);ax.fill_between(r[0],r[1],color=AZUL,alpha=.15);ax.set_xscale('log');ax.set_ylabel('Densidad por peso')
        elif n==5:
            nota='Pagos individuales en escala logarítmica. Rojo: mayor que Q3 + 1,5 IQR. Máximo 800 movimientos de ocho categorías; la separación vertical no es una variable financiera.'
            f,_,_=grafico_swarm(gastos)
            if f is None:aviso(ax,'No hay pagos positivos.')
            else:
                tr=f.data[0];ax.scatter(tr.x,tr.y,c=list(tr.marker.color),s=12,alpha=.7);ax.set_xscale('log');ax.set_yticks(f.layout.yaxis.tickvals);ax.set_yticklabels(f.layout.yaxis.ticktext,fontsize=7);ax.invert_yaxis();fig.subplots_adjust(left=.25)
        elif n==6:
            nota='Porcentaje de pagos positivos iguales o inferiores a cada monto. Cada pago cuenta una vez: no es porcentaje del gasto total.'
            if pos.empty:aviso(ax,'No hay pagos positivos.')
            else:
                c=pos.GASTOS_CANTIDAD.value_counts().sort_index();ax.step(np.r_[0,c.index],np.r_[0,c.cumsum()/c.sum()*100],where='post',color=VERDE,lw=3);ax.set_ylim(0,105);ax.set_ylabel('Pagos (%)');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)))
        elif n in [7,8]:
            nota='Distribución de pagos por categoría. Caja: 50 % central y mediana. El violín usa log10(monto) y requiere cinco pagos con variación; su ancho muestra densidad, no gasto total.'
            grupos=[pos.loc[pos.GASTOS_CATEGORIA.eq(c),'GASTOS_CANTIDAD'].to_numpy() for c in top]
            if not grupos:aviso(ax,'No hay pagos positivos.')
            elif n==7:
                ax.boxplot(grupos,vert=False,labels=top,patch_artist=True,boxprops=dict(facecolor='#164E63'),medianprops=dict(color=VERDE));ax.set_xscale('log');ax.invert_yaxis();fig.subplots_adjust(left=.25)
            else:
                validos=[(c,g) for c,g in zip(top[:8],grupos[:8]) if len(g)>=5 and np.unique(g).size>1]
                if not validos:aviso(ax,'Datos insuficientes por categoría.')
                else:ax.violinplot([np.log10(g) for _,g in validos],vert=False,showmedians=True);ax.set_yticks(range(1,len(validos)+1));ax.set_yticklabels([c for c,_ in validos]);ax.set_xlabel('log10 del monto');fig.subplots_adjust(left=.25)
        elif n in [9,10]:
            t=datos_pareto(gastos)
            nota='Categorías con gasto neto positivo. Pareto: barras de monto y línea de porcentaje acumulado; 80 % es una referencia. Lollipop: hasta 12 categorías por monto.'
            if t.empty:aviso(ax,'No hay gasto neto positivo.')
            elif n==9:
                ax.bar(range(len(t)),t.Monto,color=AZUL);ax.set_xticks(range(len(t)));ax.set_xticklabels(t.index,rotation=30,ha='right',fontsize=7)
                der=ax.twinx();der.plot(range(len(t)),t['Acumulado %'],color=AMBAR,marker='o');der.axhline(80,color=ROJO,ls=':');der.set_ylim(0,105);der.tick_params(colors='#B4C9D9');ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)))
            else:
                t=t.head(12).iloc[::-1];y=np.arange(len(t));ax.hlines(y,0,t.Monto,color='#284562',lw=3);ax.scatter(t.Monto,y,color=AZUL,s=60);ax.set_yticks(y);ax.set_yticklabels(t.index);fig.subplots_adjust(left=.25)
        elif n==11:
            nota=f'Cascada completa de {anterior} a {actual}. Todas las categorías contribuyen; rojo aumenta el gasto y verde lo reduce. El total final concilia con el segundo mes.'
            if tabla.empty:aviso(ax,'Se requieren dos meses con gastos.')
            else:
                valores=[float(tabla[anterior].sum())]+tabla.Cambio.tolist()+[float(tabla[actual].sum())];suma=valores[0]
                ax.bar(0,suma,color=AZUL)
                for k,v in enumerate(valores[1:-1],1):ax.bar(k,abs(v),bottom=min(suma,suma+v),color=ROJO if v>0 else VERDE);suma+=v
                ax.bar(len(valores)-1,valores[-1],color=AZUL);ax.set_xticks(range(len(valores)));ax.set_xticklabels([anterior]+tabla.index.tolist()+[actual],rotation=35,ha='right',fontsize=7);ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)))
        elif n==12:
            nota='Versión impresa del Sunburst: anillo interior por categoría y exterior por subcategoría. Usa pagos positivos y conserva los totales entre niveles.'
            if pos.empty:aviso(ax,'No hay pagos positivos.')
            else:
                p=pos.copy();p['Sub']=p.get('GASTOS_SUBCATEGORIA',pd.Series('Sin subcategoría',index=p.index)).fillna('Sin subcategoría')
                cat=p.groupby('GASTOS_CATEGORIA').GASTOS_CANTIDAD.sum().sort_values(ascending=False);sub=p.groupby(['GASTOS_CATEGORIA','Sub']).GASTOS_CANTIDAD.sum()
                valores=[];colores=[]
                for j,c in enumerate(cat.index):
                    for v in sub.loc[c]:valores.append(v);colores.append(PALETA[j%len(PALETA)])
                ax.pie(cat,radius=.72,colors=[PALETA[j%len(PALETA)] for j in range(len(cat))],wedgeprops=dict(width=.3,edgecolor=FONDO),startangle=90)
                ax.pie(valores,radius=1,colors=colores,wedgeprops=dict(width=.25,edgecolor=FONDO),startangle=90);ax.legend(cat.index,loc='center left',bbox_to_anchor=(1,.5),fontsize=7,frameon=False)
        elif n==13:
            nota='Número de registros por día de semana y hora. Puede representar cuándo se cargaron los movimientos, no cuándo se realizaron. Horas faltantes pueden concentrarse en medianoche.'
            if datos.empty or datos.GASTOS_FECHA.dt.hour.eq(0).all():aviso(ax,'No hay información horaria suficiente.')
            else:
                c=pd.crosstab(datos.GASTOS_FECHA.dt.dayofweek,datos.GASTOS_FECHA.dt.hour).reindex(index=range(7),columns=range(24),fill_value=0)
                im=ax.imshow(c,aspect='auto',cmap='Blues');ax.set_yticks(range(7));ax.set_yticklabels(['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']);ax.set_xlabel('Hora registrada');fig.colorbar(im,ax=ax)
        elif n==14:
            nota='Gasto diario y media móvil de siete días. Incluye ceros en días sin registros y ajustes negativos. La media comienza al completar siete días; no es un pronóstico.'
            dias=pd.date_range(desde,hasta,freq='D');diario=datos.groupby(datos.GASTOS_FECHA.dt.normalize()).GASTOS_CANTIDAD.sum().reindex(dias,fill_value=0)
            if len(diario)<7:aviso(ax,'Selecciona al menos siete días.')
            else:ax.bar(diario.index,diario,color='#284562');ax.plot(diario.index,diario.rolling(7,min_periods=7).mean(),color=AMBAR,lw=2);ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:dinero(x)));fig.autofmt_xdate()
        elif n==15:
            nota='Supuestos ajustables: saldo = ingreso medio × (1 − caída) − gasto medio × (1 + aumento). Incluye meses parciales y sin registros. No es una predicción.'
            if 'Ingresos' not in mensual or mensual.Ingresos.sum()<=0 or mensual.Gastos.sum()<0:aviso(ax,'Faltan ingresos positivos y gastos no negativos.')
            else:
                caida=opciones.get('caida',40);aumento=opciones.get('aumento',40)
                x=np.linspace(0,caida,9) if caida else np.array([0.]);y=np.linspace(0,aumento,9) if aumento else np.array([0.])
                z=float(mensual.Ingresos.mean())*(1-x[None,:]/100)-float(mensual.Gastos.mean())*(1+y[:,None]/100);limite=max(abs(z).max(),1)
                im=ax.imshow(z,origin='lower',aspect='auto',vmin=-limite,vmax=limite,cmap='RdYlGn');ax.set_xticks(range(len(x)));ax.set_xticklabels([f'{v:g}%' for v in x]);ax.set_yticks(range(len(y)));ax.set_yticklabels([f'{v:g}%' for v in y]);ax.set_xlabel('Caída de ingresos');ax.set_ylabel('Aumento de gastos');fig.colorbar(im,ax=ax,format=FuncFormatter(lambda v,p:dinero(v)))
        yield nombre,fig,nota



def perfil_semanal_pdf(gastos,desde,hasta):
    from modules.perfil_semanal import crear_perfil_semanal
    datos=crear_perfil_semanal(gastos,desde,hasta).data[0]
    fig,ax=figura('Perfil por día de la semana')
    ax.bar(datos.x,datos.y,color=[AZUL]*5+[VIOLETA]*2,width=.6)
    for i,(v,detalle) in enumerate(zip(datos.y,datos.customdata)):
        if pd.notna(v):ax.annotate(dinero(v),(i,v),xytext=(0,7 if v>=0 else -12),textcoords='offset points',ha='center',fontsize=9,color='white')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:dinero(v)))
    ax.set_ylabel('Gasto neto medio por día (COP)');ax.margins(y=.25)
    return fig


def polar_semanal_pdf(gastos,desde,hasta):
    from modules.calor_polar import crear_calor_polar
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from matplotlib.cm import ScalarMappable
    t=crear_calor_polar(gastos,desde,hasta).data[0]
    n=len(set(t.base));promedio=float(np.mean(t.marker.color)) if len(t.marker.color) else 0
    referencia=promedio if promedio>0 else 1e-9
    cmap=LinearSegmentedColormap.from_list('altium_gasto',[(0,'#16A34A'),(.25,'#84CC16'),(.5,'#FACC15'),(.75,'#FF7426'),(1,'#FF0033')])
    norm=Normalize(0,2*referencia,clip=True)
    fig=plt.figure(figsize=(11.2,max(7,3+n*.12)))
    ax=fig.add_axes([.02,.12,.62,.76],projection='polar')
    ax.set_theta_zero_location('N');ax.set_theta_direction(-1)
    hueco=max(2,n*.35)
    ax.bar(np.deg2rad(t.theta),np.ones(len(t.base)),width=2*np.pi/7*.94,
           bottom=np.array(t.base)-1+hueco,color=cmap(norm(t.marker.color)),edgecolor=FONDO,linewidth=.45)
    ax.set_ylim(0,hueco+n+.8);ax.set_yticks([])
    ax.set_xticks(np.arange(7)*2*np.pi/7)
    ax.set_xticklabels(['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'],fontsize=9)
    ax.grid(False)
    ax.text(0,0,'GASTO TOTAL\n'+dinero(sum(t.marker.color)),ha='center',va='center',fontsize=10,color='white',fontweight='bold')
    fechas={}
    for base,detalle in zip(t.base,t.customdata):fechas.setdefault(base,[]).append(detalle[0])
    fig.text(.66,.9,'SEMANAS FILTRADAS',fontsize=9,color='white',fontweight='bold')
    filas=max(1,int(np.ceil(n/2)))
    for i,(base,lista) in enumerate(fechas.items()):
        col,fila=divmod(i,filas)
        fig.text(.66+col*.15,.86-fila*(.7/filas),f'S{int(base):02d}  {lista[0]}\n       {lista[-1]}',fontsize=6.8,color='#B4C9D9',va='top')
    cax=fig.add_axes([.97,.2,.012,.55]);cb=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=cax)
    cb.set_ticks([0,referencia,2*referencia]);cb.set_ticklabels(['$0','Promedio','2× promedio']);cb.ax.tick_params(labelsize=7)
    fig.suptitle('Mapa de calor polar · gasto por fecha',color='white',fontsize=13,fontweight='bold',y=.98)
    fig.text(.04,.035,'Cada anillo = una semana. De lunes a domingo. Antiguo dentro, reciente fuera.',fontsize=8,color='#B4C9D9')
    return fig


def anillos_distribucion_pdf(gastos,ingresos,nombres,montos,colores):
    from modules.categorias_noche import _identidad
    fig,axes=plt.subplots(1,2,figsize=(11.2,5.2))
    categorias=gastos.groupby('GASTOS_CATEGORIA').GASTOS_CANTIDAD.sum().sort_values(ascending=False)
    grupos=sorted([(n,v,c) for n,v,c in zip(nombres,montos,colores) if v>0],key=lambda t:t[1],reverse=True)
    datos=[([(str(n),float(v),_identidad(n,i)[1]) for i,(n,v) in enumerate(categorias.items()) if v>0],float(categorias.sum()),'Gasto total'),(grupos,ingresos,'Ingresos')]
    for ax,(filas,total,centro),titulo in zip(axes,datos,['Distribución de gastos por categoría','Regla 50/30/20 sobre tus ingresos']):
        ax.set_title(titulo,color='white',fontsize=10,pad=15)
        if filas:
            ax.pie([v for _,v,_ in filas],colors=[c for _,_,c in filas],startangle=90,counterclock=False,wedgeprops=dict(width=.35,edgecolor=FONDO,linewidth=2))
            etiquetas=[f'{n}  {v/total*100:.1f}%'.replace('.',',') if total>0 else n+'  sin base' for n,v,_ in filas]
            ax.legend(etiquetas,loc='upper center',bbox_to_anchor=(.5,-.05),fontsize=7,frameon=False,ncol=2)
        ax.text(0,.12,centro.upper(),ha='center',fontsize=8,color='#94A3B8')
        ax.text(0,-.12,dinero(total),ha='center',fontsize=12,fontweight='bold',color='white')
    fig.subplots_adjust(left=.02,right=.98,top=.9,bottom=.30,wspace=.3)
    return fig



def mapas_categorias_pdf(gastos):
    from modules.categorias_tarjetas import mosaico
    from modules.categorias_noche import _identidad
    d=gastos.copy()
    d['Categoria']=d.GASTOS_CATEGORIA.fillna('Sin categoría').astype(str)
    desc=d.get('GASTOS_DESCRIPCION',pd.Series('Sin descripción',index=d.index)).fillna('').astype(str).str.strip().replace('','Sin descripción')
    d['Descripcion']=desc
    t=d.groupby(['Categoria','Descripcion']).GASTOS_CANTIDAD.sum()
    t=t[t.gt(0)]
    cats=t.groupby(level=0).sum().sort_values(ascending=False)
    fig,ax=plt.subplots(figsize=(11.2,7));ax.set_xlim(0,1000);ax.set_ylim(600,0);ax.axis('off')
    for i,(cat,x,y,w,h) in enumerate(mosaico(list(cats.items()),0,0,1000,600)):
        c=_identidad(cat,i)[1]
        ax.add_patch(FancyBboxPatch((x+2,y+2),max(.1,w-4),max(.1,h-4),boxstyle='round,pad=0,rounding_size=5',facecolor=c,edgecolor=FONDO,lw=1))
        header=min(48,h*.3)
        if w>50 and h>30:
            ax.text(x+7,y+12,cat.upper(),fontsize=min(9,max(5,w/18)),color='white',va='top',fontweight='bold',clip_on=True)
            ax.text(x+7,y+28,dinero(cats[cat]),fontsize=7,color='white',va='top',clip_on=True)
        if w>8 and h-header>8:
            for nombre,xx,yy,ww,hh in mosaico(list(t.loc[cat].items()),x+5,y+header,w-10,h-header-5):
                ax.add_patch(FancyBboxPatch((xx,yy),max(.1,ww-2),max(.1,hh-2),boxstyle='round,pad=0,rounding_size=2',facecolor='white',alpha=.1,edgecolor='white',lw=.4))
                if ww>45 and hh>25:
                    label='\n'.join(textwrap.wrap(str(nombre).upper(),max(5,int(ww/4.5)))[:max(1,int((hh-10)/9))])
                    ax.text(xx+3,yy+5,label,fontsize=5.5,va='top',color='white',clip_on=True)
    fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
    # Vista de anillos: misma jerarquía categoría/subcategoría, sin navegación en papel.
    d['Subcategoria']=d.GASTOS_SUBCATEGORIA.fillna('Sin subcategoría').astype(str)
    tabla=d.groupby(['Categoria','Subcategoria']).GASTOS_CANTIDAD.sum();tabla=tabla[tabla.gt(0)]
    ctot=tabla.groupby(level=0).sum().sort_values(ascending=False)
    fig2,ax2=plt.subplots(figsize=(11.2,7))
    if len(ctot):
        colores=[_identidad(c,i)[1] for i,c in enumerate(ctot.index)]
        ax2.pie(ctot,colors=colores,radius=.68,startangle=90,counterclock=False,wedgeprops=dict(width=.32,edgecolor=FONDO,linewidth=1))
        vals=[];cols=[]
        for c,color in zip(ctot.index,colores):
            sub=tabla.loc[c].sort_values(ascending=False)
            vals.extend(sub.values);cols.extend([color]*len(sub))
        ax2.pie(vals,colors=cols,radius=1,startangle=90,counterclock=False,wedgeprops=dict(width=.30,edgecolor=FONDO,linewidth=.6))
        ax2.text(0,.03,'GASTO TOTAL',ha='center',fontsize=8,color='#94A3B8')
        ax2.text(0,-.08,dinero(ctot.sum()),ha='center',fontsize=11,color='white',fontweight='bold')
        ax2.legend([f'{c} · {v/ctot.sum()*100:.1f}%'.replace('.',',') for c,v in ctot.items()],loc='center left',bbox_to_anchor=(1,.5),frameon=False,fontsize=8)
    ax2.set_aspect('equal');fig2.subplots_adjust(left=.02,right=.73,top=.96,bottom=.04)
    return fig,fig2
