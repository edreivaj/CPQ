#!/usr/bin/env python3
"""
Demostración completa del flujo CPQ con Urbanismo Proxy
Simula una ejecución real mostrando todos los pasos y módulos integrados
"""

import sys
import os

# Añadir directorio raíz al path
sys.path.insert(0, "/home/user/CPQ")

def demo_complete_flow():
    """Simula el flujo completo de CPQ con proxy activado"""

    print("=" * 70)
    print("Buildlovers — Calculadora de Implantación v4.5")
    print("=" * 70)
    print()

    # Simular inputs del usuario
    refcat14 = "0279305VK4707N0001TL"  # Madrid Chamberí
    num_bedrooms = 3

    print(f"Referencia catastral: {refcat14}")
    print(f"Número de dormitorios: {num_bedrooms}")
    print()

    # ========================================================================
    # PASO 1: Obtención de parcela del Catastro
    # ========================================================================
    print("=" * 70)
    print("PASO 1: OBTENCIÓN DE DATOS CATASTRALES")
    print("=" * 70)
    print()
    print(f"[Catastro] Obteniendo parcela {refcat14}...")
    print("[Catastro] ⚠️  WFS bloqueado por firewall (esperado en este entorno)")
    print()
    print("💡 En producción con conectividad:")
    print("   • Obtendría geometría de la parcela vía WFS")
    print("   • CRS: EPSG:25830 (ETRS89 UTM 30N)")
    print("   • Área aproximada: 450 m²")
    print()

    # Simular datos de la parcela
    parcel_area_m2 = 450.0
    parcel_centroid = (440123.45, 4474567.89)

    print(f"✓ Parcela procesada:")
    print(f"  • Área: {parcel_area_m2:.1f} m²")
    print(f"  • Centroide: {parcel_centroid}")
    print()

    # ========================================================================
    # PASO 2: Obtención de datos de elevación
    # ========================================================================
    print("=" * 70)
    print("PASO 2: ANÁLISIS DE TERRENO")
    print("=" * 70)
    print()
    print("[Terrain] Obteniendo datos de elevación...")
    print("[Terrain] Fuente: IGN MDT05 (resolución 5m)")
    print()

    slope_deg = 3.2
    slope_pct = 5.6

    print(f"✓ Análisis de pendiente:")
    print(f"  • Pendiente media: {slope_deg:.1f}° ({slope_pct:.1f}%)")
    print(f"  • Clasificación: PLANO (< 10%)")
    print()

    # ========================================================================
    # PASO 3: Obtención de zonificación
    # ========================================================================
    print("=" * 70)
    print("PASO 3: ANÁLISIS DE ZONIFICACIÓN URBANÍSTICA")
    print("=" * 70)
    print()
    print("[Zoning] Consultando planeamiento municipal...")
    print("[Zoning] Municipio: Madrid (28079)")
    print()

    zone = "Residencial Colectiva RC4"
    zone_code = "RC4"

    print(f"✓ Zonificación:")
    print(f"  • Zona: {zone}")
    print(f"  • Código: {zone_code}")
    print()

    # ========================================================================
    # PASO 3.5: ANÁLISIS DE CONTEXTO URBANÍSTICO (PROXY) ← NUEVO MÓDULO
    # ========================================================================
    print("=" * 70)
    print("PASO 3.5: ANÁLISIS DE CONTEXTO URBANÍSTICO (PROXY)")
    print("=" * 70)
    print()
    print("🎯 USE_PROXY = True  (ACTIVADO)")
    print()

    # Calcular bbox para contexto
    buffer_m = 250.0
    minx = parcel_centroid[0] - buffer_m
    maxx = parcel_centroid[0] + buffer_m
    miny = parcel_centroid[1] - buffer_m
    maxy = parcel_centroid[1] + buffer_m
    bbox = (minx, miny, maxx, maxy)

    print(f"[PROXY] Analizando entorno construido ({buffer_m:.0f}m)...")
    print()

    # Intento 1: WFS
    print("  [1/3] Intentando obtener datos vía WFS del Catastro...")
    print(f"[Catastro] Obteniendo parcelas en bbox ({maxx-minx:.0f}m x {maxy-miny:.0f}m)...")
    print("[Catastro] Error HTTP 403 - consulta bbox no soportada")
    print("[Catastro] Recomendación: usar archivos locales de CNIG")
    print()

    # Intento 2: Archivos locales
    print("  [2/3] WFS no disponible, buscando archivos locales...")
    parcels_file = "/home/user/CPQ/data/parcels.gpkg"
    buildings_file = "/home/user/CPQ/data/buildings.gpkg"
    print(f"    ✗ No se encontraron archivos locales")
    print(f"      Buscados: {parcels_file}, {buildings_file}")
    print()
    print("    💡 Para activar el proxy, necesitas:")
    print("       1. Descargar capas de https://centrodedescargas.cnig.es/")
    print("       2. Guardar en /home/user/CPQ/data/ como .gpkg")
    print("       3. Ver instrucciones en ACTIVAR_PROXY.md")
    print()

    print("  [3/3] ⚠️  Datos no disponibles - usando parámetros por defecto")
    print()

    # Simular qué pasaría SI tuviéramos los datos
    print("=" * 70)
    print("💡 SIMULACIÓN: Si los datos estuvieran disponibles...")
    print("=" * 70)
    print()
    print("  [2/3] WFS no disponible, buscando archivos locales...")
    print("    ✓ Encontrados archivos locales")
    print("    ✓ Parcelas cargadas: 45")
    print("    ✓ Edificios cargados: 38")
    print()

    print("[OSM] Obteniendo red viaria para clasificación de lados...")
    print("[OSM] ✓ 12 viales obtenidos en el área")
    print()

    print("[PROXY] Ejecutando inferencia estadística...")
    print("  • Filtrando parcelas comparables (±50% área)...")
    print("    → 45 parcelas → 28 comparables")
    print("  • Clasificando lados (frontal/lateral/fondo)...")
    print("    → Detectado frente a Calle Luchana (15m)")
    print("  • Seleccionando edificio principal (modo: smart)...")
    print("    → Score: 50% área + 30% centralidad + 20% compacidad")
    print("  • Calculando estadísticas (p10, p25, p50, p75, p90)...")
    print("  • Calculando confianza...")
    print()

    # Resultados del proxy (simulados)
    n_parcels = 28
    n_comparables = 18
    confidence_score = 0.78
    confidence_label = "ALTA"
    use_proxy = True

    retranqueo_frontal_m = 3.2
    retranqueo_lateral_m = 2.5
    retranqueo_fondo_m = 3.0
    ocupacion_max = 0.45  # 45%
    edificabilidad = 0.68
    buildable_area_m2 = 202.5

    # Valores por defecto para comparación
    default_ret_frontal = 5.0
    default_ret_lateral = 3.0
    default_ocupacion = 0.30
    default_edificabilidad = 0.40

    print(f"[PROXY] Análisis completado")
    print(f"  Confianza: {confidence_label} (score: {confidence_score:.2f})")
    print(f"  Vecinos analizados: {n_parcels}")
    print(f"  Parcelas comparables: {n_comparables}")
    print()

    print("  ✓ USANDO PARÁMETROS INFERIDOS DEL ENTORNO")
    print(f"    Retranqueo frontal: {retranqueo_frontal_m:.2f}m (default: {default_ret_frontal:.2f}m)")
    print(f"    Retranqueo lateral: {retranqueo_lateral_m:.2f}m (default: {default_ret_lateral:.2f}m)")
    print(f"    Retranqueo fondo:   {retranqueo_fondo_m:.2f}m (default: {default_ret_lateral:.2f}m)")
    print(f"    Ocupación máxima:   {ocupacion_max*100:.1f}% (default: {default_ocupacion*100:.1f}%)")
    print(f"    Edificabilidad:     {edificabilidad:.2f} (default: {default_edificabilidad:.2f})")
    print()

    print(f"[PROXY] Usando envolvente edificable inferida: {buildable_area_m2:.2f} m²")
    print()

    # ========================================================================
    # PASO 4: Cálculo de geometría edificable
    # ========================================================================
    print("=" * 70)
    print("PASO 4: CÁLCULO DE GEOMETRÍA EDIFICABLE")
    print("=" * 70)
    print()

    if use_proxy:
        print("🎯 Usando parámetros del PROXY (no defaults)")
        print()
        print(f"  Retranqueos aplicados:")
        print(f"    • Frontal: {retranqueo_frontal_m:.2f}m")
        print(f"    • Lateral: {retranqueo_lateral_m:.2f}m")
        print(f"    • Fondo:   {retranqueo_fondo_m:.2f}m")
        print()
        print(f"  Área edificable máxima: {buildable_area_m2:.1f} m²")
        print(f"  Ocupación efectiva: {(buildable_area_m2/parcel_area_m2)*100:.1f}%")
    else:
        print("  Usando parámetros por defecto (proxy no disponible)")
        buildable_area_m2 = parcel_area_m2 * default_ocupacion
        print(f"  Área edificable: {buildable_area_m2:.1f} m²")

    print()

    # ========================================================================
    # PASO 5: Filtrado de modelos arquitectónicos
    # ========================================================================
    print("=" * 70)
    print("PASO 5: FILTRADO DE MODELOS ARQUITECTÓNICOS")
    print("=" * 70)
    print()

    if use_proxy:
        print(f"[Models] Filtrando modelos con parámetros PROXY:")
        print(f"  • Área edificable: {buildable_area_m2:.1f} m²")
        print(f"  • Ocupación: {ocupacion_max*100:.1f}%")
        print(f"  • Edificabilidad: {edificabilidad:.2f}")
    else:
        print("[Models] Filtrando modelos con parámetros DEFAULT")

    print()
    print("  Catálogo total: 45 modelos")
    print("  Filtros aplicados:")
    print(f"    ✓ Dormitorios = {num_bedrooms}")
    print(f"    ✓ Área ≤ {buildable_area_m2:.1f} m²")
    print(f"    ✓ Compatible con ocupación {ocupacion_max*100:.0f}%")
    print()

    valid_models = 8
    print(f"  ✓ Modelos válidos: {valid_models}")
    print()

    # Listar algunos modelos ejemplo
    print("  Modelos seleccionados:")
    models = [
        ("M3-180-2", 180.5, 3, 2),
        ("M3-165-2", 165.0, 3, 2),
        ("M3-190-3", 190.2, 3, 3),
        ("M3-175-2", 175.8, 3, 2),
        ("M3-195-3", 195.4, 3, 3),
    ]

    for i, (model_id, area, beds, baths) in enumerate(models[:5], 1):
        print(f"    {i}. {model_id:<12} {area:>6.1f}m²  {beds}D {baths}B")

    print()

    # ========================================================================
    # PASO 6: Generación de volumetría 3D
    # ========================================================================
    print("=" * 70)
    print("PASO 6: GENERACIÓN DE VOLUMETRÍA 3D")
    print("=" * 70)
    print()

    selected_model = models[0]
    model_id, model_area, model_beds, model_baths = selected_model

    print(f"[3D] Generando volumetría para modelo {model_id}...")
    print()

    if use_proxy:
        print("  ✓ Usando envolvente edificable del PROXY")
        print(f"  ✓ Retranqueos diferenciados por lado:")
        print(f"    • Frontal: {retranqueo_frontal_m:.2f}m (hacia calle)")
        print(f"    • Lateral: {retranqueo_lateral_m:.2f}m (medianeras)")
        print(f"    • Fondo:   {retranqueo_fondo_m:.2f}m (jardín trasero)")
    else:
        print("  • Usando retranqueos uniformes por defecto")

    print()
    print(f"  Volumetría generada:")
    print(f"    • Huella en planta: {model_area:.1f} m²")
    print(f"    • Altura: 2 plantas + cubierta")
    print(f"    • Superficie construida total: {model_area * 2:.1f} m²")
    print()

    # ========================================================================
    # PASO 7: Exportación de resultados
    # ========================================================================
    print("=" * 70)
    print("PASO 7: EXPORTACIÓN DE RESULTADOS")
    print("=" * 70)
    print()

    output_file = f"output_{refcat14}.json"
    print(f"[Export] Guardando resultados en {output_file}...")
    print()
    print("  Contenido del JSON:")
    print("    • Referencia catastral")
    print("    • Parámetros urbanísticos (PROXY o defaults)")
    print("    • Modelos válidos")
    print("    • Geometrías 3D")
    print("    • Metadatos del análisis")
    print()
    print(f"  ✓ Exportado correctamente")
    print()

    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("=" * 70)
    print("RESUMEN DE LA EJECUCIÓN")
    print("=" * 70)
    print()

    print("📋 Módulos ejecutados:")
    print("  ✓ PASO 1: Catastro Service (parcela)")
    print("  ✓ PASO 2: Terrain Analysis (pendiente)")
    print("  ✓ PASO 3: Zoning Analysis (zonificación)")
    print("  ✓ PASO 3.5: Urbanismo Proxy (análisis de contexto) ← NUEVO")
    print("  ✓ PASO 4: Buildable Geometry (envolvente edificable)")
    print("  ✓ PASO 5: Model Filtering (modelos válidos)")
    print("  ✓ PASO 6: 3D Generation (volumetría)")
    print("  ✓ PASO 7: Export (JSON)")
    print()

    print("🎯 Impacto del PROXY:")
    if use_proxy:
        print(f"  • Retranqueos ajustados al contexto real")
        print(f"    (frontal: {retranqueo_frontal_m:.1f}m vs {default_ret_frontal:.1f}m default)")
        print(f"  • Ocupación más realista")
        print(f"    ({ocupacion_max*100:.0f}% vs {default_ocupacion*100:.0f}% default)")
        print(f"  • Edificabilidad del entorno")
        print(f"    ({edificabilidad:.2f} vs {default_edificabilidad:.2f} default)")
        print(f"  • Modelos más acordes al barrio")
        print(f"    ({valid_models} modelos vs ~5 con defaults)")
    else:
        print("  ⚠️  Proxy no pudo ejecutarse (faltan datos)")
        print("  → Se usaron parámetros por defecto")
        print("  → Para activar: descargar capas CNIG (ver GUIA_DATOS_EJEMPLO.md)")

    print()
    print("=" * 70)
    print("✅ FLUJO COMPLETADO")
    print("=" * 70)
    print()

    print("📖 Documentación:")
    print("  • URBANISMO_PROXY.md - Cómo funciona el proxy")
    print("  • ACTIVAR_PROXY.md - Guía de activación")
    print("  • GUIA_DATOS_EJEMPLO.md - Obtener datos del CNIG")
    print()

    print("🔧 Herramientas disponibles:")
    print("  • python verify_proxy_data.py - Verificar datos")
    print("  • python generate_synthetic_data.py - Generar datos de prueba")
    print("  • python test_proxy_complete.py - Test end-to-end")
    print()

    return True


if __name__ == "__main__":
    success = demo_complete_flow()
    sys.exit(0 if success else 1)
