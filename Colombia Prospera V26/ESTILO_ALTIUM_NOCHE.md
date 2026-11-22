# Altium Noche

Nombre del estilo: **Altium Noche**.

Petición de uso: «Aplica el estilo Altium Noche a este gráfico».

## Referencias existentes

- Manómetro «Ingresos destinados a deudas»: `modules/medidor_deuda.py`, función `crear_medidor_deuda`.
- Sankey «Flujo general de tu dinero»: `modules/sankey_moderno.py`, función `crear_sankey_html`.
- Mantener estos componentes como referencia visual y reutilizar sus reglas al aplicar el estilo. No cambiar cálculos, filtros, unidades, denominadores ni umbrales por una modificación estética.

## Sistema visual

| Elemento | Valor |
|---|---|
| Fondo principal | `#07111F` |
| Tarjetas interiores | `#111F33` |
| Bordes discretos | `#213C58`, `#284562` |
| Texto principal | `#E2E8F0`, `#F8FAFC` |
| Texto secundario | `#94A3B8`, `#B4C9D9` |
| Azul | `#38BDF8`, `#2863BD` |
| Verde | `#00D99B`, `#17AB78` |
| Ámbar | `#F59E0B` |
| Rojo | `#FF526E`, `#F04464` |

- Paneles y tarjetas redondeados (aproximadamente 12–22 px), con bordes finos y sombra o brillo suaves.
- Iconos sencillos y consistentes: ingresos 📥, pagos 💳, gastos 🛒, disponible 🐷, atención ⚠️.
- Tipografía sans serif. Valor principal destacado; nombre y explicación en tamaños menores.
- Evitar encabezados, métricas o leyendas repetidos. Mantener la información que ayude a leer el gráfico.
- Fondo oscuro continuo, colores vivos para datos relevantes y tonos atenuados para contexto.
- Respetar el significado: rojo para alertas o aumentos del gasto cuando corresponda; verde para disponibilidad o reducción, sin reinterpretar otras métricas automáticamente.

## Manómetros

- Arco semicircular limpio, aro de fondo y bisel sutil.
- Tramos de contexto atenuados, progreso de color definido y brillo discreto.
- Aguja y punto de lectura contrastantes, sin cruzarse con el valor.
- Valor digital dentro de una tarjeta oscura debajo del pivote; estado y referencia separados.
- Mostrar la referencia explícita. Conservar el 30 % solo donde el cálculo existente lo utilice; no trasladarlo a otros indicadores sin justificación.
- Escala adaptada a los datos, sin recortar valores mayores del máximo habitual. Ausencia de datos debe mostrarse como tal.

## Flujos y tarjetas

- Cintas suaves y proporcionales a los valores reales.
- Tarjetas integradas en el gráfico con icono, nombre, monto y porcentaje claramente referido al total correspondiente.
- Conservar todos los totales entre niveles. No sumar los enlaces de distintos niveles como si fueran dinero adicional.
- No inventar ingresos para cerrar déficits; identificar el faltante por financiar.

## Formato y comportamiento

- Pesos con puntos de miles: `$1.250.000`.
- Porcentajes con coma decimal, normalmente dos decimales en los indicadores: `12,50 %`.
- Tooltips compactos, alineados a la izquierda, con alto contraste e iconos sin duplicar. Nombre y valor en la misma línea cuando quepan.
- Ancho disponible completo. Altura proporcional, sin recorte ni desplazamiento interno.
- Evitar superposiciones entre títulos, etiquetas, valores y leyendas. Borrar anotaciones antiguas antes de sustituirlas en Plotly.
- Comprobar valores cero, falta de datos y cantidades altas, además del caso habitual.

## Alcance

Esta guía se guarda con el proyecto V20. Para usarla en otro chat o proyecto, adjuntar esta guía o indicar dónde está. No representa una plantilla instalada globalmente.
