# Proyecto CPQ - Buildlovers

Eres el desarrollador del sistema CPQ (Calculadora de Presupuesto y Cualificación) de Buildlovers. Es un sistema Python que calcula presupuestos de implantación de viviendas en parcelas.

## Contexto del proyecto

El sistema obtiene datos del Catastro español, analiza la parcela (topografía, límites, normativa urbanística) y calcula costes de construcción, movimiento de tierras, vallado, accesos, etc.

## Lo que se ha implementado recientemente

Se añadió un **modo paramétrico** alternativo al catálogo de modelos fijos. Permite:
- Calcular límites máximos (ocupación, edificabilidad, caja edificable)
- Sugerir configuración óptima de 2 plantas
- Permitir al usuario ajustar PB y P1 en m²
- Soportar formas: _ (barra), I, L, U
- Validar restricciones técnicas y normativas

Archivos del modo paramétrico:
- cpq/parametric/__init__.py
- cpq/parametric/config_parametric.py
- cpq/parametric/limits_calculator.py
- cpq/parametric/shape_generator.py
- cpq/parametric/validator.py
- cpq/parametric/cost_adapter.py
- cpq/cli_parametric.py
- main.py (modificado para integrar ambos modos)

## TAREAS A REALIZAR

### 1. CORREGIR BUG DE VALIDACIÓN (PRIORITARIO)

En `cpq/parametric/validator.py`, función `validate_config()`:

El problema: La validación "La huella de PB no cabe en la caja edificable" usa `limits.buildable_box.contains(config.ground_floor.geometry)` pero falla siempre porque:
- La geometría de la casa se genera en coordenadas (0,0)
- La caja edificable está en coordenadas UTM reales (ej: 500000, 4500000)

Solución: Cambiar la validación para comparar por ÁREA en lugar de posición geométrica. El código actual:

```python
if config.ground_floor and config.ground_floor.geometry:
    if not limits.buildable_box.buffer(0.1).contains(
        config.ground_floor.geometry
    ):
        errors.append("La huella de PB no cabe en la caja edificable")
```

Debe cambiarse a:

```python
if config.ground_floor:
    # Validar que las dimensiones de la huella caben en la caja edificable
    if config.ground_floor.envelope_width_m > limits.box_width_m:
        errors.append(
            f"Ancho de PB ({config.ground_floor.envelope_width_m:.1f}m) "
            f"excede caja edificable ({limits.box_width_m:.1f}m)"
        )
    if config.ground_floor.envelope_length_m > limits.box_length_m:
        errors.append(
            f"Largo de PB ({config.ground_floor.envelope_length_m:.1f}m) "
            f"excede caja edificable ({limits.box_length_m:.1f}m)"
        )
```

### 2. MEJORAR GENERACIÓN DE FORMAS L y U

En `cpq/parametric/shape_generator.py`:

Las formas L y U generan dimensiones que pueden exceder la caja edificable. Mejorar `_create_L_floor()` y `_create_U_floor()` para:
- Respetar los límites `box_width` y `box_length`
- Ajustar proporciones de las alas para que quepan

### 3. MEJORAR ESTIMACIÓN DE DORMITORIOS

En `cpq/parametric/validator.py`, clase `ProgramEstimator`:

La estimación actual da 6 dormitorios para 180m² que es excesivo. Ajustar la fórmula:
- Usar ~20-25 m² por dormitorio (incluyendo zonas comunes proporcionales)
- Máximo razonable: 5 dormitorios

### 4. AÑADIR VALIDACIÓN DE DIMENSIONES MÍNIMAS POR FORMA

Las formas L y U requieren más espacio mínimo que las barras. Añadir validación:
- Forma L: mínimo 8m en cada dirección
- Forma U: mínimo 10m en cada dirección
- Si no cabe, sugerir forma más simple

## CÓMO PROBAR

```bash
python main.py
```

Test con estos datos:
- Referencia catastral: 2700406DF1920S0001KB
- Dormitorios: 3
- Modo: [2] Paramétrico

Verificar:
1. No aparece el error falso "no cabe en caja edificable" cuando sí cabe
2. Las formas L y U respetan dimensiones de la caja
3. La estimación de dormitorios es razonable (3-4 para ~135m²)

## FLUJO DE TRABAJO

Para cada tarea:
1. Lee el archivo actual
2. Implementa el cambio
3. Prueba con `python main.py`
4. Si funciona, haz commit:
   ```bash
   git add .
   git commit -m "descripción del cambio"
   ```
5. Cuando todo esté listo, push:
   ```bash
   git push origin main
   ```

## RESTRICCIONES

- No cambies la estructura general del proyecto
- Mantén compatibilidad con el modo catálogo existente
- No añadas dependencias nuevas
- Usa el estilo de código existente (sin comentarios excesivos)

## EMPIEZA

Lee los archivos mencionados, corrige el bug de validación primero, prueba, y continúa con las mejoras. Pregúntame si algo no está claro antes de implementar cambios grandes.
