"""Tiempo de devengo de intereses; meses vencidos para obligaciones inglesas."""
import pandas as pd
import unicodedata


def meses_interes(inicio, corte, sistema=None):
    inicio = pd.to_datetime(inicio, errors='coerce')
    corte = pd.to_datetime(corte, errors='coerce')
    if pd.isna(inicio) or pd.isna(corte) or corte < inicio:
        return 0.0
    etiqueta = '' if sistema is None or pd.isna(sistema) else ''.join(
        c for c in unicodedata.normalize('NFD', str(sistema).strip().lower())
        if unicodedata.category(c) != 'Mn')
    if etiqueta not in {'ingles', 'inglesa', 'sistema ingles', 'americano', 'americana'}:
        return max(0, (corte.normalize() - inicio.normalize()).days) / 30.4375
    meses = (corte.year - inicio.year) * 12 + corte.month - inicio.month
    aniversario = inicio.normalize() + pd.DateOffset(months=meses)
    if corte.normalize() < aniversario:
        meses -= 1
    return float(max(0, meses))
