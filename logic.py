import pandas as pd

BILLETES = [100000, 50000, 20000, 10000, 5000, 2000]
MONEDAS = [1000, 500, 200, 100, 50]

def calcular_monto_total(cantidades, valores):
    total = 0
    for cant, val in zip(cantidades, valores):
        total += (int(cant or 0) * val)
    return total

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas):
    # 1. EFECTIVO EN CAJA (Suma física de billetes y monedas)
    total_billetes = calcular_monto_total(cant_billetes, BILLETES)
    total_monedas = calcular_monto_total(cant_monedas, MONEDAS)
    efectivo_en_caja = total_billetes + total_monedas
    
    # 2. INGRESO EFECTIVO (Efectivo en Caja - Base Inicial)
    ingreso_efectivo = efectivo_en_caja - (base_inicial or 0)
    
    # 3. CÁLCULO DE FIADOS
    total_fiado = sum(int(d.get('Monto') or 0) for d in lista_deudas if d.get('Monto') is not None)
    
    # 4. VENTA TOTAL (Ingreso Efectivo + Ingresos Nequi + Fiados)
    venta_total = ingreso_efectivo + (ingresos_nequi or 0) + total_fiado
    
    # 5. Clasificación de Gastos 
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
        "efectivo_en_caja": efectivo_en_caja, 
        "ingreso_efectivo": ingreso_efectivo,
        "ingresos_nequi": ingresos_nequi,
        "nequi_total_dia": nequi_total_dia,
        "efectivo_en_casa": efectivo_en_casa,
        "total_fiado": total_fiado,
        "total_venta_dia": venta_total,
        "total_pagos": total_gastos,
        "gasto_hoy": g_hoy,
        "gasto_ayer": g_ayer,
        "gasto_nequi": g_nequi
    }

def formatear_moneda(valor):
    if valor is None or valor == 0:
        return "$0"
    return f"${int(valor):,.0f}"