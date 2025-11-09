"""
Utilidades de cálculos financieros
"""

import math


def compute_monthly_payment(
    principal: float,
    annual_rate: float,
    years: int
) -> float:
    """
    Calcula cuota mensual de hipoteca mediante sistema francés

    Args:
        principal: Capital prestado
        annual_rate: TIN anual en porcentaje (ej: 2.5 para 2.5%)
        years: Plazo en años

    Returns:
        Cuota mensual o 0.0 si error
    """
    try:
        principal = float(principal)
        annual_rate = float(annual_rate)
        years = int(years)
    except (ValueError, TypeError):
        return 0.0

    if principal <= 0:
        return 0.0

    n = years * 12
    r = (annual_rate / 100.0) / 12.0

    if r == 0:
        return round(principal / n, 2)

    factor = (1 + r) ** n
    denom = factor - 1

    if denom == 0:
        return 0.0

    monthly = principal * (r * factor) / denom
    monthly = float(monthly)

    if math.isnan(monthly) or math.isinf(monthly):
        return 0.0

    return round(monthly, 2)
