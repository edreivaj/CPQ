#!/usr/bin/env python3
"""
Buildlovers - Calculadora de Implantación v4.5
Script principal ejecutable
"""

import sys
import math
import geopandas as gpd

from cpq.config import CFG
from cpq.models import CONSTRUCTION_PRICES
from cpq.services import CatastroService, MDTService, OSMService
from cpq.analysis import (
    ParcelBoundaryAnalyzer,
    compute_volume_metrics,
    calc_pendiente,
    get_xyz_from_pad,
    dimensionar_muro_perimetral_real,
    compute_horizontal_access_costs,
    compute_vertical_access_costs,
    compute_construction_cost,
    compute_slab_cost,
    compute_earthworks_cost,
    compute_containment_cost,
    compute_fees_total
)
from cpq.utils import bbox_from_gdf, create_house_pad, compute_monthly_payment
from cpq.model_filter import filter_valid_models
from cpq.cli import (
    get_user_input_refcat,
    get_user_input_bedrooms,
    select_model_interactive,
    select_construction_system,
    select_extras,
    get_financing_parameters
)


def main():
    """Función principal del programa"""

    print("=" * 60)
    print("Buildlovers — Calculadora de Implantación v4.5")
    print("=" * 60)

    # =========================================================================
    # PASO 1: Input de usuario
    # =========================================================================

    refcat14 = get_user_input_refcat()
    num_bedrooms = get_user_input_bedrooms()

    # =========================================================================
    # PASO 2: Inicializar servicios
    # =========================================================================

    catastro_svc = CatastroService()
    mdt_svc = MDTService()
    osm_svc = OSMService()

    # =========================================================================
    # PASO 3: Obtener parcela
    # =========================================================================

    gdf_parcel = catastro_svc.get_parcel_geometry(refcat14)

    if gdf_parcel is None:
        print("Error: No se pudo obtener la parcela.")
        sys.exit(1)

    parcel_geom = gdf_parcel.geometry.iloc[0]
    parcel_area_m2 = parcel_geom.area

    print(f"\nParcela obtenida. Área: {parcel_area_m2:,.2f} m²")

    # =========================================================================
    # PASO 4: Análisis de límites
    # =========================================================================

    bbox = bbox_from_gdf(gdf_parcel, buffer=20.0)

    analyzer = ParcelBoundaryAnalyzer(catastro_svc, osm_svc)
    analysis_result = analyzer.analyze(gdf_parcel, refcat14, bbox)

    if (not analysis_result.buildable_geometry or
        analysis_result.buildable_geometry.is_empty):
        print("Error: No se pudo calcular la caja edificable.")
        sys.exit(1)

    buildable_area_m2 = analysis_result.buildable_geometry.area

    # =========================================================================
    # PASO 5: Filtrar modelos válidos
    # =========================================================================

    valid_models = filter_valid_models(
        num_bedrooms,
        parcel_area_m2,
        buildable_area_m2
    )

    if not valid_models:
        print("\n¡Atención! Ningún modelo estándar encaja.")
        print("Se requiere ITP (Implantación Totalmente Personalizada).")
        sys.exit(0)

    # =========================================================================
    # PASO 6: Seleccionar modelo
    # =========================================================================

    selected_model = select_model_interactive(valid_models)

    if selected_model is None:
        print("No se seleccionó ningún modelo.")
        sys.exit(0)

    print(f"\n✓ Modelo seleccionado: {selected_model['nombre']}")

    # =========================================================================
    # PASO 7: Descargar MDT
    # =========================================================================

    print("\n--- Descargando topografía ---")
    mdt_path = mdt_svc.download_mdt(bbox)

    if mdt_path is None:
        print("⚠️  No se pudo descargar el MDT.")
        print("Se continuará con volúmenes = 0 y pendiente = 0.")

    # =========================================================================
    # PASO 8: Crear huella y calcular métricas topográficas
    # =========================================================================

    buildable_gdf = gpd.GeoDataFrame(
        [{"geometry": analysis_result.buildable_geometry}],
        crs=CFG.ETRS89_UTM30N
    )

    huella_gdf = create_house_pad(
        buildable_gdf,
        selected_model['huella_ancho_m'],
        selected_model['huella_largo_m']
    )

    if huella_gdf is None:
        print("Error: No se pudo crear la huella.")
        sys.exit(1)

    # Volúmenes
    print("\n  [DEBUG] Calculando volúmenes...")
    vol_metrics = compute_volume_metrics(huella_gdf, mdt_path)

    # Verificación de seguridad
    for key in ['z_optimal_m', 'cut_m3', 'fill_m3', 'balance_m3']:
        val = vol_metrics.get(key, 0.0)
        if val is None or (isinstance(val, float) and
                          (math.isnan(val) or math.isinf(val))):
            vol_metrics[key] = 0.0

    print(f"  [DEBUG] Volúmenes OK: cut={vol_metrics['cut_m3']:.2f}, "
          f"fill={vol_metrics['fill_m3']:.2f}")

    # Pendiente
    print("\n  [DEBUG] Calculando pendiente...")
    xs, ys, zs = get_xyz_from_pad(huella_gdf, mdt_path)

    if xs is None or len(xs) < 3:
        print("⚠️  Advertencia: No se pudo calcular pendiente. Usando 0%")
        slope_pct = 0.0
    else:
        _, _, slope_pct, _ = calc_pendiente(xs, ys, zs)
        if math.isnan(slope_pct) or math.isinf(slope_pct):
            slope_pct = 0.0
        print(f"  [DEBUG] Pendiente calculada: {slope_pct:.2f}%")

    # Mostrar métricas
    print(f"\nMétricas topográficas:")
    cut_display = (0.0 if math.isnan(vol_metrics.get('cut_m3', 0.0))
                  else vol_metrics.get('cut_m3', 0.0))
    fill_display = (0.0 if math.isnan(vol_metrics.get('fill_m3', 0.0))
                   else vol_metrics.get('fill_m3', 0.0))

    if cut_display == 0.0 and fill_display == 0.0:
        print(f"  ⚠️  Sin datos topográficos válidos")
        print(f"  - Desmonte: 0.00 m³")
        print(f"  - Terraplén: 0.00 m³")
        print(f"  - Pendiente: {slope_pct:.2f} %")
        print(f"  (La huella puede estar fuera del área MDT o sin datos)")
    else:
        print(f"  - Desmonte: {cut_display:.2f} m³")
        print(f"  - Terraplén: {fill_display:.2f} m³")
        print(f"  - Pendiente: {slope_pct:.2f} %")

    # =========================================================================
    # PASO 9: Seleccionar sistema constructivo
    # =========================================================================

    system, level = select_construction_system()
    base_price_m2 = CONSTRUCTION_PRICES[system][level]

    # =========================================================================
    # PASO 10: CALCULAR COSTES
    # =========================================================================

    print("\n" + "=" * 60)
    print("DESGLOSE DE COSTES")
    print("=" * 60)

    total_cost = 0.0

    # [1] Construcción
    cost_construction = compute_construction_cost(
        selected_model['superficie_m2'],
        base_price_m2
    )
    total_cost += cost_construction

    print(f"\n[1] Construcción ({system}, {level}):")
    print(f"    {selected_model['superficie_m2']:.2f} m² × "
          f"{base_price_m2:,.2f} €/m² = {cost_construction:,.2f} €")

    # [2a] Losa
    cost_slab = compute_slab_cost(selected_model['superficie_huella_m2'])
    total_cost += cost_slab

    print(f"\n[2a] Losa:")
    print(f"    {selected_model['superficie_huella_m2']:.2f} m² × "
          f"{CFG.COSTE_LOSA_M2:,.2f} €/m² = {cost_slab:,.2f} €")

    # [3a] Movimiento de tierras
    cost_cut, cost_fill, cost_excess, cost_earthworks = \
        compute_earthworks_cost(vol_metrics)
    total_cost += cost_earthworks

    print(f"\n[3a] Movimiento de tierras:")
    print(f"    Desmonte: {cost_cut:,.2f} €")
    print(f"    Terraplén: {cost_fill:,.2f} €")
    print(f"    Excedente: {cost_excess:,.2f} €")
    print(f"    Subtotal: {cost_earthworks:,.2f} €")

    # [3b] Contención
    print(f"\n[3b] Contención (muro perimetral de plataforma):")

    if mdt_path is not None:
        cota_plataforma = vol_metrics.get('z_optimal_m', 0.0)
        muro_result = dimensionar_muro_perimetral_real(
            mdt_path=mdt_path,
            pad_gdf=huella_gdf,
            parcel_geom=parcel_geom,
            cota_plataforma=cota_plataforma,
            paso_perfil=1.0,
            terreno_blando=False,
        )
    else:
        muro_result = None

    coste_muro, sobrecoste_pendiente, coste_contencion_total = \
        compute_containment_cost(muro_result, slope_pct)

    total_cost += coste_contencion_total

    if muro_result:
        print(f"    Tipo seleccionado: {muro_result['tipo_muro_elegido']}")
        print(f"    Coste muro (según MDT): {coste_muro:,.2f} €")
        print(f"    Altura máxima detectada: "
              f"{muro_result['h_max_global_m']:.2f} m")
    else:
        print(f"    (No se pudo calcular muro porque no hay MDT. "
              f"Coste muro = 0 €)")

    print(f"    Sobrecoste por pendiente ({slope_pct:.2f}%): "
          f"{sobrecoste_pendiente:,.2f} €")
    print(f"    Subtotal contención: {coste_contencion_total:,.2f} €")

    # [4a] Vallado
    total_cost += analysis_result.fence_cost

    print(f"\n[4a] Vallado:")
    print(f"    Frontal: {analysis_result.frontal_length_m:.2f} ml")
    print(f"    Lateral: {analysis_result.lateral_length_m:.2f} ml")
    print(f"    Total: {analysis_result.fence_cost:,.2f} €")

    # [4b] Puerta
    total_cost += CFG.COSTE_PUERTA_ACCESO

    print(f"\n[4b] Puerta de acceso:")
    print(f"    {CFG.COSTE_PUERTA_ACCESO:,.2f} €")

    # [4c] Accesos horizontales
    dist_peat, dist_veh, cost_peat, cost_veh, p_house = \
        compute_horizontal_access_costs(analysis_result.access_point, huella_gdf)

    total_cost += (cost_peat + cost_veh)

    print(f"\n[4c] Accesos horizontales:")
    print(f"    Peatonal: {dist_peat:.2f} m × "
          f"{CFG.COSTE_PAV_PEATONAL_ML:,.2f} €/ml = {cost_peat:,.2f} €")
    print(f"    Vehicular: {dist_veh:.2f} m × "
          f"{CFG.COSTE_PAV_VEHICULO_ML:,.2f} €/ml = {cost_veh:,.2f} €")

    # [4d] Acceso vertical
    delta_cota, cost_vertical = compute_vertical_access_costs(
        analysis_result.access_point,
        p_house,
        mdt_path
    )
    total_cost += cost_vertical

    print(f"\n[4d] Adaptación vertical:")
    print(f"    Δcota: {delta_cota:.2f} m → {cost_vertical:,.2f} €")

    # [4e] Conexiones
    total_cost += CFG.COSTE_FIJO_CONEXIONES_REDES

    print(f"\n[4e] Conexiones a redes:")
    print(f"    {CFG.COSTE_FIJO_CONEXIONES_REDES:,.2f} €")

    # [5] Honorarios
    cost_fees_total = compute_fees_total()
    total_cost += cost_fees_total

    print(f"\n[5] Honorarios técnicos:")
    print(f"    Arquitectura: {CFG.COSTE_FIJO_HONORARIOS_TECNICOS:,.2f} €")
    print(f"    Cálculo estructural: {CFG.HON_CALC_ESTRUCTURAL:,.2f} €")
    print(f"    Estudio geotécnico: {CFG.HON_ESTUDIO_GEOTECNICO:,.2f} €")
    print(f"    Levantamiento topográfico: {CFG.HON_LEV_TOPOGRAFICO:,.2f} €")
    print(f"    Legalizaciones: {CFG.HON_LEGALIZACIONES:,.2f} €")
    print(f"    Subtotal: {cost_fees_total:,.2f} €")

    # [6] Extras
    selected_extras = select_extras()
    cost_extras = sum(ex['cost'] for ex in selected_extras)
    total_cost += cost_extras

    if selected_extras:
        print(f"\n[6] Extras:")
        for ex in selected_extras:
            print(f"    {ex['label']}: {ex['cost']:,.2f} €")
        print(f"    Subtotal: {cost_extras:,.2f} €")
    else:
        print(f"\n[6] Extras: 0.00 € (ninguno)")

    # =========================================================================
    # TOTAL
    # =========================================================================

    print("\n" + "-" * 60)
    print(f"TOTAL PARCIAL: {total_cost:,.2f} €")
    print("=" * 60)

    # =========================================================================
    # PASO 11: Financiación
    # =========================================================================

    print("\n[7] Financiación — Cálculo de cuota de hipoteca")

    base_financiable = max(total_cost - cost_fees_total, 0.0)

    interest_rate, years = get_financing_parameters(
        CFG.DEFAULT_INTERES_HIPOTECA,
        CFG.DEFAULT_PLAZO_HIPOTECA_ANOS
    )

    monthly_payment = compute_monthly_payment(
        base_financiable,
        interest_rate,
        years
    )

    print("-" * 60)
    print(f"[7] Base financiable (Total - Honorarios): "
          f"{base_financiable:,.2f} €")
    print(f"[7] Cuota mensual estimada: {monthly_payment:,.2f} €/mes")
    print("=" * 60)

    print("\n✓ Cálculo completado con éxito.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
