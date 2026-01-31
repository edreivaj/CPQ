#!/usr/bin/env python3
"""
Ejemplo de integración del Urbanismo Proxy en CPQ

Muestra cómo usar el análisis de contexto para sustituir
parámetros urbanísticos por defecto.
"""

import sys
from cpq.config import CFG
from cpq.services import CatastroService, OSMService
from cpq.analysis import compute_urbanismo_proxy, ProxyConfig
from cpq.utils import bbox_from_gdf


def ejemplo_basico(refcat14: str):
    """
    Ejemplo básico: análisis proxy de una parcela

    Args:
        refcat14: Referencia catastral (14 caracteres)
    """

    print("="*70)
    print("EJEMPLO: Análisis de Urbanismo Proxy")
    print("="*70)

    # 1. Inicializar servicios
    catastro = CatastroService()
    osm = OSMService()

    # 2. Obtener parcela objetivo
    print(f"\n[1/5] Obteniendo parcela {refcat14}...")
    target_gdf = catastro.get_parcel_geometry(refcat14)

    if target_gdf is None:
        print("❌ No se pudo obtener la parcela")
        return

    target_area = target_gdf.geometry.iloc[0].area
    print(f"  ✓ Parcela obtenida: {target_area:,.2f} m²")

    # 3. Obtener contexto (250m + 50m buffer)
    print("\n[2/5] Obteniendo parcelas y edificios vecinos...")
    bbox = bbox_from_gdf(target_gdf, buffer=300.0)

    # NOTA: Este ejemplo asume que tienes las capas completas
    # En producción, necesitarías servicios adicionales del Catastro
    # para obtener parcelas y edificios en el bbox

    # Por ahora, simularemos que no hay datos de contexto
    # (en la implementación real, aquí irían las consultas al Catastro)

    print("  ⚠️  Este ejemplo necesita acceso a capas completas de Catastro")
    print("     (parcels_gdf y buildings_gdf)")
    print("\n  Para usar el proxy en producción, necesitas:")
    print("  1. Servicio WFS de parcelas del Catastro")
    print("  2. Servicio WFS de edificios del Catastro")
    print("  3. O archivos SHP/GPKG locales con las capas")

    # 4. Consultar viales OSM
    print("\n[3/5] Consultando viales OSM...")
    roads_gdf = osm.fetch_roads(bbox)

    if roads_gdf.empty:
        print("  ⚠️  No se encontraron viales OSM en el área")
    else:
        print(f"  ✓ {len(roads_gdf)} segmentos viales encontrados")

    # 5. Mostrar cómo se ejecutaría el proxy (pseudocódigo)
    print("\n[4/5] Configuración del proxy:")
    cfg = ProxyConfig(
        radius_m=250.0,
        min_neighbors=10,
        min_building_area_m2=35.0,
        use_comparable_parcels=True,
        comparable_area_tolerance=0.50,
        building_selection_mode="smart",
        use_road_classification=True,
        road_buffer_m=15.0
    )

    print(f"  • Radio de búsqueda: {cfg.radius_m}m")
    print(f"  • Mínimo de vecinos: {cfg.min_neighbors}")
    print(f"  • Parcelas comparables: ±{cfg.comparable_area_tolerance*100:.0f}%")
    print(f"  • Selección edificio: {cfg.building_selection_mode}")

    print("\n[5/5] Ejecución del análisis (pseudocódigo):")
    print("""
    # En producción:
    result = compute_urbanismo_proxy(
        target_parcel_gdf=target_gdf,
        parcels_gdf=parcels_nearby,      # ← Necesitas obtener esto
        buildings_gdf=buildings_nearby,  # ← Necesitas obtener esto
        roads_gdf=roads_gdf,
        cfg=cfg
    )

    if result.use_proxy:
        print(f"Confianza: {result.confidence_label}")
        print(f"Retranqueo frontal: {result.retranqueo_frontal_m:.2f}m")
        print(f"Retranqueo lateral: {result.retranqueo_lateral_m:.2f}m")
        print(f"Ocupación máxima: {result.ocupacion_max*100:.1f}%")
        print(f"Edificabilidad: {result.edificabilidad_m2t_m2s:.2f}")

        # Usar valores proxy en lugar de defaults
        retranqueo_frontal = result.retranqueo_frontal_m
        buildable_envelope = result.buildable_envelope

    else:
        print("Confianza baja - usando defaults")
        retranqueo_frontal = CFG.RETRANQUEO_FRONTAL_M
    """)

    print("\n" + "="*70)
    print("VALORES ACTUALES (Defaults del Config)")
    print("="*70)
    print(f"Retranqueo frontal: {CFG.RETRANQUEO_FRONTAL_M}m")
    print(f"Retranqueo lateral: {CFG.RETRANQUEO_LATERAL_M}m")
    print(f"Ocupación máxima:   {CFG.OCUPACION_PORCENTAJE}%")
    print(f"Edificabilidad:     {CFG.EDIFICABILIDAD_M2T_M2S}")
    print("="*70)


def ejemplo_avanzado():
    """
    Ejemplo avanzado: diferentes perfiles de configuración
    """

    print("\n\n" + "="*70)
    print("PERFILES DE CONFIGURACIÓN")
    print("="*70)

    print("\n--- PERFIL CONSERVADOR ---")
    print("(Promotor prudente, evita riesgos)")
    conservador = ProxyConfig(
        radius_m=200,
        min_neighbors=15,
        comparable_area_tolerance=0.30,
        building_selection_mode="centroid",
        occupancy_clip=(0.05, 0.80)
    )
    print(f"  • Radio reducido: {conservador.radius_m}m")
    print(f"  • Más vecinos requeridos: {conservador.min_neighbors}")
    print(f"  • Solo parcelas muy similares: ±{conservador.comparable_area_tolerance*100:.0f}%")
    print("  • Usar percentil p25 de retranqueos")

    print("\n--- PERFIL EQUILIBRADO (DEFAULT) ---")
    print("(Balance entre aprovechamiento y seguridad)")
    equilibrado = ProxyConfig()
    print(f"  • Radio estándar: {equilibrado.radius_m}m")
    print(f"  • Vecinos: {equilibrado.min_neighbors}")
    print(f"  • Parcelas comparables: ±{equilibrado.comparable_area_tolerance*100:.0f}%")
    print("  • Usar percentil p50 (mediana)")

    print("\n--- PERFIL AGRESIVO ---")
    print("(Maximizar aprovechamiento)")
    agresivo = ProxyConfig(
        radius_m=300,
        min_neighbors=8,
        comparable_area_tolerance=0.60,
        building_selection_mode="largest",
        occupancy_clip=(0.01, 0.95)
    )
    print(f"  • Radio ampliado: {agresivo.radius_m}m")
    print(f"  • Menos vecinos: {agresivo.min_neighbors}")
    print(f"  • Rango amplio: ±{agresivo.comparable_area_tolerance*100:.0f}%")
    print("  • Usar percentil p75 de retranqueos")

    print("\n" + "="*70)


def mostrar_integracion_cpq():
    """
    Muestra cómo integrar el proxy en el flujo principal de CPQ
    """

    print("\n\n" + "="*70)
    print("INTEGRACIÓN EN FLUJO CPQ PRINCIPAL")
    print("="*70)

    print("""
# En main.py, después de obtener la parcela:

# 1. Ejecutar análisis proxy
print("[PROXY] Analizando contexto urbanístico...")

proxy_result = compute_urbanismo_proxy(
    target_parcel_gdf=gdf_parcel,
    parcels_gdf=parcels_nearby,
    buildings_gdf=buildings_nearby,
    roads_gdf=roads_nearby,
    cfg=ProxyConfig()
)

# 2. Mostrar resultados al usuario
print(f"\\n[PROXY] Análisis completado")
print(f"  Confianza: {proxy_result.confidence_label}")
print(f"  Vecinos analizados: {proxy_result.stats.n_parcels_used}")

if proxy_result.use_proxy:
    print("  ✓ Usando parámetros inferidos del entorno")
    print(f"    Retranqueo frontal: {proxy_result.retranqueo_frontal_m:.2f}m "
          f"(default: {CFG.RETRANQUEO_FRONTAL_M}m)")
    print(f"    Ocupación máxima: {proxy_result.ocupacion_max*100:.1f}% "
          f"(default: {CFG.OCUPACION_PORCENTAJE}%)")

    # 3. Sustituir parámetros
    retranqueo_frontal_efectivo = proxy_result.retranqueo_frontal_m
    retranqueo_lateral_efectivo = proxy_result.retranqueo_lateral_m
    buildable_geometry = proxy_result.buildable_envelope

else:
    print("  ⚠ Confianza insuficiente - usando defaults")
    retranqueo_frontal_efectivo = CFG.RETRANQUEO_FRONTAL_M
    retranqueo_lateral_efectivo = CFG.RETRANQUEO_LATERAL_M

    # Calcular buildable normalmente
    buildable_geometry = analysis_result.buildable_geometry

# 4. Continuar con el flujo normal
buildable_area_m2 = buildable_geometry.area

valid_models = filter_valid_models(
    num_bedrooms,
    parcel_area_m2,
    buildable_area_m2
)

# ... resto del código
""")

    print("="*70)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          URBANISMO PROXY - Ejemplos de Integración              ║
║                         CPQ v4.5+                                ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # Ejemplo 1: Uso básico
    if len(sys.argv) > 1:
        refcat = sys.argv[1]
        ejemplo_basico(refcat)
    else:
        print("Uso: python example_proxy_integration.py <REFCAT>")
        print("Ejemplo: python example_proxy_integration.py 1234567AB1234C")
        print("\nEjecutando ejemplos sin datos reales...\n")

    # Ejemplo 2: Perfiles de configuración
    ejemplo_avanzado()

    # Ejemplo 3: Integración en CPQ
    mostrar_integracion_cpq()

    print("\n\n📚 Para más información, consulta: URBANISMO_PROXY.md")
    print("="*70)
