import pandas as pd

BILLETES = [100000, 50000, 20000, 10000, 5000, 2000]
MONEDAS = [1000, 500, 200, 100, 50]

def calcular_monto_total(cantidades, valores):
    return sum(int(c or 0) * v for c, v in zip(cantidades, valores))

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas):
    # 1. EFECTIVO FÍSICO (Lo que hay en el cajón)
    efectivo_caja_fisico = calcular_monto_total(cant_billetes, BILLETES) + calcular_monto_total(cant_monedas, MONEDAS)
    
    # 2. CLASIFICACIÓN DE GASTOS
    total_gastos = 0
    g_hoy, g_ayer, g_nequi = 0, 0, 0
    for pago in lista_pagos:
        v = int(pago.get('Valor') or 0)
        m = pago.get('Metodo', 'Efectivo hoy')
        total_gastos += v
        if m == "Efectivo hoy": g_hoy += v
        elif m == "Efectivo ayer": g_ayer += v
        elif m == "Nequi": g_nequi += v

    # 3. INGRESO EFECTIVO CALCULADO (Fórmula solicitada)
    # Venta Efectivo = (Dinero en caja + Gastos pagados con ese dinero) - Base inicial
    ingreso_efectivo_calculado = (efectivo_caja_fisico + g_hoy) - (base_inicial or 0)
    
    # 4. VENTA TOTAL (Efectivo Calculado + Nequi Manual)
    venta_total = ingreso_efectivo_calculado + (ingresos_nequi or 0)
    
    # 5. FIADOS (Informativo)
    total_fiado = sum(int(d.get('Monto') or 0) for d in lista_deudas if d.get('Monto') is not None)

    return {
        "base_inicial": base_inicial,
        "efectivo_caja": efectivo_caja_fisico,
        "gasto_hoy": g_hoy,
        "gasto_ayer": g_ayer,
        "gasto_nequi": g_nequi,
        "ingreso_efectivo": ingreso_efectivo_calculado,
        "ingresos_nequi": ingresos_nequi,
        "venta_total": venta_total,
        "total_fiado": total_fiado,
        "total_pagos": total_gastos,
        "nequi_total_dia": nequi_total_dia,
        "efectivo_en_casa": efectivo_en_casa
    }

def formatear_moneda(valor):
    if valor is None or valor == 0: return "$0"
    return f"${int(valor):,.0f}"