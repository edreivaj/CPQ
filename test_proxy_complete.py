#!/usr/bin/env python3
"""
Test completo del Urbanismo Proxy

Este script demuestra el flujo completo:
1. Generar datos sintéticos
2. Verificar que están listos
3. Ejecutar análisis proxy
4. Mostrar resultados
"""

import sys
import os


def test_proxy_workflow():
    """Test completo del workflow del proxy"""

    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TEST COMPLETO URBANISMO PROXY" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")

    # Paso 1: Generar datos sintéticos
    print("\n[PASO 1/4] Generando datos sintéticos...")
    print("-" * 70)

    import generate_synthetic_data as gen

    data_dir = "/home/user/CPQ/data"
    center_x, center_y = 440000.0, 4474000.0  # Madrid centro

    try:
        success = gen.generate_synthetic_data(center_x, center_y, data_dir)
        if not success:
            print("❌ Error generando datos sintéticos")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Paso 2: Verificar datos
    print("\n" + "=" * 70)
    print("[PASO 2/4] Verificando datos...")
    print("-" * 70)

    import verify_proxy_data as verify

    try:
        success = verify.verify_data()
        if not success:
            print("❌ Los datos no pasaron la verificación")
            return False
    except Exception as e:
        print(f"❌ Error verificando datos: {e}")
        return False

    # Paso 3: Ejecutar análisis proxy
    print("\n" + "=" * 70)
    print("[PASO 3/4] Ejecutando análisis proxy...")
    print("-" * 70)

    try:
        import geopandas as gpd
        from cpq.analysis import compute_urbanismo_proxy, ProxyConfig
        from cpq.utils import bbox_from_gdf

        # Leer datos
        parcels_file = os.path.join(data_dir, "parcels.gpkg")
        buildings_file = os.path.join(data_dir, "buildings.gpkg")

        print(f"  • Leyendo parcelas desde {parcels_file}...")
        parcels_gdf = gpd.read_file(parcels_file)

        print(f"  • Leyendo edificios desde {buildings_file}...")
        buildings_gdf = gpd.read_file(buildings_file)

        # Seleccionar una parcela al azar como objetivo
        import numpy as np
        np.random.seed(42)
        target_idx = np.random.randint(0, len(parcels_gdf))
        target_parcel = parcels_gdf.iloc[[target_idx]]

        print(f"\n  • Parcela objetivo: {target_parcel['id'].iloc[0]}")
        print(f"  • Área parcela: {target_parcel['area_m2'].iloc[0]:.1f} m²")

        # Crear bbox para contexto (250m)
        bbox = bbox_from_gdf(target_parcel, buffer=250.0)

        # Filtrar parcelas y edificios en el bbox
        print(f"\n  • Filtrando contexto (250m)...")

        from shapely.geometry import box
        bbox_geom = box(*bbox)

        parcels_nearby = parcels_gdf[parcels_gdf.intersects(bbox_geom)]
        buildings_nearby = buildings_gdf[buildings_gdf.intersects(bbox_geom)]

        # Excluir la parcela objetivo
        parcels_nearby = parcels_nearby[parcels_nearby['id'] != target_parcel['id'].iloc[0]]

        print(f"    - Parcelas vecinas: {len(parcels_nearby)}")
        print(f"    - Edificios vecinos: {len(buildings_nearby)}")

        if len(parcels_nearby) < 5:
            print("\n  ⚠️  Pocas parcelas vecinas - aumentando radio...")
            bbox = bbox_from_gdf(target_parcel, buffer=400.0)
            bbox_geom = box(*bbox)
            parcels_nearby = parcels_gdf[parcels_gdf.intersects(bbox_geom)]
            buildings_nearby = buildings_gdf[buildings_gdf.intersects(bbox_geom)]
            parcels_nearby = parcels_nearby[parcels_nearby['id'] != target_parcel['id'].iloc[0]]
            print(f"    - Parcelas vecinas (400m): {len(parcels_nearby)}")
            print(f"    - Edificios vecinos (400m): {len(buildings_nearby)}")

        # Ejecutar proxy
        print(f"\n  • Ejecutando compute_urbanismo_proxy()...")

        cfg = ProxyConfig(
            radius_m=250.0,
            min_neighbors=5,  # Reducido para datos sintéticos
            comparable_area_tolerance=0.50,
            building_selection_mode="smart",
            use_road_classification=False  # Sin OSM para datos sintéticos
        )

        proxy_result = compute_urbanismo_proxy(
            target_parcel_gdf=target_parcel,
            parcels_gdf=parcels_nearby,
            buildings_gdf=buildings_nearby,
            roads_gdf=None,  # Sin viales para datos sintéticos
            cfg=cfg
        )

        # Paso 4: Mostrar resultados
        print("\n" + "=" * 70)
        print("[PASO 4/4] RESULTADOS DEL ANÁLISIS PROXY")
        print("=" * 70)

        print(f"\n📊 Estadísticas:")
        print(f"  • Parcelas analizadas: {proxy_result.stats.n_parcels_analyzed}")
        print(f"  • Parcelas comparables: {proxy_result.stats.n_comparables}")
        print(f"  • Parcelas con edificio: {proxy_result.stats.n_parcels_used}")

        print(f"\n🎯 Confianza:")
        print(f"  • Score: {proxy_result.confidence_score:.3f}")
        print(f"  • Nivel: {proxy_result.confidence_label.upper()}")
        print(f"  • Usar proxy: {'SÍ ✓' if proxy_result.use_proxy else 'NO ✗'}")

        print(f"\n📐 Parámetros Inferidos:")
        print(f"  • Retranqueo frontal: {proxy_result.retranqueo_frontal_m:.2f} m")
        print(f"  • Retranqueo lateral: {proxy_result.retranqueo_lateral_m:.2f} m")
        print(f"  • Retranqueo fondo:   {proxy_result.retranqueo_fondo_m:.2f} m")
        print(f"  • Ocupación máxima:   {proxy_result.ocupacion_max*100:.1f} %")
        print(f"  • Edificabilidad:     {proxy_result.edificabilidad_m2t_m2s:.2f}")

        if proxy_result.buildable_envelope:
            print(f"\n🏗️  Envolvente Edificable:")
            print(f"  • Área edificable: {proxy_result.buildable_area_m2:.1f} m²")
            print(f"  • Ratio uso suelo: {(proxy_result.buildable_area_m2 / target_parcel['area_m2'].iloc[0])*100:.1f}%")

        # Comparación con defaults
        from cpq.config import CFG

        print(f"\n📊 Comparación con Defaults:")
        print(f"  {'Parámetro':<25} {'Proxy':<12} {'Default':<12} {'Diferencia':<12}")
        print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12}")

        ret_front_diff = proxy_result.retranqueo_frontal_m - CFG.RETRANQUEO_FRONTAL_M
        ret_lat_diff = proxy_result.retranqueo_lateral_m - CFG.RETRANQUEO_LATERAL_M
        ocup_diff = (proxy_result.ocupacion_max * 100) - CFG.OCUPACION_PORCENTAJE
        edif_diff = proxy_result.edificabilidad_m2t_m2s - CFG.EDIFICABILIDAD_M2T_M2S

        print(f"  {'Retranqueo frontal (m)':<25} {proxy_result.retranqueo_frontal_m:<12.2f} "
              f"{CFG.RETRANQUEO_FRONTAL_M:<12.2f} {ret_front_diff:+.2f} m")
        print(f"  {'Retranqueo lateral (m)':<25} {proxy_result.retranqueo_lateral_m:<12.2f} "
              f"{CFG.RETRANQUEO_LATERAL_M:<12.2f} {ret_lat_diff:+.2f} m")
        print(f"  {'Ocupación (%)':<25} {proxy_result.ocupacion_max*100:<12.1f} "
              f"{CFG.OCUPACION_PORCENTAJE:<12.1f} {ocup_diff:+.1f} %")
        print(f"  {'Edificabilidad':<25} {proxy_result.edificabilidad_m2t_m2s:<12.2f} "
              f"{CFG.EDIFICABILIDAD_M2T_M2S:<12.2f} {edif_diff:+.2f}")

        print("\n" + "=" * 70)
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 70)

        print("\n💡 Próximos pasos:")
        print("  1. Activar proxy en main.py → USE_PROXY = True")
        print("  2. Ejecutar main.py con una referencia catastral real")
        print("  3. Verificar que los parámetros proxy se usan correctamente")

        return True

    except ImportError as e:
        print(f"\n❌ Error de importación: {e}")
        print("\n💡 Asegúrate de que el módulo cpq está disponible:")
        print("   - Ejecuta desde /home/user/CPQ/")
        print("   - O añade al PYTHONPATH: export PYTHONPATH=/home/user/CPQ:$PYTHONPATH")
        return False

    except Exception as e:
        print(f"\n❌ Error ejecutando proxy: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Añadir directorio raíz al path
    sys.path.insert(0, "/home/user/CPQ")

    success = test_proxy_workflow()
    sys.exit(0 if success else 1)
