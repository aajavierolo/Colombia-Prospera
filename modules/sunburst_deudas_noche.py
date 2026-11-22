"""Sunburst de saldos: tipo de deuda y crédito, con el acabado del anillo Altium Noche."""
from decimal import Decimal
from html import escape,unescape
import math,re
import pandas as pd
from modules.anillos_neon import icono_svg

PALETA=['#FF1744','#168BFF','#00E5A0','#FFC400','#B46CFF','#00D9ED','#FF8A26']

def icono_tipo_deuda(tipo,x,y,tam=18):
    import unicodedata
    clave=''.join(c for c in unicodedata.normalize('NFD',str(tipo).upper()) if unicodedata.category(c)!='Mn')
    nombre=('vivienda' if any(v in clave for v in ['VIVIEN','HIPOTEC','CASA']) else
            'carro' if any(v in clave for v in ['VEHIC','CARRO','MOTO']) else
            'educacion' if any(v in clave for v in ['EDUC','ESTUDIO']) else
            'fuente' if any(v in clave for v in ['COOPER','BANCO','BANCAR']) else
            'hijos' if any(v in clave for v in ['PERSON','LIBRANZA','NOMINA']) else 'credito')
    return icono_svg(nombre,x,y,tam)

def preparar_sunburst_deudas(deudas,ayudas=None):
    grupos={}
    for posicion,(_,fila) in enumerate(deudas.iterrows()):
        valor=pd.to_numeric(fila.get('Saldo'),errors='coerce')
        if pd.isna(valor):
            continue
        if not math.isfinite(float(valor)):
            raise ValueError('Hay un saldo no finito en la distribución de deudas.')
        if valor<=0:
            continue
        tipo=fila.get('Tipo');nombre=fila.get('Nombre')
        tipo=str(tipo).strip() if pd.notna(tipo) and str(tipo).strip() else 'Sin tipo'
        nombre=str(nombre).strip() if pd.notna(nombre) and str(nombre).strip() else 'Crédito sin nombre'
        ayuda=ayudas[posicion] if ayudas is not None and posicion<len(ayudas) else ''
        ayuda=unescape(re.sub(r'<[^>]+>','',str(ayuda).replace('<br>',' | ')))
        ayuda=re.sub(r'\$([\d,]+)',lambda m:'$'+m[1].replace(',','.'),ayuda)
        grupos.setdefault(tipo,[]).append({'nombre':nombre,'saldo':Decimal(str(valor)),'ayuda':ayuda})
    resultado=[]
    for tipo,creditos in grupos.items():
        resultado.append({'tipo':tipo,'saldo':sum((c['saldo'] for c in creditos),Decimal(0)),'creditos':sorted(creditos,key=lambda c:c['saldo'],reverse=True)})
    return sorted(resultado,key=lambda g:g['saldo'],reverse=True)

def crear_sunburst_deudas_html(grupos):
    total=sum((g['saldo'] for g in grupos),Decimal(0))
    numero=sum(len(g['creditos']) for g in grupos)
    alto_base=max(520,175+len(grupos)*30+numero*40)
    alto=alto_base+100
    cy=alto_base/2+20;cx=300
    dinero=lambda v:'$ '+f'''{v:,.0f}'''.replace(',','.')
    porcentaje=lambda v:f'''{v/total*100:.1f}'''.replace('.',',')+' %' if total else '—'
    def texto(x,y,t,size=12,color='#E2E8F0',anchor='start',bold=False):
        return f'''<text x="{x}" y="{y}" fill="{color}" font-size="{size}" text-anchor="{anchor}" font-weight="{700 if bold else 400}">{escape(str(t))}</text>'''
    def sector(r0,r1,a,b):
        def punto(r,ang):return cx+r*math.cos(math.radians(ang)),cy+r*math.sin(math.radians(ang))
        if b-a>=359.999999:
            return f'''M{cx},{cy-r1} A{r1},{r1} 0 1 1 {cx},{cy+r1} A{r1},{r1} 0 1 1 {cx},{cy-r1} M{cx},{cy-r0} A{r0},{r0} 0 1 0 {cx},{cy+r0} A{r0},{r0} 0 1 0 {cx},{cy-r0}'''
        p1,p2,p3,p4=punto(r1,a),punto(r1,b),punto(r0,b),punto(r0,a);large=int(b-a>180)
        return f'''M{p1[0]},{p1[1]} A{r1},{r1} 0 {large} 1 {p2[0]},{p2[1]} L{p3[0]},{p3[1]} A{r0},{r0} 0 {large} 0 {p4[0]},{p4[1]} Z'''
    svg=['<rect x="1" y="1" width="1198" height="'+str(alto-2)+'" rx="20" fill="url(#bg)" stroke="#23569D"/>',
         '<rect x="19" y="22" width="43" height="43" rx="11" fill="url(#badge)" stroke="#38BDF8"/>',icono_svg('indicador',29,31,24),
         texto(75,39,'Distribución del saldo pendiente',15,'#F8FAFC',bold=True),texto(75,57,'Anillo interior: cada crédito · Anillo exterior: tipo de deuda',11,'#94A3B8'),
         '<rect x="991" y="77" width="170" height="49" rx="10" fill="#071D3F" stroke="#244A87"/>',texto(1003,95,'SALDO PENDIENTE',9,'#94A3B8'),texto(1003,114,dinero(total),16,'#38BDF8',bold=True)]
    angle=-90;leyenda_y=150
    svg.append(f'''<rect x="676" y="137" width="480" height="{alto_base-162}" rx="12" fill="#071A36" stroke="#1A4B87"/>''')
    for i,grupo in enumerate(grupos):
        color=PALETA[i%len(PALETA)];final=angle+float(grupo['saldo']/total)*360
        tip_grupo=grupo['tipo']+' | '+dinero(grupo['saldo'])+' COP | '+porcentaje(grupo['saldo'])+' del saldo total | '+str(len(grupo['creditos']))+' créditos'
        svg.append(f'''<path class="nodo" tabindex="0" role="button" aria-pressed="false" aria-label="{escape(tip_grupo,quote=True)}" data-grupo="{i}" data-clave="tipo-{i}" data-nombre="{escape(grupo['tipo'],quote=True)}" data-importe="{dinero(grupo['saldo'])}" data-porcentaje="{porcentaje(grupo['saldo'])}" data-tip="{escape(tip_grupo,quote=True)}" d="{sector(120,168,angle,final)}" fill="{color}" fill-opacity=".72" fill-rule="evenodd" stroke="#07152E" stroke-width="2"><title>{escape(tip_grupo)}</title></path>''')
        if final-angle>=14:
            medio=math.radians((angle+final)/2);gx=cx+144*math.cos(medio);gy=cy+144*math.sin(medio)
            etiqueta=grupo['tipo'] if len(grupo['tipo'])<=13 else grupo['tipo'][:12]+'…'
            svg.append(f'''<defs><clipPath id="tipo-icono-{i}"><path d="{sector(120,168,angle,final)}" fill-rule="evenodd" clip-rule="evenodd"/></clipPath></defs><g class="etiqueta" data-grupo="{i}" data-clave="tipo-{i}" clip-path="url(#tipo-icono-{i})">''')
            if final-angle>=38:
                svg.append(icono_tipo_deuda(grupo['tipo'],gx-9,gy-21,18))
                svg.append(texto(gx,gy+11,etiqueta,9,'white','middle',True))
            else:
                svg.append(icono_tipo_deuda(grupo['tipo'],gx-8,gy-8,16))
            svg.append('</g>')
        svg.append(f'''<g class="nodo" tabindex="0" role="button" aria-pressed="false" aria-label="{escape(tip_grupo,quote=True)}" data-grupo="{i}" data-clave="tipo-{i}" data-nombre="{escape(grupo['tipo'],quote=True)}" data-importe="{dinero(grupo['saldo'])}" data-porcentaje="{porcentaje(grupo['saldo'])}" data-tip="{escape(tip_grupo,quote=True)}"><rect x="687" y="{leyenda_y-9}" width="461" height="29" rx="6" fill="transparent"/>''')
        svg.append(icono_tipo_deuda(grupo['tipo'],690,leyenda_y-4,18))
        svg.append(texto(716,leyenda_y+10,grupo['tipo'],13,color,bold=True))
        svg.append(texto(1138,leyenda_y+10,dinero(grupo['saldo'])+' · '+porcentaje(grupo['saldo']),11,color,'end',True))
        svg.append('</g>')
        leyenda_y+=30;inicio_credito=angle
        for j,credito in enumerate(grupo['creditos']):
            fin_credito=inicio_credito+float(credito['saldo']/total)*360
            ayuda=credito['ayuda'] or (credito['nombre']+' | Tipo: '+grupo['tipo']+' | Saldo: '+dinero(credito['saldo'])+' COP | '+porcentaje(credito['saldo'])+' del total')
            tip=ayuda+' | Dentro de '+grupo['tipo']+': '+f"{credito['saldo']/grupo['saldo']*100:.1f}".replace('.',',')+' %'
            svg.append(f'''<path class="nodo" tabindex="0" role="button" aria-pressed="false" aria-label="{escape(tip,quote=True)}" data-grupo="{i}" data-clave="credito-{i}-{j}" data-nombre="{escape(credito['nombre'],quote=True)}" data-importe="{dinero(credito['saldo'])}" data-porcentaje="{porcentaje(credito['saldo'])}" data-tip="{escape(tip,quote=True)}" d="{sector(72,116,inicio_credito,fin_credito)}" fill="{color}" fill-opacity="{.94 if j%2==0 else .7}" fill-rule="evenodd" stroke="#07152E" stroke-width="2"><title>{escape(tip)}</title></path>''')
            if fin_credito-inicio_credito>=12:
                medio=math.radians((inicio_credito+fin_credito)/2);x=cx+94*math.cos(medio);y=cy+94*math.sin(medio)
                etiqueta=credito['nombre'] if len(credito['nombre'])<=13 else credito['nombre'][:12]+'…'
                svg.append(f'''<defs><clipPath id="credito-icono-{i}-{j}"><path d="{sector(72,116,inicio_credito,fin_credito)}" fill-rule="evenodd" clip-rule="evenodd"/></clipPath></defs><g class="etiqueta" data-grupo="{i}" data-clave="credito-{i}-{j}" clip-path="url(#credito-icono-{i}-{j})">''')
                if fin_credito-inicio_credito>=45:
                    svg.append(icono_svg('credito',x-6,y-20,12))
                    svg.append(texto(x,y+1,etiqueta,9,'white','middle',True))
                    svg.append(texto(x,y+14,porcentaje(credito['saldo']),10,'white','middle',True))
                elif fin_credito-inicio_credito>=27:
                    svg.append(icono_svg('credito',x-7,y-15,14))
                    svg.append(texto(x,y+12,porcentaje(credito['saldo']),9,'white','middle',True))
                else:
                    svg.append(icono_svg('credito',x-7,y-7,14))
                svg.append('</g>')
            svg.append(f'''<g class="nodo" tabindex="0" role="button" aria-pressed="false" aria-label="{escape(tip,quote=True)}" data-grupo="{i}" data-clave="credito-{i}-{j}" data-nombre="{escape(credito['nombre'],quote=True)}" data-importe="{dinero(credito['saldo'])}" data-porcentaje="{porcentaje(credito['saldo'])}" data-tip="{escape(tip,quote=True)}"><rect x="687" y="{leyenda_y-4}" width="461" height="37" rx="6" fill="transparent"/>'''+f'''<circle cx="699" cy="{leyenda_y+8}" r="4" fill="{color}"/>'''+icono_svg('credito',710,leyenda_y-4,16)+texto(734,leyenda_y+10,credito['nombre'],min(12,max(8,290/max(len(credito['nombre']),1)*1.6)))+texto(1138,leyenda_y+10,porcentaje(credito['saldo']),12,color,'end',True)+texto(734,leyenda_y+25,dinero(credito['saldo'])+' COP',10,'#94A3B8')+'</g>')
            leyenda_y+=40;inicio_credito=fin_credito
        angle=final
    svg.extend([f'''<circle cx="{cx}" cy="{cy}" r="170" fill="none" stroke="#3F6DFF" stroke-width="2" filter="url(#glow)"/>''',f'''<circle cx="{cx}" cy="{cy}" r="168" fill="url(#shine)" pointer-events="none"/>''',f'''<circle id="restablecer-centro" class="restablecer" role="button" tabindex="0" aria-label="Mostrar todas las deudas" cx="{cx}" cy="{cy}" r="70" fill="#08172F" stroke="#244A87"/>''','<g class="etiqueta">'+icono_svg('credito',cx-13,cy-43,26)+'</g>',texto(cx,cy-3,'SALDO TOTAL',10,'#94A3B8','middle').replace('<text ','<text id="centro-titulo" ',1),texto(cx,cy+19,dinero(total),min(19,125/max(len(dinero(total)),1)*1.7),'#F8FAFC','middle',True).replace('<text ','<text id="centro-saldo" ',1),texto(cx,cy+38,str(numero)+' CRÉDITOS CON SALDO',9,'#7DD3FC','middle').replace('<text ','<text id="centro-detalle" ',1),texto(cx,alto_base-20,'Haz clic en un segmento o en la leyenda',10,'#94A3B8','middle')])
    svg.append('<g id="restablecer" class="restablecer" role="button" tabindex="0" aria-label="Mostrar todas las deudas"><rect x="680" y="85" width="200" height="33" rx="9" fill="#112B4A" stroke="#38BDF8"/>'+texto(780,106,'Mostrar todo',12,'#E2E8F0','middle',True)+'</g>')
    svg.append(f'''<rect x="24" y="{alto_base+1}" width="1152" height="84" rx="12" fill="#111F33" stroke="#284562"/>''')
    svg.append(texto(40,alto_base+23,'Selecciona un tipo de deuda o un crédito para ver su detalle.',12,'#B4C9D9',bold=True).replace('<text ','<text id="detalle-titulo" ',1))
    for linea in range(3):
        svg.append(texto(40,alto_base+42+linea*15,'',11,'#D7E6FA').replace('<text ',f'''<text id="detalle-linea-{linea}" ''',1))
    html=r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;background:#07111F;overflow:hidden}body>svg{display:block;width:100%;height:100vh}text,.etiqueta,.etiqueta *{pointer-events:none}.nodo,.restablecer{cursor:pointer;outline:none;transition:opacity .2s,filter .2s}.atenuado{opacity:.16}.nodo.seleccionado{filter:brightness(1.18)}path.nodo.seleccionado{stroke:#F8FAFC;stroke-width:3}g.nodo.seleccionado>rect{fill:#38BDF81A;stroke:#38BDF8}.restablecer:hover,.restablecer:focus{filter:brightness(1.25);stroke:#F8FAFC}.nodo:hover,.nodo:focus{filter:brightness(1.2);stroke:#F8FAFC}#tip{display:none;position:fixed;pointer-events:none;z-index:10;max-width:min(330px,calc(100vw - 12px));background:#111F33;border:1px solid #38BDF8;padding:10px 12px;border-radius:10px;color:#F8FAFC;font:12px/1.5 Arial;box-shadow:0 8px 24px #0008}</style></head><body><svg viewBox="0 0 1200 HEIGHT" xmlns="http://www.w3.org/2000/svg" font-family="Arial,sans-serif"><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#061C46"/><stop offset="1" stop-color="#030B1D"/></linearGradient><linearGradient id="badge" x2="1" y2="1"><stop stop-color="#168EEB"/><stop offset="1" stop-color="#181263"/></linearGradient><radialGradient id="shine"><stop offset=".4" stop-color="white" stop-opacity="0"/><stop offset=".76" stop-color="white" stop-opacity=".14"/><stop offset="1" stop-color="white" stop-opacity=".02"/></radialGradient><filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>CONTENT</svg><div id="tip"></div><script>const tip=document.getElementById('tip');function mostrar(el,x,y){tip.textContent=el.dataset.tip;tip.style.display='block';tip.style.left=Math.max(6,Math.min(x+12,innerWidth-tip.offsetWidth-6))+'px';tip.style.top=Math.max(6,Math.min(y+12,innerHeight-tip.offsetHeight-6))+'px'}const nodos=[...document.querySelectorAll('.nodo')];const etiquetas=[...document.querySelectorAll('.etiqueta[data-grupo]')];let seleccion=null;
const centroTitulo=document.getElementById('centro-titulo'),centroSaldo=document.getElementById('centro-saldo'),centroDetalle=document.getElementById('centro-detalle');const originales=[centroTitulo.textContent,centroSaldo.textContent,centroDetalle.textContent];
function coincide(n,el){return n.dataset.clave===el.dataset.clave || (el.dataset.clave.startsWith('tipo-') && n.dataset.grupo===el.dataset.grupo) || (el.dataset.clave.startsWith('credito-') && n.dataset.clave==='tipo-'+el.dataset.grupo)}
function restablecer(){seleccion=null;[...nodos,...etiquetas].forEach(n=>{n.classList.remove('atenuado','seleccionado');if(n.classList.contains('nodo'))n.setAttribute('aria-pressed','false')});[centroTitulo.textContent,centroSaldo.textContent,centroDetalle.textContent]=originales;document.getElementById('detalle-titulo').textContent='Selecciona un tipo de deuda o un crédito para ver su detalle.';for(let i=0;i<3;i++)document.getElementById('detalle-linea-'+i).textContent='';tip.style.display='none'}
function seleccionar(el){if(seleccion===el.dataset.clave){restablecer();return}seleccion=el.dataset.clave;[...nodos,...etiquetas].forEach(n=>{const activo=coincide(n,el);n.classList.toggle('atenuado',!activo);n.classList.toggle('seleccionado',n.dataset.clave===seleccion);if(n.classList.contains('nodo'))n.setAttribute('aria-pressed',String(n.dataset.clave===seleccion))});centroTitulo.textContent=el.dataset.clave.startsWith('tipo-')?'TIPO DE DEUDA':'CRÉDITO';centroSaldo.textContent=el.dataset.importe;centroDetalle.textContent=el.dataset.porcentaje+' DEL TOTAL';document.getElementById('detalle-titulo').textContent=el.dataset.nombre.length>145?el.dataset.nombre.slice(0,142)+'…':el.dataset.nombre;const palabras=(el.dataset.tip||'').split(/\s+/);let lineas=[''];palabras.forEach(p=>{let i=lineas.length-1;if((lineas[i]+' '+p).length>170){lineas.push(p)}else{lineas[i]+=(lineas[i]?' ':'')+p}});if(lineas.length>3)lineas[2]=lineas[2].slice(0,167)+'…';for(let i=0;i<3;i++)document.getElementById('detalle-linea-'+i).textContent=lineas[i]||'';tip.style.display='none'}
nodos.forEach(el=>{el.onpointermove=e=>mostrar(el,e.clientX,e.clientY);el.onpointerleave=()=>tip.style.display='none';el.onfocus=()=>mostrar(el,innerWidth*.4,innerHeight*.5);el.onblur=()=>tip.style.display='none';el.onclick=()=>seleccionar(el);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();seleccionar(el)}}});document.querySelectorAll('.restablecer').forEach(el=>{el.onclick=restablecer;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();restablecer()}}});document.addEventListener('keydown',e=>{if(e.key==='Escape')restablecer()});</script></body></html>'''.replace('HEIGHT',str(alto)).replace('CONTENT',''.join(svg))
    return html,alto

def mostrar_sunburst_deudas(deudas,ayudas=None,clave='deudas_sunburst_noche_v22'):
    import streamlit as st
    import streamlit.components.v1 as componentes
    grupos=preparar_sunburst_deudas(deudas,ayudas)
    if not grupos:
        st.info('No hay saldos pendientes para mostrar en la distribución.')
        return
    html,alto=crear_sunburst_deudas_html(grupos)
    st.markdown(f'''<style>.st-key-{clave}{{width:100%;max-width:100%;min-width:0}}.st-key-{clave} iframe{{width:100% !important;height:auto !important;aspect-ratio:1200 / {alto};display:block;border:0;max-height:none !important}}</style>''',unsafe_allow_html=True)
    with st.container(key=clave):componentes.html(html,height=alto,scrolling=False)
