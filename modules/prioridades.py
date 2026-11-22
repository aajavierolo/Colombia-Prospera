"""Prioridad del movimiento: Transaccional prevalece sobre Presupuesto_Mes."""
import unicodedata

import pandas as pd

PRIORIDADES = ["Básicos", "Calidad de vida", "Estilo de vida", "Caprichosos"]


def clave(valor):
    if pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFD", str(valor).strip().upper())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def prioridad_valida(valor):
    return {clave(p): p for p in PRIORIDADES}.get(clave(valor), "")


def catalogo_prioridades(datos):
    catalogo = {}
    if datos is None or datos.empty:
        return catalogo
    for r in range(len(datos)):
        for c in range(0, datos.shape[1] - 2):
            if not clave(datos.iat[r,c]) or clave(datos.iat[r,c]) in {"MONTO","PRIORIDAD","ACCION DE CONTROL"}:
                continue
            campos = {clave(datos.iat[r,k]): k for k in range(c+1,min(c+4,datos.shape[1]))}
            if "MONTO" not in campos or "PRIORIDAD" not in campos:
                continue
            prioridad_col = campos["PRIORIDAD"]
            categoria = clave(datos.iat[r, c])
            for fila in range(r + 1, len(datos)):
                sub = clave(datos.iat[fila, c])
                if sub == "TOTAL":
                    break
                if sub:
                    valor = datos.iat[fila, prioridad_col]
                    catalogo[(categoria, sub)] = "" if pd.isna(valor) else str(valor).strip()
    return catalogo


def aplicar_prioridades(gastos, datos, transaccional):
    resultado = gastos.copy()
    catalogo = catalogo_prioridades(datos)
    opciones = {"PRIORIDAD", "PRIORIDAD (OPCIONAL)", "PRIORIDAD OPCIONAL"}
    columna = next((c for c in transaccional.columns if clave(c) in opciones), None)
    manuales = (transaccional[columna].reindex(resultado.index) if columna is not None
                else pd.Series("", index=resultado.index, dtype=object))
    defaults, overrides, aplicadas, origenes = [], [], [], []
    for indice, fila in resultado.iterrows():
        predeterminada = catalogo.get((clave(fila.get("GASTOS_CATEGORIA")),
                                      clave(fila.get("GASTOS_SUBCATEGORIA"))), "")
        manual = manuales.loc[indice]
        manual = "" if pd.isna(manual) else str(manual).strip()
        defaults.append(predeterminada)
        overrides.append(manual)
        if manual:
            aplicada = prioridad_valida(manual)
            origen = "Transaccional" if aplicada else "Revisar Transaccional"
        else:
            aplicada = prioridad_valida(predeterminada)
            origen = "Presupuesto_Mes" if aplicada else ("Revisar Presupuesto_Mes" if predeterminada else "Sin clasificar")
        aplicadas.append(aplicada or "Sin clasificar")
        origenes.append(origen)
    resultado["PRIORIDAD_DATOS"] = defaults
    resultado["PRIORIDAD_MANUAL"] = overrides
    resultado["PRIORIDAD_GASTO"] = aplicadas
    resultado["ORIGEN_PRIORIDAD"] = origenes
    return aplicar_control(resultado, datos, transaccional)


ACCIONES = ["Mantener", "Reducir", "Eliminar"]


def aplicar_control(gastos, datos, transaccional):
    resultado = gastos.copy()
    catalogo = {}
    if datos is not None and not datos.empty:
        for r in range(len(datos)):
            for c in range(datos.shape[1] - 3):
                if not clave(datos.iat[r,c]) or clave(datos.iat[r,c]) in {"MONTO","PRIORIDAD","ACCION DE CONTROL"} or "MONTO" not in {clave(datos.iat[r,c+1]),clave(datos.iat[r,c+2])} or clave(datos.iat[r,c+3]) != "ACCION DE CONTROL":
                    continue
                categoria = clave(datos.iat[r,c])
                for fila in range(r+1,len(datos)):
                    sub = clave(datos.iat[fila,c])
                    if sub == "TOTAL":
                        break
                    if sub:
                        valor = datos.iat[fila,c+3]
                        catalogo[(categoria,sub)] = "" if pd.isna(valor) else str(valor).strip()
    columna = next((c for c in transaccional.columns if clave(c) in {"ACCION DE CONTROL", "ACCION DE CONTROL (OPCIONAL)"}), None)
    manuales = transaccional[columna].reindex(resultado.index) if columna is not None else pd.Series("",index=resultado.index,dtype=object)
    validas = {clave(x):x for x in ACCIONES}
    defaults, overrides, aplicadas, origenes = [], [], [], []
    for indice, fila in resultado.iterrows():
        default = catalogo.get((clave(fila.get("GASTOS_CATEGORIA")),clave(fila.get("GASTOS_SUBCATEGORIA"))),"")
        manual = manuales.loc[indice]
        manual = "" if pd.isna(manual) else str(manual).strip()
        valor = manual or default
        aplicada = validas.get(clave(valor),"")
        origen = ("Transaccional" if manual else "Presupuesto_Mes") if aplicada else ("Revisar Transaccional" if manual else "Revisar Presupuesto_Mes" if default else "Sin acción")
        defaults.append(default);overrides.append(manual);aplicadas.append(aplicada or "Sin acción");origenes.append(origen)
    resultado["CONTROL_DATOS"] = defaults
    resultado["CONTROL_MANUAL"] = overrides
    resultado["ACCION_CONTROL"] = aplicadas
    resultado["ORIGEN_CONTROL"] = origenes
    return resultado
