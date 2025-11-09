# CPQ - Calculadora de Presupuesto y Cualificación

**Buildlovers - Sistema de Cálculo de Implantación v4.5**

Sistema modular para calcular presupuestos de implantación de viviendas en parcelas, considerando normativa urbanística, topografía, costes de construcción y financiación.

---

## 📁 Estructura del Proyecto

```
CPQ/
├── cpq/                          # Paquete principal
│   ├── __init__.py              # Inicialización del paquete
│   ├── config.py                # Configuración y constantes
│   ├── models.py                # Modelos de datos y catálogos
│   ├── model_filter.py          # Filtrado de modelos válidos
│   ├── cli.py                   # Interfaz de línea de comandos
│   │
│   ├── services/                # Servicios externos
│   │   ├── __init__.py
│   │   ├── catastro.py         # Servicio de Catastro
│   │   ├── mdt.py              # Servicio de MDT (topografía)
│   │   └── osm.py              # Servicio de OpenStreetMap
│   │
│   ├── analysis/                # Módulos de análisis
│   │   ├── __init__.py
│   │   ├── boundaries.py       # Análisis de límites y vallado
│   │   ├── terrain.py          # Análisis topográfico
│   │   └── costs.py            # Cálculos de costes
│   │
│   └── utils/                   # Utilidades
│       ├── __init__.py
│       ├── geometry.py         # Utilidades geométricas
│       └── finance.py          # Cálculos financieros
│
├── main.py                      # Script principal ejecutable
└── requirements.txt             # Dependencias del proyecto
```

---

## 🚀 Instalación

### Requisitos

- Python >= 3.8
- pip

### Pasos

1. **Clonar o descargar el repositorio**

2. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

3. **Ejecutar el programa**

```bash
python main.py
# O en sistemas Unix/Linux:
./main.py
```

---

## 📋 Dependencias

El proyecto requiere las siguientes bibliotecas Python:

- **geopandas** >= 0.12.0 - Procesamiento de datos geoespaciales
- **shapely** >= 2.0.0 - Manipulación de geometrías
- **pyproj** >= 3.4.0 - Transformaciones de coordenadas
- **rasterio** >= 1.3.0 - Procesamiento de datos raster (MDT)
- **numpy** >= 1.23.0 - Computación numérica
- **requests** >= 2.28.0 - Peticiones HTTP a servicios externos

---

## 📖 Uso

### Flujo básico

1. **Introducir referencia catastral**: El programa solicita la referencia catastral de la parcela (14 caracteres)

2. **Número de dormitorios**: Especificar cuántos dormitorios se desean

3. **Seleccionar modelo**: El sistema filtra modelos válidos según normativa y presenta opciones

4. **Sistema constructivo**: Elegir entre steelframe, madera u hormigón

5. **Nivel de acabado**: Seleccionar essencial, premium o excellence

6. **Extras opcionales**: Añadir piscinas, pérgolas, placas solares, etc.

7. **Financiación**: Configurar parámetros de hipoteca

### Ejemplo de ejecución

```bash
$ python main.py

============================================================
Buildlovers — Calculadora de Implantación v4.5
============================================================

Introduce la referencia catastral completa: 1234567AB1234C
Número de dormitorios deseado: 3

[Catastro] Obteniendo parcela 1234567AB1234C...
Parcela obtenida. Área: 800.00 m²

--- Analizando Límites ---
...
```

---

## 🧩 Arquitectura Modular

### Módulos principales

#### **config.py**
Centraliza toda la configuración del sistema:
- URLs de servicios (Catastro, MDT, OSM)
- Parámetros geométricos
- Costes de construcción
- Normativa urbanística
- Matrices de costes

#### **models.py**
Define modelos de datos:
- Catálogo de modelos de casas (MODELS_DATABASE)
- Precios de construcción por sistema y nivel
- Catálogo de extras (EXTRAS_CATALOG)
- Dataclass ParcelAnalysisResult

#### **services/**
Servicios externos para obtención de datos:
- **CatastroService**: Consultas WFS al Catastro
- **MDTService**: Descarga de Modelo Digital del Terreno
- **OSMService**: Consultas a OpenStreetMap (Overpass API)

#### **analysis/**
Lógica de análisis:
- **boundaries.py**: ParcelBoundaryAnalyzer para clasificación de límites frontal/lateral
- **terrain.py**: Análisis topográfico, cálculo de volúmenes, pendientes, muros
- **costs.py**: Funciones de cálculo de costes por partidas

#### **utils/**
Utilidades generales:
- **geometry.py**: Operaciones geométricas (bbox, huella, conversiones)
- **finance.py**: Cálculos financieros (cuotas hipoteca)

#### **cli.py**
Interfaz de línea de comandos para interacción con usuario

#### **model_filter.py**
Filtrado de modelos válidos según normativa urbanística

---

## 🔧 Configuración

### Modificar costes

Editar el archivo `cpq/config.py`:

```python
COSTE_LOSA_M2 = 180.00
COSTE_DESMONTE_M3 = 20.50
COSTE_TERRAPLEN_M3 = 35.00
...
```

### Añadir modelos de casa

Editar el archivo `cpq/models.py`:

```python
MODELS_DATABASE = [
    {
        "model_id": "BL_NUEVO_01",
        "nombre": "Nuevo Modelo",
        "numero_dormitorios": 3,
        "numero_baños": 2,
        "plantas": 1,
        "superficie_m2": 110,
        "huella_ancho_m": 10.0,
        "huella_largo_m": 11.0,
        "maqueta_ref_id": "MAQ_NUEVO_01"
    },
    ...
]
```

### Modificar normativa

En `cpq/config.py`:

```python
OCUPACION_PORCENTAJE = 30.0        # Ocupación máxima
EDIFICABILIDAD_M2T_M2S = 0.4       # Edificabilidad
RETRANQUEO_FRONTAL_M = 5.0         # Retranqueo frontal
RETRANQUEO_LATERAL_M = 3.0         # Retranqueo lateral
```

---

## 📊 Partidas de Coste

El sistema calcula las siguientes partidas:

1. **Construcción**: Según sistema (steelframe/madera/hormigón) y nivel
2. **Losa de cimentación**: Superficie de huella × coste/m²
3. **Movimiento de tierras**: Desmonte, terraplén, gestión de excedentes
4. **Contención**: Muros perimetrales + sobrecostes por pendiente
5. **Vallado**: Frontal y lateral según clasificación de límites
6. **Puerta de acceso**: Coste fijo
7. **Accesos horizontales**: Peatonal y vehicular
8. **Adaptación vertical**: Según diferencia de cota con matriz de costes
9. **Conexiones a redes**: Coste fijo
10. **Honorarios técnicos**: Arquitectura, estructuras, geotecnia, topografía, legalizaciones
11. **Extras**: Piscinas, pérgolas, solar, domótica, etc.

---

## 🛠️ Desarrollo

### Ejecutar tests

```bash
# TODO: Implementar suite de tests
pytest tests/
```

### Contribuir

1. Crear rama feature
2. Implementar cambios
3. Documentar en docstrings
4. Crear pull request

---

## 📝 Licencia

© Buildlovers - Todos los derechos reservados

---

## 🐛 Troubleshooting

### Error al descargar MDT

Si el servicio de MDT no está disponible:
- El programa continuará con volúmenes = 0
- Se asignará pendiente = 0%
- Los costes de movimiento de tierras serán 0

### Error de geometría inválida

Verificar que:
- La referencia catastral sea correcta (14 caracteres)
- La parcela exista en el Catastro
- La geometría retornada sea válida

### Timeout en servicios

Aumentar timeouts en `cpq/config.py`:

```python
CATASTRO_TIMEOUT = 60      # Aumentar si es necesario
MDT_TIMEOUT = 120
OSM_TIMEOUT = 40
```

---

## 📞 Contacto

Para soporte técnico, contactar con el equipo de desarrollo de Buildlovers.

---

**Versión**: 4.5.0
**Última actualización**: 2025
