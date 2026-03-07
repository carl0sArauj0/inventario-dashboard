import pandas as pd

# Definición de denominaciones constantes 
BILLETES = [100000, 50000, 20000, 10000, 5000, 2000]
MONEDAS = [1000, 500, 200, 100, 50]

def calcular_monto_total(cantidades, valores):
    """
    Suma el valor total multiplicando cada cantidad por su denominación.
    cantidades: lista de enteros
    valores: lista de denominaciones (BILLETES o MONEDAS)
    """
    total = 0
    for cant, val in zip(cantidades, valores):
        total += (cant * val)
    return total

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, nequi_total_dia, efectivo_en_casa, lista_pagos):
    # Cálculos de efectivo contado e ingreso efectivo 
    total_billetes = calcular_monto_total(cant_billetes, BILLETES)
    total_monedas = calcular_monto_total(cant_monedas, MONEDAS)
    efectivo_en_caja = total_billetes + total_monedas
    ingreso_efectivo = efectivo_en_caja - base_inicial
    venta_total = ingreso_efectivo + (nequi_total_dia or 0)
    
    # --- LÓGICA DE DESGLOSE DE GASTOS ---
    total_gastos = 0
    gasto_efectivo_hoy = 0
    gasto_efectivo_ayer = 0
    gasto_nequi = 0
    
    for pago in lista_pagos:
        v = pago.get('Valor') if pago.get('Valor') is not None else 0
        m = pago.get('Metodo', 'Efectivo hoy')
        
        total_gastos += v
        if m == "Efectivo hoy":
            gasto_efectivo_hoy += v
        elif m == "Efectivo ayer":
            gasto_efectivo_ayer += v
        elif m == "Nequi":
            gasto_nequi += v

    return {
        "resumen": {
            "base_inicial": base_inicial,
            "efectivo_contado": efectivo_en_caja,
            "ingreso_efectivo": ingreso_efectivo,
            "nequi_total_dia": nequi_total_dia,
            "efectivo_en_casa": efectivo_en_casa,
            "total_venta_dia": venta_total,
            "total_pagos": total_gastos,
            "desglose_gastos": {
                "hoy": gasto_efectivo_hoy,
                "ayer": gasto_efectivo_ayer,
                "nequi": gasto_nequi
            }
        }
    }

def formatear_moneda(valor):
    """Devuelve el valor en formato moneda legible"""
    return f"${valor:,.0f}"

def calcular_analisis_mensual(df):
    """
    Recibe un DataFrame de Pandas y calcula promedios y totales.
    """
    if df.empty:
        return None
        
    resumen = {
        "Venta Total Mes": df['total_venta_dia'].sum(),
        "Promedio Venta Diaria": df['total_venta_dia'].mean(),
        "Día de Mayor Venta": df.loc[df['total_venta_dia'].idxmax()]['fecha'],
        "Total Efectivo": df['ingreso_efectivo'].sum(),
        "Total Nequi": df['ingreso_nequi'].sum()
    }
    return resumen