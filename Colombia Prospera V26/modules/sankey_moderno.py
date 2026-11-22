"""Presentación SVG del flujo financiero, con tarjetas y cintas proporcionales."""
import html
import textwrap
from modules.sankey_financiero import preparar_flujos, icono_flujo, PALETA


def crear_sankey_html(gastos, ingresos):
    fuentes,destinos=preparar_flujos(gastos,ingresos)
    entrada=float(fuentes.sum());salida=float(destinos.sum())
    disponible=max(entrada-salida,0);deficit=max(salida-entrada,0)
    if max(entrada,salida)<=0:return '',0
    dinero=lambda v:f"${v:,.0f}".replace(',','.')
    pct=lambda v,total:f"{v/total*100:.1f}%".replace('.',',') if total>0 else 'Sin base'
    base=max(entrada,salida);escala=240/base
    def filas(serie):
        cursor=60;resultado=[]
        for nombre,valor in serie.items():
            ancho=float(valor)*escala;alto=max(68,ancho)
            resultado.append((str(nombre),float(valor),cursor+alto/2,alto,ancho))
            cursor+=alto+12
        return resultado,cursor
    fuentes_filas,fin_i=filas(fuentes);destinos_filas,fin_g=filas(destinos)
    alto=max(560,fin_i+25,fin_g+25)
    centro=60+(alto-110)/2
    ingreso_h=entrada*escala;gasto_h=salida*escala
    ingreso_y=centro-ingreso_h/2;gasto_y=centro-gasto_h/2
    partes=[]
    def esc(v):return html.escape(str(v),quote=True)
    def tip(texto):return f'class="tip" data-tip="{esc(texto)}"'
    def texto(x,y,contenido,tamano=13,color='#E2E8F0',peso=500,ancla='start'):
        return f'<text x="{x}" y="{y}" text-anchor="{ancla}" font-size="{tamano}" font-weight="{peso}" fill="{color}">{esc(contenido)}</text>'
    def cinta(x1,y1,x2,y2,grosor,color,detalle):
        if grosor<=0:return
        mitad=(x1+x2)/2
        partes.append(f'<path {tip(detalle)} d="M{x1},{y1} C{mitad},{y1} {mitad},{y2} {x2},{y2} L{x2},{y2+grosor} C{mitad},{y2+grosor} {mitad},{y1+grosor} {x1},{y1+grosor} Z" fill="{color}" opacity=".47"/>')
    # Las cintas se dibujan primero; las tarjetas y los nodos van encima.
    cursor=ingreso_y
    for j,(nombre,valor,y,h,ancho) in enumerate(fuentes_filas):
        cinta(255,y-ancho/2,425,cursor,ancho,PALETA[j%len(PALETA)],f'{nombre} → ingresos\n{dinero(valor)} · {pct(valor,entrada)} de ingresos')
        cursor+=ancho
    cinta(480,ingreso_y,690,gasto_y,min(entrada,salida)*escala,'#F25470',f'Ingresos destinados a gastos\n{dinero(min(entrada,salida))}')
    disponible_y=centro+gasto_h/2+55
    if disponible:
        cinta(480,ingreso_y+salida*escala,690,disponible_y,disponible*escala,'#22BC88',f'Disponible\n{dinero(disponible)} · {pct(disponible,entrada)} de ingresos')
        alto=max(alto,disponible_y+max(95,disponible*escala)+50)
    if deficit:
        cinta(560,gasto_y+gasto_h+75,690,gasto_y+entrada*escala,deficit*escala,'#EBA334',f'Déficit por financiar\n{dinero(deficit)}\nNo es un ingreso registrado')
        alto=max(alto,gasto_y+gasto_h+deficit*escala+160)
    cursor=gasto_y
    for j,(nombre,valor,y,h,ancho) in enumerate(destinos_filas):
        cinta(745,cursor,925,y-ancho/2,ancho,PALETA[j%len(PALETA)],f'Gastos → {nombre}\n{dinero(valor)} · {pct(valor,salida)} de gastos\n{pct(valor,entrada)} de ingresos')
        cursor+=ancho
    def tarjeta(x,nombre,valor,y,h,color,fuente):
        top=y-h/2
        partes.append(f'<g {tip(nombre+chr(10)+dinero(valor)+chr(10)+pct(valor,entrada if fuente else salida))}>')
        partes.append(f'<rect x="{x}" y="{top}" width="235" height="{h}" rx="12" fill="#111F33" stroke="{color}" stroke-opacity=".24" filter="url(#sombra)"/>')
        partes.append(f'<rect x="{x}" y="{top+10}" width="4" height="{h-20}" rx="2" fill="{color}"/>')
        partes.append(f'<rect x="{x+13}" y="{y-22}" width="39" height="44" rx="10" fill="{color}" opacity=".12"/>')
        partes.append(texto(x+32,y+7,icono_flujo(nombre,fuente),23,ancla='middle'))
        nombres=textwrap.wrap(nombre,24)[:2]
        inicio=y-(18 if len(nombres)==1 else 25)
        for k,linea in enumerate(nombres):partes.append(texto(x+62,inicio+k*15,linea,12,peso=650))
        partes.append(texto(x+62,y+9,dinero(valor),16,peso=800))
        partes.append(texto(x+62,y+27,pct(valor,entrada if fuente else salida)+' del total',11,color=color,peso=650))
        partes.append('</g>')
    for j,(nombre,valor,y,h,_) in enumerate(fuentes_filas):tarjeta(20,nombre,valor,y,h,PALETA[j%len(PALETA)],True)
    for j,(nombre,valor,y,h,_) in enumerate(destinos_filas):tarjeta(925,nombre,valor,y,h,PALETA[j%len(PALETA)],False)
    def central(x,y,h,color,icono,titulo,valor,detalle):
        if h<=0:return
        partes.append(f'<rect x="{x}" y="{y}" width="55" height="{h}" rx="10" fill="{color}"/>')
        cy=y+h/2
        # La tarjeta central sobresale del nodo para conservar legibilidad incluso en flujos pequeños.
        partes.append(f'<g {tip(titulo+chr(10)+dinero(valor)+chr(10)+detalle)}>')
        partes.append(f'<rect x="{x-40}" y="{cy-49}" width="135" height="98" rx="13" fill="{color}" filter="url(#sombra)"/>')
        partes.append(texto(x+27,cy-22,icono,24,'white',ancla='middle'))
        partes.append(texto(x+27,cy-2,titulo,11,'white',650,'middle'))
        partes.append(texto(x+27,cy+19,dinero(valor),14,'white',800,'middle'))
        partes.append(texto(x+27,cy+36,detalle,10,'white',500,'middle'))
        partes.append('</g>')
    central(425,ingreso_y,ingreso_h,'#2863BD','📥','Ingresos totales',entrada,'100% de ingresos')
    central(690,gasto_y,gasto_h,'#F04464','🛒','Gastos totales',salida,pct(salida,entrada)+' de ingresos')
    if disponible:central(690,disponible_y,disponible*escala,'#17AB78','🐷','Disponible',disponible,pct(disponible,entrada)+' de ingresos')
    if deficit:central(505,gasto_y+gasto_h+75,deficit*escala,'#D99123','⚠️','Déficit',deficit,'Por financiar')
    # Solo encabezados de las columnas: las métricas ya están en Resumen.
    encabezado=texto(20,34,'FUENTES DE INGRESO',12,'#9DB0C9',750)+texto(1160,34,'DESTINOS DEL GASTO',12,'#9DB0C9',750,'end')
    svg=f'<svg viewBox="0 0 1180 {alto:.0f}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Flujo financiero de fuentes a gastos y disponible"><defs><filter id="sombra" x="-20%" y="-30%" width="150%" height="170%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#183B66" flood-opacity=".09"/></filter></defs><rect width="1180" height="{alto}" rx="22" fill="#07111F"/>{encabezado}{"".join(partes)}</svg>'
    pagina='''<!doctype html><html><head><meta charset="UTF-8"><style>
    *{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent;font-family:Arial,sans-serif;overflow:hidden}
    svg{width:100%;max-width:none;height:auto;display:block;margin:0;overflow:visible}text{font-family:Arial,sans-serif;pointer-events:none}
    .tip{cursor:default;transition:opacity .15s}.tip:hover{opacity:1;filter:brightness(1.03)}
    #tooltip{display:none;position:fixed;z-index:10;pointer-events:none;background:#102033;color:#f8fafc;
    border:1px solid #7CA7D1;border-radius:10px;padding:10px 13px;font-size:12px;line-height:1.5;white-space:pre-line;max-width:280px;box-shadow:0 6px 24px #0003}
    </style></head><body>'''+svg+'''<div id="tooltip"></div><script>
    const box=document.getElementById('tooltip');document.querySelectorAll('.tip').forEach(el=>{
    el.addEventListener('mousemove',e=>{box.textContent=el.dataset.tip;box.style.display='block';
    box.style.left=Math.max(8,Math.min(e.clientX+14,window.innerWidth-box.offsetWidth-10))+'px';
    box.style.top=Math.max(8,Math.min(e.clientY+14,window.innerHeight-box.offsetHeight-10))+'px';});
    el.addEventListener('mouseleave',()=>box.style.display='none');});
    let lastHeight=0;
    function size(){const svg=document.querySelector('svg');const height=Math.ceil(svg.getBoundingClientRect().height)+32;if(height!==lastHeight){lastHeight=height;window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:height},'*');}}
    window.addEventListener('load',size);window.addEventListener('resize',size);new ResizeObserver(size).observe(document.querySelector('svg'));if(document.fonts){document.fonts.ready.then(size);}setTimeout(size,100);
    </script></body></html>'''
    return pagina,int(alto)+32
