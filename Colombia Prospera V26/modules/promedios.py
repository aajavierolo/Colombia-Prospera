"""Promedios de gasto sobre el intervalo calendario seleccionado."""
from calendar import monthrange
from datetime import timedelta


def calcular_promedios_gasto(total, desde, hasta):
    if hasta < desde:
        raise ValueError("La fecha final no puede ser anterior a la inicial.")
    dias = (hasta - desde).days + 1
    meses = 0.0
    cursor = desde
    while cursor <= hasta:
        dias_mes = monthrange(cursor.year, cursor.month)[1]
        fin_mes = cursor.replace(day=dias_mes)
        fin_tramo = min(fin_mes, hasta)
        meses += ((fin_tramo - cursor).days + 1) / dias_mes
        cursor = fin_tramo + timedelta(days=1)
    diario = float(total) / dias
    return diario, diario * 7, float(total) / meses, dias, meses
