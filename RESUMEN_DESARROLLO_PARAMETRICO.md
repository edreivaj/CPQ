# Resumen de Desarrollo - Sistema Paramétrico CPQ

## Contexto

El proyecto CPQ (Calculadora de Presupuesto y Cualificación) de Buildlovers es un sistema Python que calcula presupuestos de implantación de viviendas en parcelas españolas. Obtiene datos del Catastro, analiza topografía, normativa urbanística y calcula costes de construcción.

**Problema inicial:** El sistema usaba un catálogo fijo de 6 modelos de casa predefinidos. Si ningún modelo encajaba en la parcela, no había alternativa.

**Solución implementada:** Añadir un **modo paramétrico** que permite diseñar viviendas a medida dentro de los límites urbanísticos calculados automáticamente.

---

## Lo que se implementó

### 1. Nuevo módulo `cpq/parametric/`

Se crearon 6 archivos nuevos:

#### `cpq/parametric/__init__.py`
Exporta todas las clases públicas del módulo.

#### `cpq/parametric/config_parametric.py`
Estructuras de datos principales:

```python
class ShapeType(Enum):
    BAR = "_"      # Barra rectangular
    I_SHAPE = "I"  # Rectangular alargada
    L_SHAPE = "L"  # Forma en L
    U_SHAPE = "U"  # Forma en U

@dataclass
class TechnicalConstraints:
    min_wing_width_m: float = 3.5      # Ancho mínimo de ala
    min_stair_width_m: float = 0.90    # Ancho mínimo escalera
    min_stair_length_m: float = 3.0    # Largo mínimo escalera
    max_aspect_ratio: float = 4.0      # Proporción máxima largo/ancho
    # ... más restricciones técnicas

@dataclass
class FloorConfig:
    floor_number: int           # 0=PB, 1=P1
    area_m2: float
    shape: ShapeType
    envelope_width_m: float
    envelope_length_m: float
    wing_a_width_m: float       # Para formas L y U
    wing_a_length_m: float
    geometry: Polygon

@dataclass
class ParametricConfig:
    num_floors: int
    ground_floor: FloorConfig
    first_floor: FloorConfig
    total_footprint_m2: float
    total_built_m2: float
    estimated_bedrooms: int
    estimated_bathrooms: int
    is_valid: bool
    validation_errors: List[str]

@dataclass
class ParametricLimits:
    parcel_area_m2: float
    buildable_box: Polygon
    max_footprint_m2: float      # Ocupación máxima
    max_built_area_m2: float     # Edificabilidad máxima
    box_width_m: float
    box_length_m: float
    suggested_pb_m2: float
    suggested_p1_m2: float
    suggested_shape: ShapeType
```

#### `cpq/parametric/limits_calculator.py`
Calcula los límites máximos permitidos:

```python
class ParametricLimitsCalculator:
    def calculate_limits(self, parcel_area_m2, buildable_geometry, ocupacion_pct, edificabilidad):
        # Calcula:
        # - max_footprint = parcel_area × ocupacion - parking
        # - max_built = parcel_area × edificabilidad
        # - Dimensiones de la caja edificable (minimum rotated rectangle)
        # - Sugerencia óptima para 2 plantas
        # - Forma recomendada según proporciones
```

#### `cpq/parametric/shape_generator.py`
Genera geometrías de planta:

```python
class ShapeGenerator:
    def generate_bar(width, length) -> Polygon
    def generate_L(wing_a_w, wing_a_l, wing_b_w, wing_b_l) -> Polygon
    def generate_U(wing_a, wing_b, connector) -> Polygon
    
    def create_floor_config(floor_number, area_m2, shape, box_width, box_length) -> FloorConfig
```

#### `cpq/parametric/validator.py`
Valida configuraciones y estima programa funcional:

```python
class ParametricValidator:
    def validate_config(config, limits) -> Tuple[bool, List[str]]:
        # Valida:
        # - Ocupación no excede máximo
        # - Edificabilidad no excede máximo
        # - Dimensiones caben en caja edificable
        # - Restricciones técnicas (anchos mínimos)
        # - Proporciones razonables
        # - Espacio para escalera si 2 plantas

class ProgramEstimator:
    def estimate_program(total_m2, num_floors) -> Tuple[int, int]:
        # Estima dormitorios y baños según superficie
```

#### `cpq/parametric/cost_adapter.py`
Adapta la configuración paramétrica al sistema de costes existente:

```python
class ParametricModelAdapter:
    @staticmethod
    def to_model_dict(config: ParametricConfig) -> Dict:
        # Convierte a formato compatible con compute_construction_cost(), etc.
        return {
            "model_id": f"PARAM_{config.config_id}",
            "nombre": f"Paramétrico {shape} {m2}m²",
            "superficie_m2": config.total_built_m2,
            "superficie_huella_m2": config.total_footprint_m2,
            "numero_dormitorios": config.estimated_bedrooms,
            # ...
        }
```

### 2. Nueva interfaz CLI `cpq/cli_parametric.py`

Funciones de interacción con el usuario:

```python
def select_mode() -> str:
    # Muestra: [1] Catálogo | [2] Paramétrico
    # Retorna "catalog" o "parametric"

def display_parametric_limits(limits):
    # Muestra límites calculados (ocupación, edificabilidad, sugerencia)

def display_parametric_config(config):
    # Muestra configuración actual (PB, P1, forma, validación)

def get_parametric_input(limits) -> Tuple[float, float, ShapeType]:
    # Solicita al usuario: PB m², P1 m², forma

def confirm_use_suggested() -> bool
def confirm_parametric_config(config) -> bool
```

### 3. Modificaciones a `main.py`

Se añadieron imports:
```python
from cpq.cli_parametric import (
    select_mode, display_parametric_limits, display_parametric_config,
    get_parametric_input, confirm_use_suggested, confirm_parametric_config,
)
from cpq.parametric import (
    ParametricLimitsCalculator, ShapeGenerator, ParametricValidator,
    ParametricModelAdapter, TechnicalConstraints, ParametricConfig,
)
from cpq.parametric.validator import ProgramEstimator
```

Se reemplazó el PASO 5 (filtrar modelos) y PASO 6 (seleccionar modelo) con un nuevo flujo:

```python
mode = select_mode()

if mode == "parametric":
    # Calcular límites
    limits = limits_calc.calculate_limits(parcel_area, buildable_geometry, ...)
    display_parametric_limits(limits)
    
    # Generar configuración sugerida
    suggested_config = ...
    display_parametric_config(suggested_config)
    
    if confirm_use_suggested():
        parametric_config = suggested_config
    else:
        # Usuario personaliza PB, P1, forma
        pb_m2, p1_m2, shape = get_parametric_input(limits)
        parametric_config = ...
    
    # Convertir a modelo para costes
    selected_model = ParametricModelAdapter.to_model_dict(parametric_config)

else:
    # Flujo catálogo existente (sin cambios)
    valid_models = filter_valid_models(...)
    selected_model = select_model_interactive(valid_models)
```

---

## Flujo de usuario resultante

```
1. Usuario introduce referencia catastral
2. Usuario indica número de dormitorios
3. Sistema obtiene parcela del Catastro
4. Sistema analiza contexto urbanístico (proxy)
5. Sistema calcula caja edificable

6. NUEVO: Usuario elige modo
   ┌─────────────────────────────────────────────────┐
   │ MODO DE CONFIGURACIÓN                          │
   │   [1] Catálogo - Seleccionar modelo predefinido│
   │   [2] Paramétrico - Diseñar a medida           │
   └─────────────────────────────────────────────────┘

7a. Si CATÁLOGO: flujo existente (filtrar → seleccionar)

7b. Si PARAMÉTRICO:
   ┌─────────────────────────────────────────────────┐
   │ LÍMITES MÁXIMOS CALCULADOS                     │
   │   Parcela: 800.00 m²                           │
   │   Máx. ocupación (huella): 227.50 m²           │
   │   Máx. edificabilidad (total): 320.00 m²       │
   │                                                 │
   │ Sugerencia óptima (2 plantas):                 │
   │   Planta Baja: 160.00 m²                       │
   │   Planta Primera: 160.00 m²                    │
   │   Forma recomendada: L                         │
   └─────────────────────────────────────────────────┘
   
   Usuario acepta sugerencia o personaliza (PB m², P1 m², forma)
   Sistema valida en tiempo real
   
8. Continúa al cálculo de costes (igual para ambos modos)
```

---

## Archivos creados/modificados

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `cpq/parametric/__init__.py` | Nuevo | 30 |
| `cpq/parametric/config_parametric.py` | Nuevo | 101 |
| `cpq/parametric/limits_calculator.py` | Nuevo | 110 |
| `cpq/parametric/shape_generator.py` | Nuevo | 203 |
| `cpq/parametric/validator.py` | Nuevo | 189 |
| `cpq/parametric/cost_adapter.py` | Nuevo | 39 |
| `cpq/cli_parametric.py` | Nuevo | 183 |
| `main.py` | Modificado | +150, -28 |
| **TOTAL** | | ~1005 líneas nuevas |

---

## Bugs conocidos pendientes de corregir

### 1. Validación de geometría (PRIORITARIO)

**Archivo:** `cpq/parametric/validator.py`

**Problema:** La validación "La huella de PB no cabe en la caja edificable" falla siempre porque compara posiciones geométricas (la casa se genera en 0,0 pero la caja está en coordenadas UTM reales).

**Solución:** Cambiar para validar por dimensiones:

```python
# ANTES:
if not limits.buildable_box.buffer(0.1).contains(config.ground_floor.geometry):
    errors.append("La huella de PB no cabe en la caja edificable")

# DESPUÉS:
if config.ground_floor.envelope_width_m > limits.box_width_m:
    errors.append(f"Ancho de PB excede caja edificable")
if config.ground_floor.envelope_length_m > limits.box_length_m:
    errors.append(f"Largo de PB excede caja edificable")
```

### 2. Formas L y U generan dimensiones excesivas

**Archivo:** `cpq/parametric/shape_generator.py`

Las funciones `_create_L_floor()` y `_create_U_floor()` no respetan los límites de la caja edificable. Deben ajustar proporciones de las alas.

### 3. Estimación de dormitorios excesiva

**Archivo:** `cpq/parametric/validator.py`, clase `ProgramEstimator`

Da 6 dormitorios para 180m² (excesivo). Ajustar fórmula para ~20-25 m²/dormitorio.

---

## Commits realizados

```
20118be feat: añadir modo paramétrico para configuración de viviendas a medida
d6cec6f docs: añadir prompt para continuar desarrollo en local con Claude Code
```

**Rama:** `claude/github-local-testing-guide-gEjoT`

---

## Cómo probar

```bash
python main.py
```

1. Referencia catastral: `2700406DF1920S0001KB`
2. Dormitorios: `3`
3. Modo: `[2] Paramétrico`
4. Verificar que muestra límites y permite configurar

---

## Próximos pasos sugeridos

1. Corregir el bug de validación de geometría
2. Mejorar generación de formas L y U
3. Ajustar estimación de dormitorios
4. Añadir validación de dimensiones mínimas por forma
5. Tests unitarios para el módulo paramétrico
6. Merge a main cuando esté estable

---

Este resumen cubre todo el trabajo realizado. El código está en la rama `claude/github-local-testing-guide-gEjoT` listo para continuar el desarrollo.
