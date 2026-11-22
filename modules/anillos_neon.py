"""Tarjetas SVG de distribución con leyenda lateral y brillo Altium Noche."""
import math
import re
from html import escape, unescape
from modules.categorias_noche import _clave, _pesos


def icono_svg(nombre,x,y,tam=20):
    clave=_clave(nombre)
    if 'EXTRAORDINARIO' in clave:
        path='<path d="M14 2L4 14h7l-1 8 10-13h-7z"/>'
    elif 'PRESCINDIBLE' in clave:
        path='<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8 8l13 13M8 16L21 3"/>'
    elif 'FUENTE' in clave:
        path='<path d="M2 8l10-6 10 6zM3 22h18M6 10v9M12 10v9M18 10v9"/>'
    elif any(c in clave for c in ['VIVIEN','NECESIDAD','FIJO']):
        path='<path d="M2 11L12 3l10 8M5 10v11h5v-7h4v7h5V10"/>'
    elif any(c in clave for c in ['CREDIT','DEUDA']):
        path='<rect x="2" y="5" width="20" height="15" rx="3"/><path d="M2 10h20M6 15h5"/>'
    elif any(c in clave for c in ['EDUC']):
        path='<path d="M1 9l11-6 11 6-11 6zM6 12v6q6 5 12 0v-6M22 10v9"/>'
    elif any(c in clave for c in ['HIJ']):
        path='<circle cx="12" cy="6" r="3"/><path d="M5 22v-7a7 7 0 0114 0v7M12 14v8"/>'
    elif any(c in clave for c in ['SALUD']):
        path='<path d="M12 22S1 15 2 8c1-6 8-6 10-1 3-5 10-5 10 1 0 7-10 14-10 14zM6 12h4l2-4 2 8 2-4h3"/>'
    elif any(c in clave for c in ['CARRO','MOTO','TRANSP']):
        path='<path d="M3 17V9h18v8M5 9l3-5h9l3 5M3 13h18"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>'
    elif any(c in clave for c in ['AHORRO','UTILIZADO']):
        path='<path d="M12 22V10M12 15C2 15 2 7 3 4c7 0 10 4 9 11zM12 11c0-7 5-9 10-9 0 6-3 10-10 9z"/>'
    elif any(c in clave for c in ['ALIMENT','GUST','VARIABLE']):
        path='<path d="M2 3h3l3 13h12l2-10H6M9 20h1M18 20h1"/>'
    elif 'IMPUEST' in clave:
        path='<path d="M2 8l10-6 10 6zM3 22h18M6 10v9M12 10v9M18 10v9"/>'
    else:
        path='<path d="M5 20V12M12 20V7M19 20V2"/>'
    return f'<g transform="translate({x},{y}) scale({tam/24})" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none">{path}</g>'


def crear_anillo_neon(fig,total,titulo,regla=False,deuda=False,ingreso=False,patrimonio=False,centro=None,subtitulo=None,etiqueta_total=None):
    tr=fig.data[0]
    labels=list(tr.labels);values=[float(v) for v in tr.values]
    # Plotly Express puede guardar la paleta en layout.colorway y dejar
    # marker.colors vacío si no se especifica una columna color.
    paleta = list(fig.layout.colorway or fig.layout.template.layout.colorway or
                  ['#FF3030','#168BFF','#00D99B','#FBBF24','#A78BFA','#22D3EE','#FB923C'])
    colores = list(tr.marker.colors) if tr.marker.colors is not None else [
        paleta[i % len(paleta)] for i in range(len(values))
    ]
    orden = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    labels = [labels[i] for i in orden]
    values = [values[i] for i in orden]
    colores = [colores[i] for i in orden]
    ayudas_ordenadas = [tr.hovertext[i] for i in orden] if tr.hovertext is not None else None
    suma=sum(max(v,0) for v in values)
    ancho = 1200 if deuda else 640
    alto=max(430,166+len(labels)*39) if deuda else max(510,166+len(labels)*39)
    svg=[]
    def text(x,y,value,size=12,color='#E2E8F0',anchor='start',weight=400):
        return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(value))}</text>'
    svg.append(f'<rect x="1" y="1" width="{ancho-2}" height="{alto-2}" rx="20" fill="url(#bg)" stroke="#23569D"/>')
    svg.append('<rect x="19" y="22" width="43" height="43" rx="11" fill="url(#badge)" stroke="#38BDF8"/>')
    svg.append(icono_svg('indicador',29,31,24))
    svg.append(text(75,39,titulo,15,'#F8FAFC',weight=700))
    svg.append(text(75,57,'Distribución de los activos del patrimonio' if patrimonio else 'Participación de cada fuente en el ingreso' if ingreso else 'Participación de cada crédito en el saldo pendiente' if deuda else 'Distribución real sobre ingresos' if regla else 'Participación de cada categoría en el gasto',11,'#94A3B8'))
    svg.append('<g transform="translate(540,0)">' if deuda else '<g>')
    svg.append('<rect x="451" y="77" width="170" height="49" rx="10" fill="#071D3F" stroke="#244A87"/>')
    svg.append(text(463,95,str(etiqueta_total) if etiqueta_total else 'TOTAL ACTIVOS' if patrimonio else 'SALDO PENDIENTE' if deuda else 'TOTAL INGRESOS' if (regla or ingreso) else 'TOTAL GASTOS',9,'#94A3B8'))
    svg.append(text(463,114,_pesos(total),16,'#38BDF8',weight=700))
    svg.append('</g>')
    cx,cy,r,hole=(300,245,137,73) if deuda else (192,280,163,86)
    angle=-90
    datos=[]
    for indice,(nombre,valor,color) in enumerate(zip(labels,values,colores)):
        if valor<=0 or suma<=0:continue
        end=angle+valor/suma*360
        # Dos arcos para el caso de una única porción de 360 grados.
        def point(rad,a):return cx+rad*math.cos(math.radians(a)),cy+rad*math.sin(math.radians(a))
        if end-angle>=359.999:
            path=f'M{cx},{cy-r} A{r},{r} 0 1 1 {cx},{cy+r} A{r},{r} 0 1 1 {cx},{cy-r} M{cx},{cy-hole} A{hole},{hole} 0 1 0 {cx},{cy+hole} A{hole},{hole} 0 1 0 {cx},{cy-hole}'
        else:
            x1,y1=point(r,angle);x2,y2=point(r,end);x3,y3=point(hole,end);x4,y4=point(hole,angle);large=int(end-angle>180)
            path=f'M{x1},{y1} A{r},{r} 0 {large} 1 {x2},{y2} L{x3},{y3} A{hole},{hole} 0 {large} 0 {x4},{y4} Z'
        pct=valor/total*100 if total>0 else 0
        if not regla:pct=valor/suma*100
        if ayudas_ordenadas is not None:
            tip = unescape(re.sub(r"<[^>]+>", "", str(ayudas_ordenadas[indice]).replace("<br>", " | ")))
        else:
            tip = str(nombre) + ' | ' + _pesos(valor) + ' | ' + format(pct,'.1f').replace('.',',') + ('% DE ACTIVOS' if patrimonio else '% DEL INGRESO' if ingreso else '% DEL GASTO')
            if total > 0:
                tip += (' | TOTAL ACTIVOS: ' if patrimonio else ' | TOTAL INGRESOS: ' if ingreso else ' | SALDO TOTAL: ' if deuda else ' | TOTAL DE GASTOS: ') + _pesos(total)
        tip = re.sub(r"\$([\d,]+)", lambda m: "$" + m[1].replace(",", "."), tip)
        datos.append((nombre,valor,color,pct))
        svg.append(f'<path class="segmento" data-tip="{escape(tip,quote=True)}" d="{path}" fill="{color}" fill-rule="evenodd" stroke="#07152E" stroke-width="2"/>')
        if valor/suma>=.025:
            x,y=point((r+hole)/2,(angle+end)/2)
            svg.append(icono_svg('fuente' if ingreso else 'credito' if deuda else nombre,x-10,y-23,20))
            if valor/suma>=.065:
                svg.append(text(x,y+7,(str(nombre).upper() if len(str(nombre))<=16 else str(nombre).upper()[:15]+'…'),10,'white','middle',700))
                svg.append(text(x,y+22,format(pct,'.1f').replace('.',',')+'%' if (total>0 or not regla) else '—',11,'white','middle',700))
        angle=end
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{r+1}" fill="none" stroke="#3F6DFF" stroke-width="2" filter="url(#glow)"/>')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#shine)" pointer-events="none"/>')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{hole-1}" fill="#08172F" stroke="#244A87"/>')
    svg.append(icono_svg('credito',cx-13,cy-44,26))
    svg.append(text(cx,cy-3,str(subtitulo).upper() if subtitulo else 'TOTAL ACTIVOS' if patrimonio else 'SALDO TOTAL' if deuda else 'TOTAL INGRESOS' if ingreso else 'INGRESOS' if regla else 'TOTAL DE GASTOS',11,'#94A3B8','middle'))
    svg.append(text(cx,cy+20,str(centro) if centro is not None else _pesos(total),25 if centro is not None else 20,'#F8FAFC','middle',700))
    svg.append(text(cx,cy+40,(str(len(datos))+' CRÉDITOS CON SALDO') if deuda else 'PERIODO FILTRADO',9,'#7DD3FC','middle'))
    svg.append('<g transform="translate(300,0)">' if deuda else '<g>')
    legend_h=max(120,len(datos)*39+18)
    ly=max(143,cy-legend_h/2)
    svg.append(f'<rect x="376" y="{ly}" width="{480 if deuda else 247}" height="{legend_h}" rx="12" fill="#071A36" stroke="#1A4B87"/>')
    for i,(nombre,valor,color,pct) in enumerate(datos):
        y=ly+26+i*39
        svg.append(f'<circle cx="390" cy="{y-4}" r="4.5" fill="{color}"/>')
        svg.append(icono_svg('fuente' if ingreso else 'credito' if deuda else nombre,400,y-12,16))
        # Nombres completos con reducción tipográfica en etiquetas largas.
        size=min(14 if deuda else 11,max(7,(280 if deuda else 135)/max(len(str(nombre)),1)*1.6))
        svg.append(text(424,y,str(nombre),size,'#E2E8F0'))
        svg.append(text(835 if deuda else 612,y,format(pct,'.1f').replace('.',',')+'%' if total>0 or not regla else '—',12,color,'end',700))
        svg.append(text(424,y+14,_pesos(valor),9,'#94A3B8'))
    svg.append('</g>')
    html='<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;background:#07111F;overflow:hidden}svg{display:block;width:100%;height:100vh}text,g{pointer-events:none}.segmento:hover{filter:brightness(1.15);stroke:white}#tip{display:none;position:fixed;pointer-events:none;z-index:10;max-width:280px;background:#111F33;border:1px solid #38BDF8;padding:10px;border-radius:10px;color:#F8FAFC;font:12px/1.5 Arial}</style></head><body><svg viewBox="0 0 WIDTH HEIGHT" xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif"><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#061C46"/><stop offset="1" stop-color="#030B1D"/></linearGradient><linearGradient id="badge" x2="1" y2="1"><stop stop-color="#168EEB"/><stop offset="1" stop-color="#181263"/></linearGradient><radialGradient id="shine"><stop offset=".53" stop-color="white" stop-opacity="0"/><stop offset=".76" stop-color="white" stop-opacity=".18"/><stop offset="1" stop-color="white" stop-opacity=".03"/></radialGradient><filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>CONTENT</svg><div id="tip"></div><script>const tip=document.getElementById(\'tip\');document.querySelectorAll(\'.segmento\').forEach(el=>{el.onpointermove=e=>{tip.textContent=el.dataset.tip;tip.style.display=\'block\';tip.style.left=Math.max(3,Math.min(e.clientX+10,innerWidth-tip.offsetWidth-6))+\'px\';tip.style.top=Math.max(3,Math.min(e.clientY+10,innerHeight-tip.offsetHeight-6))+\'px\';};el.onpointerleave=()=>tip.style.display=\'none\';});</script></body></html>'.replace('WIDTH',str(ancho)).replace('HEIGHT',str(alto)).replace('CONTENT',''.join(svg))
    if titulo == "Distribución de gastos por categoría":
        html = (html.replace('stroke="#3F6DFF" stroke-width="2" filter="url(#glow)"',
                             'stroke="#487699" stroke-width="1"')
                    .replace('stop-opacity=".18"', 'stop-opacity=".07"')
                    .replace('fill="#071A36" stroke="#1A4B87"', 'fill="#0A1A30" stroke="#254565"')
                    .replace('stop-color="#061C46"', 'stop-color="#102849"')
                    .replace('stop-color="#030B1D"', 'stop-color="#081326"'))
    return html,alto


def mostrar_anillo_neon(fig,total,titulo,clave,regla=False,deuda=False,ingreso=False,patrimonio=False,centro=None,subtitulo=None,etiqueta_total=None,ajustar_marco=False):
    import streamlit as st
    import streamlit.components.v1 as components
    if not fig.data:
        st.info("No hay datos para mostrar esta distribución.")
        return
    html,alto=crear_anillo_neon(fig,total,titulo,regla,deuda,ingreso,patrimonio,centro,subtitulo,etiqueta_total)
    ancho = 1200 if deuda else 640
    # La tarjeta de fuentes comparte la altura del gráfico mensual contiguo.
    altura_uniforme = (ingreso or patrimonio) and not ajustar_marco
    altura_panel = 540 if altura_uniforme else alto
    dimension = "height:540px !important;aspect-ratio:auto;" if altura_uniforme else f"height:auto !important;aspect-ratio:{ancho} / {alto};"
    st.markdown(f'<style>.st-key-{clave} {{width:100%;max-width:100%;}} .st-key-{clave} iframe {{width:100% !important;{dimension}display:block;border:0;max-height:none !important;}}</style>',unsafe_allow_html=True)
    with st.container(key=clave):components.html(html,height=altura_panel,scrolling=False)
