#!/usr/bin/env python3
"""
Script de verificación rápida - CPQ v4.5
Verifica que todos los módulos se importan correctamente
"""

print("="*60)
print("CPQ v4.5 - Verificación de Módulos")
print("="*60)
print()

try:
    print("[1/7] Verificando configuración...")
    from cpq.config import CFG
    print(f"  ✅ Config OK - {len(vars(CFG))} parámetros cargados")

    print("\n[2/7] Verificando modelos...")
    from cpq.models import MODELS_DATABASE, CONSTRUCTION_PRICES, EXTRAS_CATALOG
    print(f"  ✅ Modelos OK - {len(MODELS_DATABASE)} casas disponibles")
    print(f"  ✅ Precios OK - {len(CONSTRUCTION_PRICES)} sistemas constructivos")
    print(f"  ✅ Extras OK - {len(EXTRAS_CATALOG)} extras disponibles")

    print("\n[3/7] Verificando servicios...")
    from cpq.services import CatastroService, MDTService, OSMService
    print("  ✅ CatastroService OK")
    print("  ✅ MDTService OK")
    print("  ✅ OSMService OK")

    print("\n[4/7] Verificando análisis...")
    from cpq.analysis import (
        ParcelBoundaryAnalyzer,
        compute_volume_metrics,
        calc_pendiente,
        compute_horizontal_access_costs
    )
    print("  ✅ ParcelBoundaryAnalyzer OK")
    print("  ✅ Funciones de terreno OK")
    print("  ✅ Funciones de costes OK")

    print("\n[5/7] Verificando utilidades...")
    from cpq.utils import bbox_from_gdf, create_house_pad, compute_monthly_payment
    print("  ✅ Utilidades geométricas OK")
    print("  ✅ Utilidades financieras OK")

    print("\n[6/7] Verificando CLI...")
    from cpq.cli import select_model_interactive, select_construction_system
    print("  ✅ CLI OK")

    print("\n[7/7] Verificando filtrado de modelos...")
    from cpq.model_filter import filter_valid_models
    print("  ✅ Model filter OK")

    print("\n" + "="*60)
    print("✅ TODOS LOS MÓDULOS IMPORTADOS CORRECTAMENTE")
    print("="*60)
    print()
    print("El programa está listo para ejecutarse.")
    print("Ejecuta: python main.py")
    print()

except ImportError as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPor favor, instala las dependencias:")
    print("  pip install -r requirements.txt")
    print("  o ejecuta: ./setup.sh")
    exit(1)
except Exception as e:
    print(f"\n❌ ERROR INESPERADO: {e}")
    exit(1)
