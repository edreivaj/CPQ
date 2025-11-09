#!/bin/bash
# Setup script para CPQ - Buildlovers

echo "=============================================="
echo "CPQ - Calculadora de Implantación v4.5"
echo "Setup y verificación del entorno"
echo "=============================================="
echo ""

# Verificar Python
echo "[1/4] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Por favor, instala Python 3.8 o superior."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION encontrado"
echo ""

# Verificar pip
echo "[2/4] Verificando pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip no encontrado. Por favor, instala pip."
    exit 1
fi

PIP_VERSION=$(pip3 --version 2>&1 | awk '{print $2}')
echo "✅ pip $PIP_VERSION encontrado"
echo ""

# Instalar dependencias
echo "[3/4] Instalando dependencias..."
echo "Esto puede tardar varios minutos..."
echo ""

pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencias instaladas correctamente"
else
    echo ""
    echo "❌ Error instalando dependencias"
    exit 1
fi
echo ""

# Verificar imports
echo "[4/4] Verificando instalación..."
python3 -c "
import sys
try:
    import geopandas
    import shapely
    import pyproj
    import rasterio
    import numpy
    import requests
    print('✅ Todas las dependencias verificadas')
    sys.exit(0)
except ImportError as e:
    print(f'❌ Error importando: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "=============================================="
    echo "✅ Setup completado con éxito"
    echo "=============================================="
    echo ""
    echo "Para ejecutar el programa:"
    echo "  python3 main.py"
    echo "  o"
    echo "  ./main.py"
    echo ""
else
    echo ""
    echo "❌ Setup incompleto. Revisa los errores anteriores."
    exit 1
fi
