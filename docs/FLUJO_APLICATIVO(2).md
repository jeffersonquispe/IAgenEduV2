# 🏁 Guía Funcional y Reglas de Negocio: IA-GEN-EDU

Este documento detalla el funcionamiento de la aplicación desde una perspectiva de **usuario y negocio**. Aquí se explica el significado de cada campo, las reglas que rigen las decisiones del sistema y cómo las entradas del docente moldean los documentos finales de planificación.

---

## 🏗️ 1. Flujo Lógico de Planificación

El aplicativo sigue la secuencia pedagógica estándar del Currículo Nacional: desde la visión macro (Unidad) hasta la micro (Sesión).

1.  **Fase de Definición**: El usuario establece el "universo" de trabajo (Área, Grado, Competencia).
2.  **Fase de Propuesta**: El sistema sugiere temas y el usuario define los hitos de aprendizaje (Producto, Sesiones).
3.  **Fase de Generación de Unidad**: La IA propone una estructura de largo plazo.
4.  **Fase de Especialización**: El usuario toma una pieza de la unidad y decide **cómo** enseñarla (Metodología activa).

---

## 📥 2. Diccionario Funcional de Entradas (Inputs)

Cada campo en el formulario representa una decisión pedagógica con reglas específicas.

### 2.1 Sección de Configuración Base
- **Institución Educativa**: 
  - *Significado*: Nombre del centro para el encabezado oficial.
  - *Regla*: Es texto libre, pero se recomienda usar el nombre legal para que el archivo .docx sea válido administrativamente.
- **Área Curricular**:
  - *Significado*: El dominio del conocimiento (Matemática, Comunicación, etc.).
  - *Regla de Negocio*: Es el "Filtro Maestro". Al cambiarlo, el sistema invalida las competencias previas para asegurar que no se mezclen áreas distintas.
- **Grado y Sección**:
  - *Significado*: El público objetivo del aprendizaje.
  - *Influencia*: Determina el nivel de los estándares que la IA inyectará automáticamente en las tablas.

### 2.2 Sección de Contenido Pedagógico
- **Competencias (Selección CNEB)**:
  - *Significado*: Las capacidades que el estudiante desarrollará.
  - *Regla*: El sistema permite solo las vinculadas al área seleccionada.
  - *Impacto*: Si seleccionas 2 competencias, la unidad generará una matriz que combine ambas en el propósito de aprendizaje.
- **Tematícas (Temas del Curso)**:
  - *Significado*: Los contenidos específicos que se abordarán.
  - *Relación*: Estos temas se distribuyen a lo largo de la secuencia de sesiones. Actúan como el "índice" de contenidos del documento.
- **Número de Sesiones**:
  - *Significado*: La duración temporal de la unidad.
  - *Regla*: Define cuántas filas tendrá la tabla de organización de la unidad.

### 2.3 Sección de Evaluación y Metodología
- **Producto Final de Unidad**:
  - *Significado*: La evidencia tangible del aprendizaje (ej. un ensayo, un prototipo, una maqueta).
  - *Relación Crítica*: Este campo **gobierna la rúbrica**. Los niveles de logro de la rúbrica se redactarán específicamente para medir *este* producto.
- **Metodología (Solo en Sesión)**:
  - *Significado*: El enfoque didáctico (ERCA, ABP, Aula Invertida).
  - *Influencia*: Es la "instrucción de estilo". Cambia la estructura de la sesión:
    - *ABP*: El inicio se centra en el planteamiento de un problema real.
    - *Aula Invertida*: El inicio se centra en verificar lo estudiado previamente.

---

## 📤 3. Anatomía Funcional de las Salidas (Outputs)

Los documentos generados deben cumplir con estándares de estructura y contenido para ser útiles al docente.

### 3.1 La Unidad Didáctica (.docx)
Es el documento de visión general. Incluye:
- **Título de la Unidad**: Generado por la IA basándose en los temas y el área. Debe ser motivador.
- **Situación Significativa**: Un texto narrativo que plantea un reto contextualizado.
- **Matriz de Propósitos**: 
  - *Condición*: Debe incluir Competencia, Capacidad, Desempeño y Criterio. 
  - *Relación*: El Desempeño se adapta según el Grado elegido.
- **Secuencia de Sesiones**: Un resumen de cada clase futura. 
  - *Regla*: No debe haber temas repetidos en sesiones distintas.
- **Rúbrica de Unidad**: Escala de valoración del Producto Final.

### 3.2 La Sesión de Aprendizaje (.docx)
Es el documento operativo para el aula. Se centra en:
- **Momentos de la Sesión**:
  - **Inicio**: Motivación y recojo de saberes.
  - **Desarrollo**: Aplicación práctica según la **Metodología**.
  - **Cierre**: Reflexión sobre lo aprendido (Metacognición).
- **Materiales**: Sugerencia de recursos físicos o virtuales necesarios.
- **Rúbrica de la Sesión**: Versión simplificada de la evaluación para la clase de hoy.

---

## ⚖️ 4. Reglas de Negocio y Relaciones Input-Output

| Entrada (Input) | Proceso / Relación | Salida (Output) |
| :--- | :--- | :--- |
| **Área + Temas** | La IA construye una narrativa coherente. | **Situación Significativa** |
| **Grado** | Filtra estándares del CNEB. | **Criterios de Evaluación** |
| **Producto Final** | Define las dimensiones de calidad. | **Rúbrica Analítica** |
| **Metodología** | Cambia los pasos de la secuencia | **Mismos de Aprendizaje/Desarrollo** |
| **Núm. Sesiones** | Divide el tiempo equitativamente. | **Cronograma de la Unidad** |

---

## 💎 5. Condiciones de Calidad del Contenido

Para que el sistema entregue un documento válido, se verifican las siguientes condiciones:
1.  **Coherencia Horizontal**: El título de la sesión debe estar directamente relacionado con la competencia seleccionada.
2.  **Progresividad**: Los niveles de la rúbrica (C, B, A, AD) deben mostrar un avance claro en la complejidad de la tarea.
3.  **Factibilidad**: Las actividades propuestas deben ser realizables en el tiempo de duración especificado (ej. 90 minutos).
4.  **Formato**: El output debe estar contenido enteramente en tablas. Si la IA intenta generar párrafos sueltos, el sistema los "encapsula" en celdas de tabla automáticamente.

---

## 🕹️ 6. Estado y Continuidad del Flujo

- **Persistencia**: La aplicación "recuerda" la Unidad mientras generas la Sesión. Esto evita que tengas que volver a escribir los temas o competencias.
- **Independencia**: Puedes generar múltiples sesiones diferentes para una misma unidad, probando distintas metodologías para cada una.
- **Validación Final**: El botón de descarga solo aparece si el "Motor de Reglas" confirma que la tabla generada es consistente y no contiene errores de estructura.

---

## 🎭 7. Escenarios de Ejemplo: Influencia de Decisiones

Para entender mejor cómo el sistema "razona", veamos dos ejemplos de cómo las entradas cambian radicalmente la salida.

### Escenario A: Proyecto Tecnológico (ABP)
- **Inputs**: Área: Ciencia y Tecnología | Competencia: Diseña soluciones tecnológicas | Metodología: ABP.
- **Comportamiento del Sistema**:
  - La **Situación Significativa** planteará un problema ambiental o social.
  - La **Secuencia Didáctica** guiará al alumno por pasos de: 1. Determinación de la solución, 2. Diseño del prototipo, 3. Validación.
  - La **Rúbrica** evaluará la funcionalidad y el impacto del modelo construido.

### Escenario B: Comprensión Lectora (Aula Invertida)
- **Inputs**: Área: Comunicación | Competencia: Lee diversos tipos de textos | Metodología: Aula Invertida.
- **Comportamiento del Sistema**:
  - La **Situación Significativa** se centrará en la necesidad de analizar críticamente una fuente de información.
  - El **Inicio de la Sesión** no explicará el texto, sino que lanzará preguntas sobre la lectura previa realizada en casa.
  - El **Desarrollo** se dedicará íntegramente a debates grupales y análisis profundo.

---

## 🛠️ 8. Mantenimiento y Extensibilidad Profesional

El diseño funcional de la aplicación está preparado para crecer según las necesidades del docente:
- **Actualización Curricular**: Se pueden integrar nuevas competencias o estándares sin cambiar la lógica de la IA.
- **Personalización Institucional**: Las reglas de negocio (como los valores institucionales) son módulos independientes que se pueden adaptar a diferentes visiones educativas.
- **Flexibilidad de Exportación**: El motor está diseñado para asegurar que, sin importar cuán creativo sea el contenido de la IA, el archivo Word siempre conserve la limpieza y el orden requeridos por la administración escolar.

---
*Este manual garantiza que cada bit de información ingresada se convierta en una herramienta pedagógica valiosa, coherente y lista para el aula.*
