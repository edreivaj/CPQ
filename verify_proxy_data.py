#!/usr/bin/env python3
"""
Script para verificar que los datos necesarios para el Proxy están disponibles
"""

import os
import sys


def verify_data():
    """Verifica que los archivos de datos estén listos para el proxy"""

    print("=" * 70)
    print("VERIFICACIÓN DE DATOS PARA URBANISMO PROXY")
    print("=" * 70)

    data_dir = "/home/user/CPQ/data"
    parcels_file = os.path.join(data_dir, "parcels.gpkg")
    buildings_file = os.path.join(data_dir, "buildings.gpkg")

    errors = []
    warnings = []

    # 1. Verificar directorio
    print("\n[1/5] Verificando directorio de datos...")
    if not os.path.exists(data_dir):
        print(f"  ✗ Directorio no encontrado: {data_dir}")
        print(f"\n  💡 Crear con: mkdir -p {data_dir}")
        return False
    else:
        print(f"  ✓ Directorio existe: {data_dir}")

    # 2. Verificar archivos
    print("\n[2/5] Verificando archivos...")

    if not os.path.exists(parcels_file):
        print(f"  ✗ Archivo no encontrado: {parcels_file}")
        errors.append("Falta archivo de parcelas")
    else:
        size_mb = os.path.getsize(parcels_file) / 1024 / 1024
        print(f"  ✓ Parcelas: {parcels_file} ({size_mb:.1f} MB)")

    if not os.path.exists(buildings_file):
        print(f"  ✗ Archivo no encontrado: {buildings_file}")
        errors.append("Falta archivo de edificios")
    else:
        size_mb = os.path.getsize(buildings_file) / 1024 / 1024
        print(f"  ✓ Edificios: {buildings_file} ({size_mb:.1f} MB)")

    if errors:
        print(f"\n❌ Faltan archivos necesarios:")
        for err in errors:
            print(f"   - {err}")
        print(f"\n📖 Consulta GUIA_DATOS_EJEMPLO.md para obtenerlos")
        return False

    # 3. Verificar contenido con geopandas
    print("\n[3/5] Verificando contenido geodata...")

    try:
        import geopandas as gpd
    except ImportError:
        print("  ⚠️  GeoPandas no disponible - no se puede verificar CRS")
        warnings.append("No se pudo verificar el sistema de coordenadas")
        print("\n  Instalando con: pip install geopandas")
        return True  # Los archivos existen, aunque no podemos verificarlos

    try:
        parcels = gpd.read_file(parcels_file)
        buildings = gpd.read_file(buildings_file)

        print(f"  ✓ Parcelas: {len(parcels)} geometrías")
        print(f"  ✓ Edificios: {len(buildings)} geometrías")

        if len(parcels) == 0:
            errors.append("Archivo de parcelas está vacío")
        if len(buildings) == 0:
            errors.append("Archivo de edificios está vacío")

    except Exception as e:
        print(f"  ✗ Error leyendo archivos: {e}")
        errors.append("No se pudieron leer los archivos GIS")
        return False

    # 4. Verificar CRS
    print("\n[4/5] Verificando sistema de coordenadas...")

    parcels_crs = str(parcels.crs)
    buildings_crs = str(buildings.crs)

    if "25830" in parcels_crs:
        print(f"  ✓ Parcelas en EPSG:25830 (ETRS89 UTM 30N)")
    else:
        print(f"  ⚠️  Parcelas en {parcels_crs} (esperado: EPSG:25830)")
        warnings.append(f"CRS de parcelas: {parcels_crs}")

    if "25830" in buildings_crs:
        print(f"  ✓ Edificios en EPSG:25830 (ETRS89 UTM 30N)")
    else:
        print(f"  ⚠️  Edificios en {buildings_crs} (esperado: EPSG:25830)")
        warnings.append(f"CRS de edificios: {buildings_crs}")

    # 5. Verificar extensión espacial
    print("\n[5/5] Verificando cobertura espacial...")

    try:
        parcels_bounds = parcels.total_bounds
        buildings_bounds = buildings.total_bounds

        print(f"  Parcelas bbox: {parcels_bounds}")
        print(f"  Edificios bbox: {buildings_bounds}")

        # Verificar que hay overlap
        p_minx, p_miny, p_maxx, p_maxy = parcels_bounds
        b_minx, b_miny, b_maxx, b_maxy = buildings_bounds

        overlap = not (p_maxx < b_minx or p_minx > b_maxx or
                      p_maxy < b_miny or p_miny > b_maxy)

        if overlap:
            print(f"  ✓ Las capas se superponen espacialmente")
        else:
            print(f"  ⚠️  Las capas NO se superponen")
            warnings.append("Parcelas y edificios no se solapan")

    except Exception as e:
        print(f"  ⚠️  No se pudo calcular bbox: {e}")

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)

    if errors:
        print("\n❌ ERRORES CRÍTICOS:")
        for err in errors:
            print(f"   • {err}")
        print("\n📖 Ver GUIA_DATOS_EJEMPLO.md para solucionar")
        return False

    if warnings:
        print("\n⚠️  ADVERTENCIAS:")
        for warn in warnings:
            print(f"   • {warn}")
        print("\nLos datos pueden funcionar, pero verifica que todo está correcto.")

    print("\n🎉 ¡Los datos están listos para usar el proxy!")
    print("\nPróximos pasos:")
    print("  1. Editar main.py y cambiar USE_PROXY = True (línea ~89)")
    print("  2. Ejecutar: python main.py")
    print("  3. Verificar que aparece '[PROXY] Análisis completado'")

    return True


def show_activation_instructions():
    """Muestra instrucciones para activar el proxy"""

    print("\n" + "=" * 70)
    print("CÓMO ACTIVAR EL PROXY")
    print("=" * 70)
    print("""
1. Editar main.py:

   Buscar línea ~89 y cambiar:

   USE_PROXY = False  # ← Cambiar a True

   Por:

   USE_PROXY = True   # ← ¡ACTIVADO!

2. Ejecutar main.py:

   python main.py

3. Buscar en la salida:

   [PROXY] Análisis completado
   Confianza: ALTA (score: 0.82)
   ✓ USANDO PARÁMETROS INFERIDOS DEL ENTORNO

4. Si la confianza es BAJA, ajustar ProxyConfig en main.py (línea ~140)

📚 Documentación completa: URBANISMO_PROXY.md
📋 Guía de datos: GUIA_DATOS_EJEMPLO.md
    """)


if __name__ == "__main__":
    success = verify_data()

    if success:
        show_activation_instructions()
        sys.exit(0)
    else:
        print("\n❌ Los datos no están listos aún.")
        print("\n📖 Consulta GUIA_DATOS_EJEMPLO.md para obtener los datos necesarios")
        sys.exit(1)
