import pandas as pd

# Denominaciones de Colombia
BILLETES = [100000, 50000, 20000, 10000, 5000, 2000]
MONEDAS = [1000, 500, 200, 100, 50]

def calcular_monto_total(cantidades, valores):
    """Suma el valor total de billetes o monedas"""
    return sum(int(c or 0) * v for c, v in zip(cantidades, valores))

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingreso_efectivo_manual, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas):
    # 1. EFECTIVO EN CAJA (Suma física de billetes y monedas para auditoría)
    efectivo_caja_fisico = calcular_monto_total(cant_billetes, BILLETES) + calcular_monto_total(cant_monedas, MONEDAS)
    
    # 2. VENTA TOTAL (Según tu nueva regla: Efectivo Manual + Nequi Manual)
    venta_total = (ingreso_efectivo_manual or 0) + (ingresos_nequi or 0)
    
    # 3. Cálculo de Fiados (Informativo, NO suma a venta total)
    total_fiado = sum(int(d.get('Monto') or 0) for d in lista_deudas if d.get('Monto') is not None)
    
    # 4. Clasificación de Gastos
    total_gastos = 0
    g_hoy, g_ayer, g_nequi = 0, 0, 0
    for pago in lista_pagos:
        v = int(pago.get('Valor') or 0)
        m = pago.get('Metodo', 'Efectivo hoy')
        total_gastos += v
        if m == "Efectivo hoy": g_hoy += v
        elif m == "Efectivo ayer": g_ayer += v
        elif m == "Nequi": g_nequi += v

    return {
        "base_inicial": base_inicial,
        "efectivo_caja": efectivo_caja_fisico,
        "ingreso_efectivo": ingreso_efectivo_manual,
        "ingresos_nequi": ingresos_nequi,
        "venta_total": venta_total,
        "total_fiado": total_fiado,
        "total_pagos": total_gastos,
        "gasto_hoy": g_hoy,
        "gasto_ayer": g_ayer,
        "gasto_nequi": g_nequi,
        "nequi_total_dia": nequi_total_dia,
        "efectivo_en_casa": efectivo_en_casa
    }

def formatear_moneda(valor):
    if valor is None or valor == 0: return "$0"
    return f"${int(valor):,.0f}"