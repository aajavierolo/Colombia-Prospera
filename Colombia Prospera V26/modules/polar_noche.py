"""Calendario polar SVG con acabado nocturno y fechas reales."""
import math
import json
from html import escape
from modules.calor_polar import crear_calor_polar


def crear_polar_noche(gastos, desde, hasta):
    fig = crear_calor_polar(gastos, desde, hasta)
    t = fig.data[0]
    semanas = sorted(set(t.base))
    n = len(semanas)
    alto = max(800, 160 + math.ceil(n/2)*32)
    cx, cy, radio, hueco = 380, 420, 250, 94
    ancho = (radio-hueco)/max(n,1)
    promedio = sum(t.marker.color)/max(len(t.marker.color),1)
    total = sum(t.marker.color)
    def pesos(v): return "$ " + format(v, ",.0f").replace(",", ".")
    def punto(r,a):
        ang=math.radians(a-90)
        return cx+r*math.cos(ang),cy+r*math.sin(ang)
    def txt(x,y,texto,size=13,color="#E2E8F0",anchor="middle",bold=False):
        return f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" fill="{color}" font-size="{size}" font-weight="{700 if bold else 400}">{escape(str(texto))}</text>'
    def color(v):
        if v <= 0:
            return '#16A34A'
        if promedio <= 0:
            return '#FF0033'
        f = min(v / promedio, 2)
        stops = [(0, (22,163,74)), (.5, (132,204,22)),
                 (1, (250,204,21)), (1.5, (255,116,38)), (2, (255,0,51))]
        for a, b in zip(stops[:-1], stops[1:]):
            if f <= b[0]:
                ratio = (f-a[0])/(b[0]-a[0])
                return '#' + ''.join(format(round(x+(y-x)*ratio),'02x') for x,y in zip(a[1],b[1]))
        return '#FF0033'
    svg=['<rect width="1200" height="'+str(alto)+'" rx="22" fill="url(#fondo)" stroke="#244A87"/>']
    svg.append(txt(30,38,'¿CUÁL ES LA DISTRIBUCIÓN POR DÍAS?',25,'#F8FAFC','start',True))
    svg.append(txt(30,64,'CADA ANILLO ES UNA SEMANA · CADA SECTOR ES UN DÍA DE LUNES A DOMINGO',12,'#7DD3FC','start'))
    for rr in [radio+9,radio+22,radio+39]:
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#1566B5" stroke-width="1" stroke-opacity=".35"/>')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radio+4}" fill="none" stroke="#0EA5E9" stroke-width="2" filter="url(#glow)"/>')
    for base,theta,v,detalle in zip(t.base,t.theta,t.marker.color,t.customdata):
        r1=hueco+(base-1)*ancho+.6;r2=hueco+base*ancho-.6
        a=theta-360/14+.55;b=theta+360/14-.55
        x1,y1=punto(r2,a);x2,y2=punto(r2,b);x3,y3=punto(r1,b);x4,y4=punto(r1,a)
        path=f'M{x1},{y1} A{r2},{r2} 0 0 1 {x2},{y2} L{x3},{y3} A{r1},{r1} 0 0 0 {x4},{y4} Z'
        tip=escape(f'{detalle[0]} · {detalle[1]} | GASTO NETO: {pesos(v)} | MOVIMIENTOS: {detalle[2]}',quote=True)
        svg.append(f'<path class="celda" d="{path}" fill="{color(v)}" stroke="#C6E9FF" stroke-opacity=".38" stroke-width=".6" data-tip="{tip}"/>')
    # Un brillo radial sutil respeta el color que codifica el importe.
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radio}" fill="url(#luz)" pointer-events="none"/>')
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{hueco-1}" fill="#08162E" stroke="#38BDF8" stroke-width="2" filter="url(#glow)"/>')
    svg.append(f'<rect x="{cx-16}" y="{cy-57}" width="32" height="24" rx="5" fill="none" stroke="white" stroke-width="2"/><path d="M{cx+5},{cy-50}h14v12h-14z" fill="#08162E" stroke="white" stroke-width="2"/>')
    svg.append(txt(cx,cy-10,'GASTO TOTAL',13,'#B4C9D9'))
    svg.append(txt(cx,cy+17,pesos(total),21,'#FFFFFF',bold=True))
    svg.append(txt(cx,cy+41,'DEL PERIODO FILTRADO',10,'#7DD3FC'))
    dias=['LUNES','MARTES','MIÉRCOLES','JUEVES','VIERNES','SÁBADO','DOMINGO']
    for i,dia in enumerate(dias):
        x,y=punto(radio+27,i*360/7)
        svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#38BDF8" filter="url(#glow)"/>')
        x,y=punto(radio+61,i*360/7)
        svg.append(f'<rect x="{x-54}" y="{y-14}" width="108" height="27" rx="12" fill="#0D2147" stroke="#285F99"/>')
        svg.append(txt(x,y+4,dia,12,'#F8FAFC',bold=True))
    svg.append(txt(380,770,'VERDE: $0 · AMARILLO: PROMEDIO · ROJO: SUPERIOR AL PROMEDIO',12,'#B4C9D9'))
    svg.append(txt(820,119,'SEMANAS DEL PERIODO',15,'#F8FAFC',bold=True))
    fechas_por_semana={}
    for base,detalle in zip(t.base,t.customdata):fechas_por_semana.setdefault(base,[]).append(detalle[0])
    filas=max(1,math.ceil(n/2))
    for i,base in enumerate(semanas):
        col,fila=divmod(i,filas);x=740+col*166;y=153+fila*32
        fechas=fechas_por_semana[base]
        svg.append(txt(x,y,f'S{int(base):02d}  {fechas[0]}',11,'#E2E8F0','start',True))
        svg.append(txt(x,y+13,'       '+fechas[-1],10,'#94A3B8','start'))
    svg.append(txt(1010,alto-47,'ANILLOS: ANTIGUO DENTRO → RECIENTE FUERA',10,'#94A3B8'))
    svg.append('<rect x="1107" y="178" width="17" height="400" rx="8" fill="url(#escala)" stroke="#284562"/>')
    for y,label in [(181,'2× PROMEDIO'),(379,'PROMEDIO'),(578,'$0')]:svg.append(txt(1132,y,label,10,'#E2E8F0','start'))
    svg.append(txt(1115,610,pesos(promedio),12,'#FACC15',bold=True))
    html='<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;background:#07111F;font-family:Arial,sans-serif;overflow:hidden}svg{width:100%;height:100vh;display:block}text{pointer-events:none}.celda:hover{stroke:white;stroke-width:2;filter:brightness(1.3)}#tip{position:fixed;display:none;pointer-events:none;background:#111F33;border:1px solid #38BDF8;border-radius:9px;padding:10px;color:white;font:13px Arial;max-width:310px;line-height:1.5}</style></head><body><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 HEIGHT" font-family="Arial,sans-serif"><defs><linearGradient id="fondo" x2="1" y2="1"><stop stop-color="#061C46"/><stop offset="1" stop-color="#030A1B"/></linearGradient><radialGradient id="luz"><stop offset=".32" stop-color="#FFFFFF" stop-opacity=".02"/><stop offset=".72" stop-color="#FFFFFF" stop-opacity=".19"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient><linearGradient id="escala" x2="0" y2="1"><stop stop-color="#FF0033"/><stop offset=".25" stop-color="#FF7426"/><stop offset=".5" stop-color="#FACC15"/><stop offset=".75" stop-color="#84CC16"/><stop offset="1" stop-color="#16A34A"/></linearGradient><filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>CONTENT</svg><div id="tip"></div><script>const tip=document.getElementById(\'tip\');document.querySelectorAll(\'.celda\').forEach(el=>{el.onpointermove=e=>{tip.textContent=el.dataset.tip;tip.style.display=\'block\';tip.style.left=Math.max(4,Math.min(e.clientX+12,innerWidth-tip.offsetWidth-8))+\'px\';tip.style.top=Math.max(4,Math.min(e.clientY+12,innerHeight-tip.offsetHeight-8))+\'px\';};el.onpointerleave=()=>tip.style.display=\'none\';});</script></body></html>'.replace('HEIGHT',str(alto)).replace('CONTENT',''.join(svg))
    return html, alto
