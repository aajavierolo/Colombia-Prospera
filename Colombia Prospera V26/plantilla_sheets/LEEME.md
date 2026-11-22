# Datos: 15 categorias y 20 subcategorias por categoria

Edita solamente Datos para administrar el catalogo y el presupuesto. Mapeo es una vista automatica.

- Encabezados de categorias: A1, D1, G1, J1, M1; A24, D24, G24, J24, M24; A47, D47, G47, J47, M47.
- Cada bloque tiene 20 filas de subcategorias con su monto al lado. No sobrescribas la fila TOTAL.
- Los seis encabezados vacios son M24 y los cinco de la fila 47. Escribe el nombre de la categoria y despues sus subcategorias y montos.
- Las opciones de Transaccional se actualizan al editar Datos. Cambiar una categoria actualiza el desplegable de subcategorias de esa fila.
- Cambiar el nombre de una categoria actualiza sus movimientos y conceptos historicos. Renombrar una subcategoria en una sola celda conserva su relacion con movimientos e historico. Eliminar un concepto conserva sus meses anteriores y deja su propuesta vigente en cero.
- Ordena siempre concepto y monto juntos dentro del bloque. Los montos mensuales del historico no se reasignan por ordenar Datos.
- Espera unos segundos despues de editar para que finalice la sincronizacion.

Altium 24 lee los bloques sin limitarse a las categorias anteriores. Una subcategoria sin monto se considera presupuesto cero. Las graficas se conservan.

El script Codigo.gs esta instalado en el proyecto Apps Script vinculado a la hoja. La copia XLSX exportada sirve para importar en Altium; Apps Script se ejecuta en Google Sheets.

No se ha construido ni publicado una imagen Docker V26 con estos cambios.

## Espacios del historico

Historico_presupuesto tiene 15 bloques de 20 filas, correspondientes a los 15 bloques de Datos. Las filas 2:301 ofrecen 300 espacios. Las categorias adicionales ocupan 182:201, 202:221, 222:241, 242:261, 262:281 y 282:301. Los espacios se completan al agregar conceptos en Datos.

Los registros anteriores que ya no figuren en el catalogo se conservan debajo de los bloques. Las columnas de meses siguen siendo editables y se conservan por concepto. No agregues conceptos a mano en las filas reservadas: ingresa el catalogo en Datos. Altium ignora las reservas sin concepto y conserva sus graficas.

Verificado: al ingresar una subcategoria nueva en Datos, el historico utiliza una fila libre de su bloque; los valores mensuales anteriores permanecen ligados a cada concepto. La reserva del bloque 10 corresponde a Datos M24 y ya incluye la categoria creada por el usuario.

## Mes unico de ingresos

Transaccional usa J como mes automatico a partir de la fecha de K. La antigua N se elimino fisicamente. Categoria esta ahora en N, Horas en O y Valor Hora en P. Al editar o agregar una fecha en K, J se actualiza y queda vacia cuando no hay fecha.

Altium 24 busca primero el mes anterior a Fecha (J), conserva la lectura de N en archivos antiguos y usa la fecha si no hay mes. Se verificaron ingresos, horas y periodos antes y despues, sin cambiar funciones de graficos.

La lectura de Altium se hace por encabezados y conserva compatibilidad con archivos anteriores. Las formulas de Valor Hora y las listas de clasificacion se desplazan junto con sus columnas.

Tambien se reconectaron con J los resumenes de la hoja Ingresos que usaban el mes de la antigua N, para evitar referencias rotas tras eliminar la columna.

## Prioridad de los gastos

Datos tiene una columna Prioridad junto a cada monto: Basicos, Calidad de vida, Estilo de vida o Caprichosos. Al ordenar un bloque, incluye subcategoria, monto y prioridad.

Transaccional!I es Prioridad (opcional). Si tiene una opcion, esa se aplica solo al movimiento. Si queda vacia, Altium usa la prioridad de su categoria y subcategoria en Datos. Si ambas estan vacias se muestra Sin clasificar. No se han asignado prioridades personales automaticamente.

El total general de Datos se traslado de O19 a R19 para dejar espacio a la prioridad del quinto bloque. Altium conserva lectura de las plantillas anteriores.

En Altium, dentro del resumen, abre Prioridad de los gastos: Datos y excepciones por movimiento. Alli aparecen los totales, el detalle y el origen de la prioridad aplicada. Las graficas anteriores permanecen iguales. Exporta de nuevo el Excel desde Sheets y cargalo en Altium 24.

Pruebas: prioridad manual prevalece, campo opcional vacio vuelve a Datos, campos vacios muestran Sin clasificar, importes y presupuestos conservados, y compatibilidad con archivos antiguos.

## Propuesta inicial para revisar

Se completaron las prioridades de las 81 subcategorias presentes al momento de la propuesta: 53 Basicos, 19 Calidad de vida, 7 Estilo de vida y 2 Caprichosos. Las cuotas y obligaciones se propusieron como Basicos; bienestar como Calidad de vida; ocio planificado como Estilo de vida; Lujos y Gastos Hormiga como Caprichosos.

Revisa especialmente Otros, nombres personales, cadenas/fondos y conceptos mixtos como Internet/Netflix. Es una propuesta inicial que puedes cambiar o vaciar. La asignacion se hace una sola vez y no vuelve a llenar campos que borres despues. Las elecciones de Transaccional se conservan.

## Separadores visuales en Datos

Se agregaron columnas separadoras D, H, L y P. Los cinco bloques de cada fila empiezan en A, E, I, M y Q, con Subcategoria, Monto y Prioridad. Los encabezados siguen en filas 1, 24 y 47. El total general esta en V19. Las lecturas de presupuesto y prioridades buscan los encabezados, manteniendo compatibilidad con el formato sin separadores.

## Accion de control

Datos agrega Accion de control junto a Prioridad, con Mantener, Reducir o Eliminar. Los bloques empiezan ahora en A, F, K, P y U; conservan una columna separadora. El total general esta en AA19.

Transaccional!Q es Accion de control (opcional), aplicada al gasto de esa fila. Si esta vacia, se usa Datos. Si ambas estan vacias, Altium muestra Sin accion. Las prioridades opcionales permanecen en I.

En el resumen de Altium se agrego Acciones de control: mantener, reducir o eliminar, con importes registrados, movimientos y origen de la accion. Es un plan de control, no una reduccion automatica del gasto ni ahorro ya realizado. No se asignan acciones personales automaticamente.

## Orden de columnas de Datos

Cada bloque queda Categoria/Subcategoria, Prioridad, Monto y Accion de control. Se conservan los separadores E, J, O y T. El presupuesto total sigue en AA19. Las lecturas reconocen tanto este orden como los anteriores.

Transaccional actualizado: I Prioridad opcional, J Accion de control opcional. Ingresos desplazados a K:Q (K mes, L fecha, M valor, N empresa, O categoria, P horas, Q valor hora). La automatizacion de mes usa L y escribe K. Altium detecta ingresos y control por encabezados.

Separacion egresos e ingresos: K vacia (30 px). Ingresos L:R: L mes, M fecha, N valor, O empresa, P categoria, Q horas, R valor hora. Mes automatico desde M hacia L. Lecturas por encabezado verificadas con ambos formatos.

Fondos trasladados de CREDITOS a AHORROS: Fondo amigos y Fondo de emergencia. Se preservan presupuesto, prioridad, control y montos historicos; movimientos E:F actualizados. Historico usa reservas del bloque 10.

Transporte publico: Buses y Taxis desde CARRO, didi picap desde MOTO trasladados a Buses, Taxi y Picap. Se fusionaron presupuestos y meses historicos con las filas ya existentes de TRANSPORTE PUBLICO, sin duplicados. Se mantienen prioridades elegidas en destino. 19 movimientos actualizados.

Categoria HIJOS renombrada a FAMILIA Y DEPENDIENTES en Datos, Mapeo, Transaccional e Historico_presupuesto. Subcategorias y montos conservados; desplegables sincronizados.

Nombres familiares aclarados: Cuidado de Alejo — Zoraida; Onces de Mafe — Aldemar; Transporte y gastos personales de Dani; Gastos adicionales de Mafe; Gastos adicionales de Alejo. Sincronizados Datos, Mapeo, Transaccional e Historico_presupuesto conservando montos y clasificaciones.

CARRO y MOTO: Parqueadero mensual; Parqueadero diario y diligencias; Imprevistos del vehiculo; Multas de transito; Otros gastos del vehiculo. Presupuesto mixto previo conservado en Otros, nuevos conceptos en cero. Lavada del carro reclasificada a Aseo carro; dudosos en Otros. Historico y montos totales conservados.

Papeles y Accesorios creados en CARRO y MOTO, presupuesto inicial cero. Transaccional: fila499 CARRO/Papeles, fila582 MOTO/Papeles, fila605 MOTO/Accesorios. Sincronizados Mapeo, Historico_presupuesto y desplegables; montos originales conservados.

GASTOS PERSONALES creado en bloque12 de Datos (F47). Vestuario y calzado y Cuidado personal trasladados desde GUSTOS con presupuestos 100000 y 20000, prioridades y controles conservados. Tecnologia nueva en cero. Siete movimientos reclasificados; historico D:J trasladado sin alterar montos, Mapeo y listas sincronizados.

Datos compactado dentro de cada bloque: conceptos juntos arriba, espacios disponibles al final. Se conservan orden, prioridad, monto, control y notas; 20 filas por categoria, encabezados, totales y separadores intactos. Mapeo sincronizado; historico y Transaccional sin cambios de valores; lectura Altium verificada identica.
