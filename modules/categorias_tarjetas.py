"""Mapa de gasto con cabeceras y mosaicos SVG proporcionales."""
from html import escape
import json
import re
from modules.categorias_noche import _identidad, _pesos
from modules.iconos_patrimonio import icono_patrimonio_svg


def mosaico(items, x, y, w, h):
    """Squarify: repartir el área según los importes, sin tamaños mínimos falsos."""
    items = sorted(items, key=lambda t: t[1], reverse=True)
    total = sum(v for _, v in items)
    if total <= 0:
        return []
    pending = [(key, value * w * h / total) for key, value in items]
    result = []
    def worst(row, side):
        if not row or side <= 0:
            return float("inf")
        areas = [a for _, a in row]
        s = sum(areas)
        return max(side * side * max(areas) / (s * s), s * s / (side * side * min(areas)))
    while pending:
        row = [pending.pop(0)]
        side = min(w, h)
        while pending and worst(row + [pending[0]], side) <= worst(row, side):
            row.append(pending.pop(0))
        area = sum(a for _, a in row)
        if w >= h:
            strip = area / h
            offset = y
            for key, a in row:
                dh = a / strip
                result.append((key, x, offset, strip, dh))
                offset += dh
            x += strip
            w = max(0, w - strip)
        else:
            strip = area / w
            offset = x
            for key, a in row:
                dw = a / strip
                result.append((key, offset, y, dw, strip))
                offset += dw
            y += strip
            h = max(0, h - strip)
    return result


def crear_mapa_tarjetas(fig, ingresos=False, patrimonio=False, montos_netos=None):
    if not fig.data:
        return "", 760
    trace = fig.data[0]
    nodes = list(zip(trace.ids, trace.labels, trace.parents, trace.values, trace.customdata))
    roots = [(n, name) for n, name, parent, value, tip in nodes if not parent]
    details = {n: [(k, float(v)) for k, _, parent, v, _ in nodes if parent == n and v > 0] for n, _ in roots}
    totals = {n: sum(v for _, v in details[n]) for n, _ in roots}
    roots = sorted([(n, name) for n, name in roots if totals[n] > 0], key=lambda t: totals[t[0]], reverse=True)
    total = sum(totals[n] for n, _ in roots)
    montos_netos = montos_netos or {}
    def importe(n, valor):
        return _pesos(montos_netos.get(n, valor))
    if total <= 0:
        return "", 760
    height = 770 + max(0, (len(roots) - 1) // 6) * 50
    svg = []
    def text(x, y, value, size=13, weight=400, color="#FFFFFF"):
        return f'<text x="{x:.2f}" y="{y:.2f}" fill="{color}" font-size="{size}" font-weight="{weight}">{escape(str(value).upper())}</text>'
    svg.append('<rect width="1200" height="'+str(height)+'" rx="20" fill="url(#night)" stroke="#284562"/>')
    svg.append(text(24, 38, "🗂️ ¿En qué categorías gasto?", 23, 700))
    svg.append(text(24, 62, "Explora cada categoría y sus descripciones · clic para ampliar · doble clic para volver", 12, color="#B4C9D9"))
    svg.append('<rect x="865" y="14" width="310" height="64" rx="12" fill="#112859" stroke="#315AB0"/>')
    svg.append(text(882, 37, "💰 Gasto representado", 12, color="#B4C9D9"))
    svg.append(text(882, 62, _pesos(total), 23, 700))
    svg.append('<circle cx="1137" cy="46" r="23" fill="none" stroke="#00CFFF" stroke-width="5"/>')
    svg.append(text(1121, 50, "100%", 11, 700))
    svg.append('<g id="map">')
    byid = {n: (name, v, tip) for n, name, parent, v, tip in nodes}
    styles = {n: _identidad(name, i) for i, (n, name) in enumerate(roots)}
    if ingresos:
        estilos_ingresos = {"LABORALES": ("💼", "#00BE85"),
                            "RESIDUALES": ("🏦", "#1678EE"),
                            "SIN CLASIFICAR": ("◆", "#9254E8")}
        styles = {n: estilos_ingresos.get(str(name).upper(), ("◆", "#38BDF8")) for n,name in roots}

    if patrimonio:
        styles = {n: ("💳", "#CF365E") if str(name).upper().startswith("PASIVO")
                  else _identidad(name,i) for i,(n,name) in enumerate(roots)}
    tips = []
    for index, (n, x, y, w, h) in enumerate(mosaico([(n, totals[n]) for n, _ in roots], 16, 92, 1168, 610)):
        name = byid[n][0]
        icon, color = styles[n]
        gap = 6 if (ingresos or patrimonio) else 3
        x, y, w, h = x+gap, y+gap, max(.1,w-2*gap), max(.1,h-2*gap)
        clip = 'cat'+str(index)
        svg.append(f'<defs><clipPath id="{clip}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/></clipPath></defs>')
        svg.append(f'<g class="category" data-box="{x} {y} {w} {h}" clip-path="url(#{clip})">')
        tips.append(escape(str(byid[n][2])))
        svg.append(f'<rect class="hit" data-tip="{len(tips)-1}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{color}"/>')
        header = min(h, min(74, max(44, h * .33)))
        # Reservar el ancho al nombre; el icono solo ocupa espacio en bloques grandes.
        if w > 28 and header > 15:
            ancho_icono = 38 if w > 140 and header > 42 else 0
            if ancho_icono:
                svg.append(f'<circle cx="{x+22}" cy="{y+24}" r="14" fill="#FFFFFF" fill-opacity=".20"/>')
                if patrimonio:
                    svg.append(icono_patrimonio_svg(name,x+10,y+12,24))
                else:
                    svg.append(text(x+11, y+30, icon, 17))
            tam = 12 if w > 120 else 10
            svg.append(f'<foreignObject x="{x+6+ancho_icono}" y="{y+5}" width="{max(1,w-12-ancho_icono)}" height="{max(1,header-8)}"><div xmlns="http://www.w3.org/1999/xhtml" class="fit-label" data-max="14" data-min="6" style="height:100%;overflow:hidden;font-family:Arial,sans-serif;color:white;font-size:{tam}px;font-weight:700;line-height:1.12;overflow-wrap:anywhere">{escape(str(name).upper())}'
                       + (f'<div style="font-size:.88em;margin-top:3px">{escape(importe(n, totals[n]))}</div>' if header > 40 else '')
                       + (f'<div style="font-size:.78em;font-weight:400;margin-top:2px">{totals[n]/total*100:.1f}% DEL TOTAL</div>' if header > 62 else '')
                       + '</div></foreignObject>')
        if h-header > 1 and w > 2:
            for j,(key, dx, dy, dw, dh) in enumerate(mosaico(details[n],x+4,y+header,w-8 if w>8 else w,h-header-4 if h-header>4 else .1)):
                separacion = min(6, dw*.12, dh*.12) if ingresos else 2
                dx += separacion/2 if ingresos else 0
                dy += separacion/2 if ingresos else 0
                dw, dh = max(.1,dw-separacion), max(.1,dh-separacion)
                detailclip = clip+'d'+str(j)
                svg.append(f'<defs><clipPath id="{detailclip}"><rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="4"/></clipPath></defs>')
                tips.append(escape(str(byid[key][2])))
                borde = '#07152E' if ingresos else '#FFFFFF'
                opacidad_borde = '1' if ingresos else '.15'
                grosor_borde = 3 if ingresos else 1
                svg.append(f'<g clip-path="url(#{detailclip})"><rect class="hit" data-tip="{len(tips)-1}" x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="4" fill="#FFFFFF" fill-opacity="{.12+(j%4)*.055 if ingresos else .06+(j%4)*.035}" stroke="{borde}" stroke-opacity="{opacidad_borde}" stroke-width="{grosor_borde}"/>')
                if ingresos and dw > 7 and dh > 7:
                    svg.append(f'<rect x="{dx+2}" y="{dy+2}" width="{dw-4}" height="{dh-4}" rx="3" fill="none" stroke="#E0F2FE" stroke-opacity=".45" stroke-width=".8" pointer-events="none"/>')
                if dw > 10 and dh > 8:
                    label = escape(str(byid[key][0]).upper())
                    # Un único contenedor permite reducir nombre, importe y porcentaje juntos.
                    maximo = min(25, max(10, (dw * dh) ** .5 / 8))
                    contenido = '<div style="font-weight:700">' + label + '</div>'
                    if dh > 23 and dw > 22:
                        contenido += '<div style="font-size:.85em;margin-top:.2em">' + escape(importe(key, byid[key][1])) + '</div>'
                    if dh > 37 and dw > 30:
                        contenido += '<div style="font-size:.78em;opacity:.90;margin-top:.15em">' + format(byid[key][1]/total*100,'.1f').replace('.',',') + '%</div>'
                    svg.append(f'<foreignObject x="{dx+3}" y="{dy+3}" width="{max(1,dw-6)}" height="{max(1,dh-6)}"><div xmlns="http://www.w3.org/1999/xhtml" class="fit-label" data-max="{maximo:.1f}" data-min="5" style="height:100%;overflow:hidden;font-family:Arial,sans-serif;color:white;font-size:10px;line-height:1.12;overflow-wrap:anywhere">{contenido}</div></foreignObject>')
                svg.append('</g>')
        svg.append('</g>')
    svg.append('</g>')
    for i,(n,name) in enumerate(roots):
        x=27+(i%6)*194; y=728+(i//6)*50
        icon,color=styles[n]
        if patrimonio:
            svg.append(f'<rect x="{x-2}" y="{y-16}" width="25" height="25" rx="8" fill="{color}"/>')
            svg.append(icono_patrimonio_svg(name,x+1,y-13,19))
            texto_x, ancho_texto = x+30, 156
        else:
            svg.append(f'<circle cx="{x}" cy="{y-4}" r="5" fill="{color}"/>')
            texto_x, ancho_texto = x+12, 174
        svg.append(f'<foreignObject x="{texto_x}" y="{y-13}" width="{ancho_texto}" height="30"><div xmlns="http://www.w3.org/1999/xhtml" style="font-family:Arial,sans-serif;font-size:11px;color:white;line-height:1.1;overflow-wrap:anywhere">{escape(str(name).upper())}</div></foreignObject>')
        svg.append(text(texto_x,y+30,format(totals[n]/total*100,'.1f').replace('.',',')+'%',10,color='#B4C9D9'))
    tips = [re.sub(r"([+-]?\d+)\.(\d+)%", r"\1,\2%",
                   re.sub(r"\$([\d,]+)", lambda m: "$"+m[1].replace(",", "."), tip)) for tip in tips]
    tips_json=json.dumps(tips,ensure_ascii=True).replace('</','<\/')
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#07111F;font-family:Arial,sans-serif;overflow:hidden}svg{width:100%;height:100vh;display:block}text,foreignObject{pointer-events:none} .category{cursor:pointer}.hit:hover{stroke:white;stroke-width:2;filter:brightness(1.12)}#tip{text-transform:uppercase;display:none;position:fixed;pointer-events:none;background:#111F33;color:#F8FAFC;border:1px solid #38608A;border-radius:10px;padding:12px;font-size:13px;line-height:1.55;max-width:340px;z-index:10;box-shadow:0 8px 28px #0008}button{position:fixed;right:12px;bottom:8px;background:#112859;color:white;border:1px solid #315AB0;border-radius:8px;padding:7px 12px;cursor:pointer;display:block}
</style></head><body><svg id="chart" font-family="Arial, sans-serif" viewBox="0 0 1200 HEIGHT" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="night" x2="1" y2="1"><stop stop-color="#071C42"/><stop offset="1" stop-color="#07111F"/></linearGradient></defs>CONTENT</svg><div id="tip"></div><button id="back">↩ VER TODAS LAS CATEGORÍAS</button><script>
const tips=TIPS,tip=document.getElementById('tip'),chart=document.getElementById('chart'),back=document.getElementById('back');
function ajustarLetras(){
  document.querySelectorAll('.fit-label').forEach(el=>{
    let size=Number(el.dataset.max),min=Number(el.dataset.min);
    el.style.fontSize=size+'px';
    while(size>min&&(el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1)){
      size=Math.max(min,size-.5);el.style.fontSize=size+'px';
    }
  });
}
requestAnimationFrame(ajustarLetras);
if(document.fonts)document.fonts.ready.then(ajustarLetras);
new ResizeObserver(()=>requestAnimationFrame(ajustarLetras)).observe(chart);
document.querySelectorAll('[data-tip]').forEach(el=>{el.addEventListener('pointermove',e=>{tip.innerHTML=tips[Number(el.dataset.tip)].replace(/&lt;br&gt;/g,'<br>').replace(/&lt;b&gt;/g,'<b>').replace(/&lt;\/b&gt;/g,'</b>');tip.style.display='block';tip.style.left=Math.max(4,Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8))+'px';tip.style.top=Math.max(4,Math.min(e.clientY+14,innerHeight-tip.offsetHeight-8))+'px';});el.addEventListener('pointerleave',()=>tip.style.display='none');});
function mostrarCategoria(actual){
  document.querySelectorAll('.category').forEach(el=>{el.style.display=el===actual?'':'none';});
  Array.from(chart.children).forEach(el=>{
    if(el.id!=='map'&&el.tagName.toLowerCase()!=='defs')el.style.visibility='hidden';
  });
  chart.setAttribute('viewBox',actual.dataset.box);
  tip.style.display='none';back.style.display='block';
  requestAnimationFrame(ajustarLetras);
}
document.querySelectorAll('.category').forEach(el=>el.addEventListener('click',()=>mostrarCategoria(el)));
function reset(){
  document.querySelectorAll('.category').forEach(el=>el.style.display='');
  Array.from(chart.children).forEach(el=>el.style.visibility='');
  chart.setAttribute('viewBox','0 0 1200 HEIGHT');
  back.style.display='block';tip.style.display='none';
  requestAnimationFrame(ajustarLetras);
}back.onclick=reset;chart.ondblclick=reset;
</script></body></html>""".replace('HEIGHT',str(height)).replace('CONTENT',''.join(svg)).replace('TIPS',tips_json)
    if ingresos:
        html = html.replace("🗂️ ¿EN QUÉ CATEGORÍAS GASTO?", "🏦 MAPA DE INGRESOS: TIPO → FUENTE")
        html = html.replace("EXPLORA CADA CATEGORÍA Y SUS DESCRIPCIONES", "EXPLORA CADA TIPO DE INGRESO Y SUS FUENTES")
        html = html.replace("💰 GASTO REPRESENTADO", "💰 INGRESOS REPRESENTADOS")
        html = html.replace("VER TODAS LAS CATEGORÍAS", "VER TODOS LOS TIPOS DE FUENTE")
    if patrimonio:
        html = html.replace("🗂️ ¿EN QUÉ CATEGORÍAS GASTO?", "🏦 MAPA DEL PATRIMONIO")
        html = html.replace("EXPLORA CADA CATEGORÍA Y SUS DESCRIPCIONES", "EXPLORA CADA CATEGORÍA Y SUS ACTIVOS O PASIVOS")
        html = html.replace("💰 GASTO REPRESENTADO", "💰 ACTIVOS + PASIVOS (ABS.)")
    return html, height
