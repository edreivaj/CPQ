"""
Interfaz CLI para el modo paramétrico.
"""

from typing import Tuple

from .parametric.config_parametric import (
    ParametricConfig,
    ParametricLimits,
    ShapeType,
)


def select_mode() -> str:
    """
    Permite al usuario elegir entre modo catálogo y paramétrico.

    Returns:
        "catalog" o "parametric"
    """
    print("\n" + "=" * 60)
    print("MODO DE CONFIGURACIÓN")
    print("=" * 60)
    print("  [1] Catálogo - Seleccionar modelo predefinido")
    print("  [2] Paramétrico - Diseñar configuración a medida")

    while True:
        choice = input("\nSelecciona modo [1/2]: ").strip()
        if choice == "1":
            return "catalog"
        elif choice == "2":
            return "parametric"
        print("Opción no válida.")


def display_parametric_limits(limits: ParametricLimits) -> None:
    """Muestra los límites calculados al usuario."""
    print("\n" + "=" * 60)
    print("LÍMITES MÁXIMOS CALCULADOS")
    print("=" * 60)

    print(f"\nParcela: {limits.parcel_area_m2:,.2f} m²")
    print(f"Caja edificable: {limits.buildable_area_m2:,.2f} m²")
    print(f"  - Dimensiones: {limits.box_width_m:.1f}m x {limits.box_length_m:.1f}m")

    print(f"\nLímites urbanísticos:")
    print(f"  - Máx. ocupación (huella): {limits.max_footprint_m2:,.2f} m²")
    print(f"  - Máx. edificabilidad (total): {limits.max_built_area_m2:,.2f} m²")

    print(f"\nSugerencia óptima (2 plantas):")
    print(f"  - Planta Baja: {limits.suggested_pb_m2:,.2f} m²")
    print(f"  - Planta Primera: {limits.suggested_p1_m2:,.2f} m²")
    print(f"  - Forma recomendada: {limits.suggested_shape.value}")
    print(
        f"  - Total construido: "
        f"{limits.suggested_pb_m2 + limits.suggested_p1_m2:,.2f} m²"
    )


def display_parametric_config(config: ParametricConfig) -> None:
    """Muestra la configuración paramétrica al usuario."""
    print("\n" + "-" * 60)
    print("CONFIGURACIÓN PARAMÉTRICA")
    print("-" * 60)

    print(f"\nForma: {config.overall_shape.value}")
    print(f"Plantas: {config.num_floors}")

    if config.ground_floor:
        print(f"\nPlanta Baja:")
        print(f"  - Superficie: {config.ground_floor.area_m2:,.2f} m²")
        print(
            f"  - Dimensiones envolvente: "
            f"{config.ground_floor.envelope_width_m:.1f}m x "
            f"{config.ground_floor.envelope_length_m:.1f}m"
        )

    if config.first_floor:
        print(f"\nPlanta Primera:")
        print(f"  - Superficie: {config.first_floor.area_m2:,.2f} m²")
        print(
            f"  - Dimensiones envolvente: "
            f"{config.first_floor.envelope_width_m:.1f}m x "
            f"{config.first_floor.envelope_length_m:.1f}m"
        )

    print(f"\nTotales:")
    print(f"  - Huella (ocupación): {config.total_footprint_m2:,.2f} m²")
    print(f"  - Superficie construida: {config.total_built_m2:,.2f} m²")

    print(f"\nPrograma estimado:")
    print(f"  - Dormitorios: {config.estimated_bedrooms}")
    print(f"  - Baños: {config.estimated_bathrooms}")

    if config.is_valid:
        print(f"\n[OK] Configuración VÁLIDA")
    else:
        print(f"\n[!] Configuración con errores:")
        for err in config.validation_errors:
            print(f"    - {err}")


def get_parametric_input(limits: ParametricLimits) -> Tuple[float, float, ShapeType]:
    """
    Solicita al usuario los parámetros de la configuración.

    Returns:
        Tuple (pb_m2, p1_m2, shape)
    """
    print("\n" + "=" * 60)
    print("CONFIGURACIÓN PERSONALIZADA")
    print("=" * 60)

    print(f"\nSuperficie Planta Baja (máx {limits.max_footprint_m2:.1f} m²):")
    while True:
        try:
            pb_input = input("  PB m²: ").strip().replace(",", ".")
            pb_m2 = float(pb_input)
            if 0 < pb_m2 <= limits.max_footprint_m2:
                break
            print(f"  Debe estar entre 1 y {limits.max_footprint_m2:.1f}")
        except ValueError:
            print("  Valor numérico requerido")

    max_p1 = min(pb_m2, limits.max_built_area_m2 - pb_m2)
    print(f"\nSuperficie Planta Primera (máx {max_p1:.1f} m², 0 para 1 planta):")
    while True:
        try:
            p1_input = input("  P1 m²: ").strip().replace(",", ".")
            p1_m2 = float(p1_input)
            if 0 <= p1_m2 <= max_p1:
                break
            print(f"  Debe estar entre 0 y {max_p1:.1f}")
        except ValueError:
            print("  Valor numérico requerido")

    print("\nForma de planta:")
    print("  [1] _ (Barra rectangular)")
    print("  [2] I (Rectangular alargada)")
    print("  [3] L (Forma en L)")
    print("  [4] U (Forma en U)")

    shape_map = {
        "1": ShapeType.BAR,
        "2": ShapeType.I_SHAPE,
        "3": ShapeType.L_SHAPE,
        "4": ShapeType.U_SHAPE,
    }

    while True:
        choice = input("  Forma [1-4]: ").strip()
        if choice in shape_map:
            shape = shape_map[choice]
            break
        print("  Opción no válida")

    return pb_m2, p1_m2, shape


def confirm_use_suggested() -> bool:
    """Pregunta si usar la configuración sugerida."""
    while True:
        choice = input("\n¿Usar configuración sugerida? [S/n]: ").strip().lower()
        if choice in ("", "s", "si", "y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        print("Responde S o N")


def confirm_parametric_config(config: ParametricConfig) -> bool:
    """Solicita confirmación del usuario."""
    if not config.is_valid:
        print("\n[ADVERTENCIA] La configuración tiene errores.")
        print("Se recomienda ajustar los parámetros.")

    while True:
        choice = input("\n¿Confirmar configuración? [S/n]: ").strip().lower()
        if choice in ("", "s", "si", "y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        print("Responde S o N")
