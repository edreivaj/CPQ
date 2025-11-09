"""
Interfaz de línea de comandos (CLI)
"""

from typing import Optional, List, Tuple
from .models import CONSTRUCTION_PRICES, EXTRAS_CATALOG


def select_model_interactive(valid_models: List[dict]) -> Optional[dict]:
    """
    Selección interactiva de modelo de casa

    Args:
        valid_models: Lista de modelos válidos

    Returns:
        Modelo seleccionado o None
    """
    if not valid_models:
        return None

    # Agrupar por dormitorios
    grouped = {}
    for m in valid_models:
        d = m['numero_dormitorios']
        grouped.setdefault(d, []).append(m)

    print("\n" + "="*60)
    print("Modelos Válidos (Agrupados por dormitorios):")
    print("="*60)

    options = {}
    idx = 1

    for d in sorted(grouped.keys()):
        print(f"\n--- {d} Dormitorios ---")
        for m in grouped[d]:
            print(f"  [{idx}] {m['nombre']} "
                  f"({m['huella_ancho_m']}x{m['huella_largo_m']}m = "
                  f"{m['superficie_huella_m2']} m²)")
            options[str(idx)] = m
            idx += 1

    # Solicitar selección
    while True:
        sel = input("\nIntroduce el número [N] del modelo a analizar: ").strip()
        if sel in options:
            return options[sel]
        print("Opción no válida. Inténtalo de nuevo.")


def select_construction_system() -> Tuple[str, str]:
    """
    Selección interactiva de sistema constructivo y nivel de acabado

    Returns:
        Tuple (sistema, nivel)
    """
    systems = list(CONSTRUCTION_PRICES.keys())

    print("\n" + "="*60)
    print("[Bloque 1] Sistema Constructivo:")
    print("="*60)

    options = {}
    for i, sys in enumerate(systems, 1):
        print(f"  [{i}] {sys.capitalize()}")
        options[str(i)] = sys

    # Seleccionar sistema
    selected_sys = None
    while selected_sys is None:
        choice = input("Selecciona sistema [N]: ").strip()
        if choice in options:
            selected_sys = options[choice]
        else:
            print("Opción inválida.")

    # Seleccionar nivel
    levels = list(CONSTRUCTION_PRICES[selected_sys].keys())
    print(f"\n[Bloque 1] Nivel de Acabado para {selected_sys.capitalize()}:")

    level_options = {}
    for i, lvl in enumerate(levels, 1):
        price = CONSTRUCTION_PRICES[selected_sys][lvl]
        print(f"  [{i}] {lvl.capitalize()} ({price:,.0f} €/m²)")
        level_options[str(i)] = lvl

    selected_level = None
    while selected_level is None:
        choice = input("Selecciona nivel [N]: ").strip()
        if choice in level_options:
            selected_level = level_options[choice]
        else:
            print("Opción inválida.")

    return selected_sys, selected_level


def select_extras() -> List[dict]:
    """
    Selección interactiva de extras

    Returns:
        Lista de extras seleccionados con label y cost
    """
    print("\n" + "="*60)
    print("[Bloque 6] Extras Disponibles:")
    print("="*60)

    extras_list = list(EXTRAS_CATALOG.keys())

    for i, key in enumerate(extras_list, 1):
        ex = EXTRAS_CATALOG[key]
        if ex["type"] == "fixed":
            print(f"  [{i}] {ex['label']} — {ex['price']:,.2f} €")
        else:
            print(f"  [{i}] {ex['label']} — {ex['unit_price']:,.2f} €/ud")

    sel_input = input(
        "\nIntroduce los números separados por comas (o Enter para ninguno): "
    ).strip()

    if not sel_input:
        return []

    selected_extras = []
    seen_groups = set()

    for token in sel_input.split(","):
        token = token.strip()

        if not token.isdigit():
            continue

        idx = int(token)

        if idx < 1 or idx > len(extras_list):
            continue

        key = extras_list[idx - 1]
        ex = EXTRAS_CATALOG[key]

        # Validar grupos (ej: solo una piscina)
        group = ex.get("group")
        if group is not None:
            if group in seen_groups:
                print(f"  (Aviso) Ya hay un extra del grupo '{group}'. "
                      f"Omitiendo: {ex['label']}")
                continue
            seen_groups.add(group)

        # Procesar según tipo
        if ex["type"] == "unit":
            while True:
                qty_input = input(
                    f"  Cantidad para '{ex['label']}' (número entero ≥0): "
                ).strip()

                if qty_input.isdigit():
                    qty = int(qty_input)
                    selected_extras.append({
                        "label": f"{ex['label']} × {qty}",
                        "cost": qty * ex['unit_price']
                    })
                    break
                else:
                    print("  Valor inválido.")
        else:
            selected_extras.append({
                "label": ex['label'],
                "cost": ex['price']
            })

    return selected_extras


def get_user_input_refcat() -> str:
    """
    Solicita referencia catastral al usuario

    Returns:
        Referencia catastral (14 caracteres)
    """
    refcat_full = input(
        "\nIntroduce la referencia catastral completa: "
    ).strip().replace(" ", "")
    return refcat_full[:14]


def get_user_input_bedrooms() -> int:
    """
    Solicita número de dormitorios al usuario

    Returns:
        Número de dormitorios (entero positivo)
    """
    num_bedrooms = None

    while num_bedrooms is None:
        try:
            val = int(input("Número de dormitorios deseado: ").strip())
            if val > 0:
                num_bedrooms = val
            else:
                print("Debe ser un número positivo.")
        except ValueError:
            print("Entrada inválida.")

    return num_bedrooms


def get_financing_parameters(
    default_interest: float,
    default_years: int
) -> Tuple[float, int]:
    """
    Solicita parámetros de financiación

    Args:
        default_interest: Interés por defecto
        default_years: Plazo por defecto

    Returns:
        Tuple (tasa_interes, años)
    """
    use_default = input(
        f"¿Usar interés/plazo por defecto "
        f"({default_interest}% a {default_years} años)? [S/n]: "
    ).strip().lower()

    if use_default in ("", "s", "si", "sí", "y", "yes"):
        return default_interest, default_years
    else:
        try:
            interest_rate = float(
                input("TIN anual (%): ").strip().replace(",", ".")
            )
            years = int(input("Plazo (años): ").strip())
            return interest_rate, years
        except ValueError:
            print("Entrada no válida. Usando valores por defecto.")
            return default_interest, default_years
