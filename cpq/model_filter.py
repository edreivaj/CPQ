"""
Filtrado y selección de modelos de casas
"""

from typing import List
from .config import CFG
from .models import MODELS_DATABASE


def filter_valid_models(
    num_bedrooms: int,
    parcel_area_m2: float,
    buildable_area_m2: float
) -> List[dict]:
    """
    Filtra modelos válidos según criterios urbanísticos

    Args:
        num_bedrooms: Número de dormitorios deseado
        parcel_area_m2: Área de la parcela
        buildable_area_m2: Área de la caja edificable

    Returns:
        Lista de modelos válidos con superficie_huella_m2 añadida
    """
    print("\n" + "="*60)
    print("--- Pre-Filtrado Inteligente (RF-1.1.d) ---")

    # Filtrar por dormitorios
    models_by_bedrooms = [
        m for m in MODELS_DATABASE
        if m['numero_dormitorios'] == num_bedrooms
    ]

    if not models_by_bedrooms:
        print(f"Error: No hay modelos de {num_bedrooms} dormitorios")
        return []

    print(f"Encontrados {len(models_by_bedrooms)} modelos de {num_bedrooms} dormitorios")

    # Calcular límites
    parking_area = CFG.PARKING_ANCHO_M * CFG.PARKING_LARGO_M
    max_edif = parcel_area_m2 * CFG.EDIFICABILIDAD_M2T_M2S
    max_ocup = parcel_area_m2 * (CFG.OCUPACION_PORCENTAJE / 100.0)

    print(f"\nDatos de Parcela:")
    print(f"  -> Superficie: {parcel_area_m2:,.2f} m²")
    print(f"  -> Max Edificabilidad: {max_edif:,.2f} m²t")
    print(f"  -> Max Ocupación: {max_ocup:,.2f} m²")
    print(f"  -> Área Caja Edificable: {buildable_area_m2:,.2f} m²")
    print(f"  -> Parking (reserva): {parking_area:.2f} m²")

    # Filtrar por normativa
    valid_models = []

    for m in models_by_bedrooms:
        m_copy = m.copy()
        m_copy['superficie_huella_m2'] = round(
            m['huella_ancho_m'] * m['huella_largo_m'], 2
        )

        m2t = m['superficie_m2']
        huella = m_copy['superficie_huella_m2']

        # Criterio A: Edificabilidad
        pass_A = m2t <= max_edif

        # Criterio B: Ocupación
        ocup_req = huella + parking_area
        pass_B = ocup_req <= max_ocup

        # Criterio C: Caja edificable
        area_req = huella + parking_area
        pass_C = area_req <= buildable_area_m2

        if pass_A and pass_B and pass_C:
            valid_models.append(m_copy)

    print(f"\nModelos válidos después de filtrado: {len(valid_models)}")

    return valid_models
