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

def procesar_cierre(base_inicial, cant_billetes, cant_monedas, ingreso_nequi, lista_pagos):
    """
    Aplica toda la lógica contable del Excel.
    """
    # 1. Calcular efectivo físico contado
    total_billetes = calcular_monto_total(cant_billetes, BILLETES)
    total_monedas = calcular_monto_total(cant_monedas, MONEDAS)
    efectivo_en_caja = total_billetes + total_monedas
    
    # 2. Calcular Ingreso Real Efectivo 
    ingreso_efectivo = efectivo_en_caja - base_inicial
    
    # 3. Calcular Venta Total del Día
    venta_total = ingreso_efectivo + ingreso_nequi
    
    # 4. Calcular Total de Pagos/Gastos
    total_gastos = 0
    
    # 5. Clasificar pagos por método (opcional para análisis)
    pagos_efectivo = 0
    pagos_nequi = 0

    for pago in lista_pagos:
        valor = pago.get('Valor') if pago.get('Valor') is not None else 0
        metodo = pago.get('Metodo', 'Efectivo')

        total_gastos += valor
        if metodo == 'Efectivo':
            pagos_efectivo =+ valor
        else:
            pagos_nequi += valor

    return {
        "resumen": {
            "base_inicial": base_inicial,
            "efectivo_contado": efectivo_en_caja,
            "ingreso_efectivo": ingreso_efectivo,
            "ingreso_nequi": ingreso_nequi,
            "total_venta_dia": venta_total,
            "total_pagos": total_gastos
        },
        "desglose": {
            "billetes": dict(zip(BILLETES, cant_billetes)),
            "monedas": dict(zip(MONEDAS, cant_monedas))
        },
        "pagos_detalle": {
            "efectivo": pagos_efectivo,
            "nequi": pagos_nequi
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