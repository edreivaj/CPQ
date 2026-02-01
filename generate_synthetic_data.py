#!/usr/bin/env python3
"""
Generador de datos sintéticos para probar el Urbanismo Proxy

Crea parcelas y edificios sintéticos alrededor de una referencia catastral
para poder probar el proxy sin descargar datos reales del Catastro.
"""

import argparse
import os
import sys
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.affinity import translate


def generate_synthetic_data(center_x, center_y, output_dir):
    """
    Genera datos sintéticos de parcelas y edificios

    Args:
        center_x: Coordenada X central (EPSG:25830)
        center_y: Coordenada Y central (EPSG:25830)
        output_dir: Directorio de salida
    """

    print("=" * 70)
    print("GENERADOR DE DATOS SINTÉTICOS PARA PROXY")
    print("=" * 70)

    try:
        import geopandas as gpd
        import pandas as pd
    except ImportError:
        print("\n❌ Error: Necesitas geopandas instalado")
        print("   Instalar con: pip install geopandas")
        sys.exit(1)

    np.random.seed(42)  # Reproducibilidad

    # Parámetros de generación
    GRID_SIZE = 20  # 20x20 = 400m x 400m
    PARCEL_SIZE_BASE = 15.0  # Tamaño base de parcela
    PARCEL_SIZE_VAR = 0.3  # Variación ±30%
    N_PARCELS = 50
    BUILDING_COVERAGE_MIN = 0.30  # Ocupación mínima
    BUILDING_COVERAGE_MAX = 0.70  # Ocupación máxima
    SETBACK_MIN = 2.0  # Retranqueo mínimo
    SETBACK_MAX = 5.0  # Retranqueo máximo

    print(f"\n[1/4] Configuración:")
    print(f"  Centro: ({center_x:.2f}, {center_y:.2f})")
    print(f"  Área: {GRID_SIZE}x{GRID_SIZE} = {GRID_SIZE*GRID_SIZE}m x {GRID_SIZE*GRID_SIZE}m")
    print(f"  Parcelas a generar: {N_PARCELS}")

    # 1. Generar parcelas
    print(f"\n[2/4] Generando parcelas...")

    parcels = []
    parcel_ids = []

    # Grid de posiciones posibles
    grid_positions = []
    for i in range(20):
        for j in range(20):
            x = center_x - 200 + i * 20
            y = center_y - 200 + j * 20
            grid_positions.append((x, y))

    # Seleccionar posiciones aleatorias
    selected_positions = np.random.choice(len(grid_positions), N_PARCELS, replace=False)

    for idx, pos_idx in enumerate(selected_positions):
        x, y = grid_positions[pos_idx]

        # Tamaño variable de parcela
        size_factor = 1.0 + np.random.uniform(-PARCEL_SIZE_VAR, PARCEL_SIZE_VAR)
        width = PARCEL_SIZE_BASE * size_factor
        height = PARCEL_SIZE_BASE * size_factor

        # Pequeña rotación aleatoria
        angle = np.random.uniform(-5, 5)

        # Crear parcela rectangular
        parcel = box(x, y, x + width, y + height)

        # Aplicar rotación ligera
        if abs(angle) > 0.1:
            from shapely.affinity import rotate
            parcel = rotate(parcel, angle, origin='center')

        parcels.append(parcel)
        parcel_ids.append(f"SYNTH_{idx:04d}")

    parcels_gdf = gpd.GeoDataFrame({
        'id': parcel_ids,
        'area_m2': [p.area for p in parcels],
        'synthetic': True
    }, geometry=parcels, crs="EPSG:25830")

    print(f"  ✓ {len(parcels_gdf)} parcelas generadas")
    print(f"  Área media: {parcels_gdf['area_m2'].mean():.1f} m²")
    print(f"  Área min/max: {parcels_gdf['area_m2'].min():.1f} / {parcels_gdf['area_m2'].max():.1f} m²")

    # 2. Generar edificios
    print(f"\n[3/4] Generando edificios...")

    buildings = []
    building_ids = []
    building_parcel_ids = []

    for idx, parcel in enumerate(parcels):
        # 80% de las parcelas tienen edificio
        if np.random.random() < 0.80:
            # Ocupación aleatoria
            coverage = np.random.uniform(BUILDING_COVERAGE_MIN, BUILDING_COVERAGE_MAX)

            # Retranqueos aleatorios por lado
            setback_front = np.random.uniform(SETBACK_MIN, SETBACK_MAX)
            setback_back = np.random.uniform(SETBACK_MIN, SETBACK_MAX)
            setback_left = np.random.uniform(SETBACK_MIN, SETBACK_MAX)
            setback_right = np.random.uniform(SETBACK_MIN, SETBACK_MAX)

            # Obtener bounds de la parcela
            minx, miny, maxx, maxy = parcel.bounds

            # Aplicar retranqueos
            building_minx = minx + setback_left
            building_maxx = maxx - setback_right
            building_miny = miny + setback_front
            building_maxy = maxy - setback_back

            # Verificar que el edificio es válido
            if building_maxx > building_minx and building_maxy > building_miny:
                building = box(building_minx, building_miny, building_maxx, building_maxy)

                # Ajustar para alcanzar la ocupación deseada
                target_area = parcel.area * coverage
                current_area = building.area

                if current_area > 0:
                    scale_factor = np.sqrt(target_area / current_area)
                    centroid = building.centroid

                    from shapely.affinity import scale
                    building = scale(building, xfact=scale_factor, yfact=scale_factor,
                                   origin=centroid)

                    # Asegurar que está dentro de la parcela
                    if parcel.contains(building) or parcel.intersects(building):
                        buildings.append(building)
                        building_ids.append(f"BLDG_{idx:04d}")
                        building_parcel_ids.append(parcel_ids[idx])

    buildings_gdf = gpd.GeoDataFrame({
        'id': building_ids,
        'parcel_id': building_parcel_ids,
        'area_m2': [b.area for b in buildings],
        'synthetic': True
    }, geometry=buildings, crs="EPSG:25830")

    print(f"  ✓ {len(buildings_gdf)} edificios generados")
    print(f"  Área media: {buildings_gdf['area_m2'].mean():.1f} m²")
    print(f"  Ocupación media: {(buildings_gdf['area_m2'].sum() / parcels_gdf['area_m2'].sum())*100:.1f}%")

    # 3. Guardar archivos
    print(f"\n[4/4] Guardando archivos...")

    os.makedirs(output_dir, exist_ok=True)

    parcels_file = os.path.join(output_dir, "parcels.gpkg")
    buildings_file = os.path.join(output_dir, "buildings.gpkg")

    parcels_gdf.to_file(parcels_file, driver="GPKG")
    buildings_gdf.to_file(buildings_file, driver="GPKG")

    print(f"  ✓ Parcelas guardadas: {parcels_file}")
    print(f"  ✓ Edificios guardados: {buildings_file}")

    # 4. Crear archivo README
    readme_file = os.path.join(output_dir, "README.txt")
    with open(readme_file, 'w') as f:
        f.write("DATOS SINTÉTICOS PARA URBANISMO PROXY\n")
        f.write("=" * 70 + "\n\n")
        f.write("Estos datos fueron generados sintéticamente para probar el proxy.\n")
        f.write("NO son datos reales del Catastro.\n\n")
        f.write(f"Centro: ({center_x:.2f}, {center_y:.2f}) EPSG:25830\n")
        f.write(f"Parcelas: {len(parcels_gdf)}\n")
        f.write(f"Edificios: {len(buildings_gdf)}\n")
        f.write(f"\nGenerado: {pd.Timestamp.now()}\n")

    print(f"  ✓ README guardado: {readme_file}")

    # Resumen
    print("\n" + "=" * 70)
    print("✅ DATOS SINTÉTICOS GENERADOS CORRECTAMENTE")
    print("=" * 70)
    print(f"\nArchivos creados:")
    print(f"  • {parcels_file} ({len(parcels_gdf)} parcelas)")
    print(f"  • {buildings_file} ({len(buildings_gdf)} edificios)")
    print(f"  • {readme_file}")

    print(f"\nPróximos pasos:")
    print(f"  1. Verificar datos: python verify_proxy_data.py")
    print(f"  2. Activar proxy: editar main.py → USE_PROXY = True")
    print(f"  3. Ejecutar: python main.py")

    return True


def get_coords_from_refcat(refcat14):
    """
    Intenta obtener coordenadas aproximadas desde una referencia catastral

    NOTA: Esta es una aproximación muy básica. Para datos reales,
    usa el servicio del Catastro.
    """

    print(f"\n⚠️  Usando coordenadas sintéticas para {refcat14}")
    print("   (no son las coordenadas reales de la referencia catastral)")

    # Coordenadas por defecto en Madrid centro (EPSG:25830)
    # Esto es solo un ejemplo - no corresponde a la refcat real
    default_x = 440000.0
    default_y = 4474000.0

    return default_x, default_y


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera datos sintéticos para probar el Urbanismo Proxy"
    )
    parser.add_argument(
        "--refcat",
        type=str,
        help="Referencia catastral (14 caracteres) - solo para referencia"
    )
    parser.add_argument(
        "--center-x",
        type=float,
        help="Coordenada X del centro (EPSG:25830)"
    )
    parser.add_argument(
        "--center-y",
        type=float,
        help="Coordenada Y del centro (EPSG:25830)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/home/user/CPQ/data",
        help="Directorio de salida (default: /home/user/CPQ/data)"
    )

    args = parser.parse_args()

    # Determinar centro
    if args.center_x and args.center_y:
        center_x = args.center_x
        center_y = args.center_y
    elif args.refcat:
        center_x, center_y = get_coords_from_refcat(args.refcat)
    else:
        # Usar Madrid centro por defecto
        center_x, center_y = 440000.0, 4474000.0
        print("\n💡 Usando coordenadas por defecto (Madrid centro)")
        print("   Usa --center-x y --center-y para especificar otra ubicación")

    # Generar datos
    success = generate_synthetic_data(center_x, center_y, args.output)

    sys.exit(0 if success else 1)
