import pandas as pd

BILLETES = [100000, 50000, 20000, 10000, 5000, 2000]
MONEDAS = [1000, 500, 200, 100, 50]

def calcular_monto_total(cantidades, valores):
    return sum(int(c or 0) * v for c, v in zip(cantidades, valores))

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingresos_nequi, nequi_total_dia, efectivo_en_casa, lista_pagos, lista_deudas):
    # 1. EFECTIVO FÍSICO
    efectivo_caja_fisico = calcular_monto_total(cant_billetes, BILLETES) + calcular_monto_total(cant_monedas, MONEDAS)
    
    # 2. CLASIFICACIÓN DE GASTOS (Con conversión segura)
    total_gastos = 0
    g_hoy, g_ayer, g_nequi = 0, 0, 0
    for pago in lista_pagos:
        try:
            # Convertimos primero a float y luego a int para evitar el ValueError
            valor_raw = pago.get('Valor')
            v = int(float(valor_raw)) if valor_raw is not None and valor_raw != "" else 0
        except (ValueError, TypeError):
            v = 0
            
        m = pago.get('Metodo', 'Efectivo hoy')
        total_gastos += v
        if m == "Efectivo hoy": g_hoy += v
        elif m == "Efectivo ayer": g_ayer += v
        elif m == "Nequi": g_nequi += v

    # 3. INGRESO EFECTIVO CALCULADO
    ingreso_efectivo_calculado = (efectivo_caja_fisico + g_hoy) - (int(float(base_inicial or 0)))
    
    # 4. VENTA TOTAL
    venta_total = ingreso_efectivo_calculado + (int(float(ingresos_nequi or 0)))
    
    # 5. FIADOS (Con conversión segura)
    total_fiado = 0
    for d in lista_deudas:
        try:
            monto_raw = d.get('Monto')
            total_fiado += int(float(monto_raw)) if monto_raw is not None and monto_raw != "" else 0
        except (ValueError, TypeError):
            continue

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
    if valor is None or valor == 0: 
        return "$0"
    return f"${int(valor):,.0f}"