"""
Adaptador para integrar configuraciones paramétricas con el sistema de costes.
"""

from typing import Dict, Any

from .config_parametric import ParametricConfig


class ParametricModelAdapter:
    """Adapta una configuración paramétrica al formato de modelo esperado."""

    @staticmethod
    def to_model_dict(config: ParametricConfig) -> Dict[str, Any]:
        """
        Convierte ParametricConfig al formato de diccionario de modelo
        compatible con el sistema de costes existente.
        """
        return {
            "model_id": f"PARAM_{config.config_id}",
            "nombre": (
                f"Paramétrico {config.overall_shape.value} "
                f"{config.total_built_m2:.0f}m²"
            ),
            "numero_dormitorios": config.estimated_bedrooms,
            "numero_banos": config.estimated_bathrooms,
            "plantas": config.num_floors,
            "superficie_m2": config.total_built_m2,
            "huella_ancho_m": (
                config.ground_floor.envelope_width_m if config.ground_floor else 0
            ),
            "huella_largo_m": (
                config.ground_floor.envelope_length_m if config.ground_floor else 0
            ),
            "superficie_huella_m2": config.total_footprint_m2,
            "maqueta_ref_id": None,
            "_is_parametric": True,
            "_parametric_config": config,
        }
