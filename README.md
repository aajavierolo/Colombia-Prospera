# 🇨🇴 Colombia Prospera V26

### Tu información financiera, organizada en un solo lugar

Registra tus movimientos en una plantilla y consulta ingresos, gastos, presupuesto, deudas y patrimonio en un dashboard interactivo. Explora escenarios y prepara un informe PDF con los filtros seleccionados.

**[Abrir el aplicativo](https://colombia-prospera.streamlit.app/)** · **[Guardar mi plantilla en Drive](https://docs.google.com/spreadsheets/d/1_-RDFht7kevHbSBu57m_mydpx41dEcVcfzb1QVp35Dw/copy)**

---

## 🚀 Empieza en cuatro pasos

### 1. Guarda tu propia plantilla

Abre **Guardar mi plantilla en Drive**, inicia sesión en Google y selecciona **Hacer una copia**. Trabaja sobre esa copia: cada persona conserva su propio archivo.

También encontrarás el botón **Guardar plantilla en mi Drive** en la pantalla inicial del aplicativo.

### 2. Completa tu información

Conserva los nombres de las pestañas, los encabezados y las fórmulas. Escribe tus registros en las filas destinadas a los datos.

| Hoja | ¿Para qué sirve? |
| --- | --- |
| **Egresos** | Registrar gastos y pagos: fecha, valor, categoría y subcategoría. |
| **Ingresos** | Registrar dinero recibido: fecha, valor y fuente. |
| **Presupuesto_Mes** | Organizar categorías, conceptos y valores propuestos. |
| **Historico_presupuesto** | Conservar el presupuesto de cada mes. |
| **Patrimonio** | Registrar activos, valores y su clasificación. |
| **Pasivos** | Registrar créditos, saldos pendientes, tasas y condiciones. |
| **Metas** | Definir objetivos financieros y valores de referencia. |
| **Personales** | Completar tu perfil y los tiempos disponibles. |
| **Inversiones** | Organizar inversiones como registro de apoyo. La lectura de esta hoja independiente aún no está integrada al dashboard. |

La vista de inversiones del dashboard utiliza los activos clasificados en **Patrimonio**. Conserva la pestaña oculta **Mapeo**, que ayuda a los desplegables.

**Para comenzar:** configura el presupuesto, registra ingresos y egresos y completa las demás hojas según lo que necesites analizar. Utiliza fechas válidas y números en las columnas de valores.

### 3. Carga tus datos

Elige la opción que prefieras en la pantalla inicial:

| Opción | Cómo usarla |
| --- | --- |
| **Subir archivo Excel** | En Google Sheets, selecciona **Archivo → Descargar → Microsoft Excel (.xlsx)**. Sube ese archivo al aplicativo. No necesitas hacer pública tu hoja. |
| **Enlace público de Google** | En tu copia, entra en **Compartir → Acceso general → Cualquier persona con el enlace → Lector**. Pega el enlace en el aplicativo y pulsa **Cargar / actualizar datos**. También se admite un Excel público alojado en Drive. |

> **Tú eliges cómo compartir tu información.** Un enlace público permite que otras personas con ese enlace consulten el archivo. Si prefieres mantener privado tu Google Sheets, utiliza la carga de Excel.

El aplicativo lee tus datos. Los filtros y las simulaciones no modifican el archivo de origen. Después de cargarlo, el formulario inicial se oculta para dejar espacio al dashboard.

### 4. Explora el dashboard

Selecciona un período en el menú lateral: todo el historial, períodos rápidos o un rango **Personalizado**.

| Sección | ¿Qué puedes consultar? |
| --- | --- |
| **📈 Resumen** | Ingresos, gastos, balance, capacidad de ahorro y evolución general. |
| **🧾 Gastos** | Categorías, distribución y patrones de tus egresos. |
| **📅 Tendencias** | Comparaciones y proyecciones de ahorro e inversión. |
| **🎯 Presupuesto** | Lo propuesto frente a lo ejecutado, excesos y disponibilidad. |
| **💰 Ingresos** | Fuentes de ingreso y escenarios de reducción. |
| **💳 Deudas** | Obligaciones pendientes, prioridades y simulación de amortización. Las deudas con saldo cero se ocultan. |
| **🏠 Patrimonio** | Composición de activos, pasivos y patrimonio. |
| **😊 Felicidad** | Relación entre ingresos, trabajo, tiempo e indicadores personales. |

La vista **Básico** muestra el resumen. La vista **Avanzado** habilita las ocho secciones.

## 🔄 Tu rutina de actualización

1. Registra nuevos movimientos en tu Sheets o Excel.
2. En el aplicativo, pulsa **↻ Cambiar / actualizar datos** en el menú lateral.
3. Vuelve a cargar el enlace de Google o sube el Excel actualizado.
4. Selecciona el período que deseas revisar.

**Los cambios del Sheets no llegan en tiempo real:** vuelve a cargar los datos para verlos reflejados.

## 💳 Simula el pago de tus deudas

Actualiza el **saldo pendiente** y las condiciones de cada obligación en **Pasivos**. En el dashboard, las deudas con saldo positivo se priorizan por mayor tasa de interés y, en caso de empate, por mayor saldo.

Para registrar intereses, usa las columnas **F: Tasa ingresada** y **G: Tipo de tasa**. Escribe la tasa con el símbolo **%** y elige **NM (Nominal Mensual)** o **EA (Efectivo Anual)**. Por ejemplo, `24%` con tipo **EA** equivale aproximadamente a **1,81% mensual**; `2%` con tipo **NM** conserva ese valor mensual. Las columnas **H: interes NM** y **I: Interes EA** se calculan automáticamente: conserva sus fórmulas. Altium lee los encabezados, calcula la conversión al leer el archivo y sigue admitiendo las plantillas anteriores, incluidos los selectores Mensual, Nominal Mensual y Efectivo Anual.

Abre **Amortización** en la tarjeta del crédito para ver las opciones disponibles según sus datos. Puedes ajustar la cuota y los abonos extraordinarios y pulsar **Aplicar simulación** para comparar el resultado.

**La simulación no registra pagos reales ni cambia el saldo del Sheets.** Los intereses y tiempos proyectados son estimaciones a partir de los datos cargados.

## 📅 Activa el guardado mensual del presupuesto

La plantilla incluye una función para conservar los valores de **Propuesto** en **Historico_presupuesto**.

**Cada persona debe activarla una sola vez en su propia copia:**

1. Abre tu copia en Google Sheets desde un computador y recarga la página.
2. Selecciona **Presupuesto automático → Activar guardado mensual**.
3. Completa la autorización de Google para que el script trabaje en esa hoja y cree la programación.

Una vez activada, se programa para el **día 1 de cada mes, entre la 1:00 y las 2:00 a. m., hora de Colombia**, aunque la hoja esté cerrada.

- Crea la columna del mes y año si hace falta.
- Guarda números, sin copiar las fórmulas de Propuesto.
- Solo completa celdas realmente vacías: conserva los datos y las fórmulas existentes en la columna de destino.
- La activación no genera un registro inmediato del mes en curso.

**Al copiar la plantilla se conserva el código, pero no la programación automática.** Debes activarla en cada copia.

## 📄 Descarga tu informe

Selecciona los filtros y pulsa **📄 Preparar informe PDF**. Cuando termine, aparecerá **📄 Descargar informe PDF**. Algunas secciones también permiten descargar tablas en CSV.

Si cambias el archivo o los filtros, prepara de nuevo el PDF para obtener un informe actualizado.

## 💬 ¿Necesitas ayuda?

| Situación | Qué revisar |
| --- | --- |
| No carga el enlace | Comprueba la conexión, el permiso público de lectura y que se permita descargar el archivo. También puedes subir el `.xlsx`. |
| No aparecen movimientos | Revisa el período seleccionado, las fechas y los valores registrados. |
| Los datos siguen iguales | Pulsa **↻ Cambiar / actualizar datos** y carga nuevamente el enlace o archivo. |
| Falta una deuda | Verifica su nombre y saldo en **Pasivos**. Las deudas con saldo cero no aparecen. |
| Falta el menú de presupuesto automático | Recarga tu copia del Sheets desde un computador. Ese menú está en Google Sheets, no en el dashboard. |
| No se guarda el presupuesto automáticamente | Comprueba que activaste y autorizaste la función en esa copia. La tarea se ejecuta el día 1. |

**Limitación conocida:** la sección **Presupuesto** puede generar un error con una plantilla completamente vacía. Su corrección está pendiente.

---

## 🛠️ Para quien instala o publica el aplicativo

Si utilizas la versión web, puedes trabajar directamente desde el navegador. No necesitas instalar Python.

### Ejecutar en tu computador

Con **Python 3.12** instalado, abre una terminal dentro de la carpeta del proyecto y crea el entorno:

```bash
python -m venv .venv
```

En **Windows**:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

En **macOS o Linux**, utiliza `python3` al crear el entorno y ejecuta:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Abre la dirección que indique Streamlit. Mantén la terminal abierta mientras usas el aplicativo y pulsa **Ctrl+C** para detenerlo. Necesitas Internet para instalar las dependencias, leer enlaces de Google y consultar cotizaciones externas.

### Publicar en Streamlit Cloud

1. Sube **el contenido** de la carpeta preparada para Cloud a la raíz de GitHub.
2. Comprueba que `app.py` y `requirements.txt` estén directamente en la raíz, junto a `modules/`, `imagenes/` y `.streamlit/config.toml`.
3. Selecciona el repositorio, la rama y **app.py** como archivo principal en Streamlit Cloud.
4. Configura **Python 3.12** al crear el despliegue.

No subas archivos financieros personales, credenciales, registros ni `.venv`. La carga manual desde la web de GitHub no aplica automáticamente las exclusiones de `.gitignore`.

El aplicativo no requiere claves ni servicios de inteligencia artificial.
