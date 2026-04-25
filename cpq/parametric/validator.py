"""
Validador de configuraciones paramétricas.
"""

from typing import Tuple, List

from .config_parametric import (
    ShapeType,
    FloorConfig,
    ParametricConfig,
    ParametricLimits,
    TechnicalConstraints,
)


class ParametricValidator:
    """Valida configuraciones paramétricas."""

    def __init__(self, constraints: TechnicalConstraints = None):
        self.constraints = constraints or TechnicalConstraints()

    def validate_config(
        self,
        config: ParametricConfig,
        limits: ParametricLimits,
    ) -> Tuple[bool, List[str]]:
        """
        Valida una configuración paramétrica completa.

        Returns:
            Tuple (es_válida, lista_errores)
        """
        errors = []

        if config.total_footprint_m2 > limits.max_footprint_m2:
            errors.append(
                f"Ocupación {config.total_footprint_m2:.1f}m² excede "
                f"máximo {limits.max_footprint_m2:.1f}m²"
            )

        if config.total_built_m2 > limits.max_built_area_m2:
            errors.append(
                f"Edificabilidad {config.total_built_m2:.1f}m² excede "
                f"máximo {limits.max_built_area_m2:.1f}m²"
            )

        if config.ground_floor and config.ground_floor.geometry:
            if not limits.buildable_box.buffer(0.1).contains(
                config.ground_floor.geometry
            ):
                errors.append("La huella de PB no cabe en la caja edificable")

        errors.extend(self._validate_technical(config))
        errors.extend(self._validate_proportions(config))

        if config.num_floors > 1:
            errors.extend(self._validate_staircase(config))

        is_valid = len(errors) == 0
        return is_valid, errors

    def _validate_technical(self, config: ParametricConfig) -> List[str]:
        """Valida restricciones técnicas mínimas."""
        errors = []

        for floor in [config.ground_floor, config.first_floor]:
            if floor is None:
                continue

            if floor.shape in [ShapeType.L_SHAPE, ShapeType.U_SHAPE]:
                if (
                    floor.wing_a_width_m
                    and floor.wing_a_width_m < self.constraints.min_wing_width_m
                ):
                    errors.append(
                        f"Ala A en P{floor.floor_number} muy estrecha: "
                        f"{floor.wing_a_width_m:.1f}m < "
                        f"{self.constraints.min_wing_width_m}m mínimo"
                    )

                if (
                    floor.wing_b_width_m
                    and floor.wing_b_width_m < self.constraints.min_wing_width_m
                ):
                    errors.append(
                        f"Ala B en P{floor.floor_number} muy estrecha: "
                        f"{floor.wing_b_width_m:.1f}m < "
                        f"{self.constraints.min_wing_width_m}m mínimo"
                    )

            if floor.shape in [ShapeType.BAR, ShapeType.I_SHAPE]:
                if floor.envelope_width_m < self.constraints.min_wing_width_m:
                    errors.append(
                        f"Ancho de P{floor.floor_number} insuficiente: "
                        f"{floor.envelope_width_m:.1f}m"
                    )

        return errors

    def _validate_proportions(self, config: ParametricConfig) -> List[str]:
        """Valida proporciones razonables."""
        errors = []

        for floor in [config.ground_floor, config.first_floor]:
            if floor is None:
                continue

            w = floor.envelope_width_m
            l = floor.envelope_length_m

            if w > 0 and l > 0:
                ratio = max(w, l) / min(w, l)

                if ratio > self.constraints.max_aspect_ratio:
                    errors.append(
                        f"P{floor.floor_number} demasiado alargada: "
                        f"proporción {ratio:.1f} > {self.constraints.max_aspect_ratio}"
                    )

        return errors

    def _validate_staircase(self, config: ParametricConfig) -> List[str]:
        """Valida espacio para escalera en viviendas de 2 plantas."""
        errors = []

        stair_area = (
            self.constraints.min_stair_width_m * self.constraints.min_stair_length_m
        )

        if config.ground_floor:
            pb_area = config.ground_floor.area_m2

            min_usable_pb = (
                self.constraints.min_living_m2
                + self.constraints.min_kitchen_m2
                + self.constraints.min_bathroom_m2
                + stair_area
            )

            if pb_area < min_usable_pb:
                errors.append(
                    f"PB ({pb_area:.1f}m²) insuficiente para programa mínimo "
                    f"con escalera ({min_usable_pb:.1f}m² requeridos)"
                )

        return errors


class ProgramEstimator:
    """Estima el programa funcional basado en superficie."""

    def __init__(self, constraints: TechnicalConstraints = None):
        self.constraints = constraints or TechnicalConstraints()
        self.m2_per_bedroom = 25.0
        self.bedrooms_per_bathroom = 2

    def estimate_program(
        self,
        total_m2: float,
        num_floors: int = 2,
    ) -> Tuple[int, int]:
        """
        Estima programa funcional basado en superficie total.

        Returns:
            Tuple (dormitorios, baños)
        """
        circulation_factor = 0.15 if num_floors == 1 else 0.20
        stair_deduction = 0 if num_floors == 1 else 6.0

        usable_m2 = total_m2 * (1 - circulation_factor) - stair_deduction

        common_areas = (
            self.constraints.min_living_m2
            + self.constraints.min_kitchen_m2
            + self.constraints.min_bathroom_m2
        )

        area_for_bedrooms = usable_m2 - common_areas

        if area_for_bedrooms <= 0:
            bedrooms = 1
        else:
            bedrooms = max(1, int(area_for_bedrooms / 15.0))

        bedrooms = min(bedrooms, 6)
        bathrooms = max(1, (bedrooms + 1) // self.bedrooms_per_bathroom)

        return bedrooms, bathrooms
