# 📋 Resumen del Proyecto - Generador Educativo AI

## ✅ Estado Actual del Proyecto

### **¿Qué ofrece la aplicación?**

La interfaz web (Streamlit) permite generar y mejorar **2 tipos de contenido educativo**:

1. **📚 Unidad Didáctica**
   - Por área curricular y grado (1° a 5° secundaria)
   - Competencia opcional del Currículo Nacional como referencia
   - Tabla con formato ITEM | CONTENIDO (competencia, capacidades, contenidos, desempeños, criterios, instrumentos, etc.)
   - **Chat integrado:** mejora el documento con instrucciones en lenguaje natural (ej.: “haz más breve la sección de criterios”, “mejora la secuencia didáctica”)
   - Exportación a TXT y DOCX

2. **📖 Sesión de Aprendizaje**
   - Basada en una unidad didáctica ya generada (se elige título de unidad y título de sesión)
   - Contenido alineado al currículo en formato de tabla
   - **Chat integrado:** mismo flujo de mejora por instrucciones
   - Exportación a TXT y DOCX

El backend (`src/core`) incluye además lógica para **programación curricular completa** y **análisis de comentarios**; ver `DETALLES_TECNICOS.md` para uso por API o futuras pantallas.

---

## ⚠️ Requisito para Generar Contenido

### **Credenciales de AWS**

El proyecto usa **Amazon Bedrock** (modelos Claude), por lo que necesitas:

1. **Crear archivo `.env`** en la raíz del proyecto:

```bash
cp env.example .env
```

2. **Editar `.env`** con tus credenciales AWS:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=tu_aws_access_key_id
AWS_SECRET_ACCESS_KEY=tu_aws_secret_access_key
```

3. **Verificar permisos AWS**
   - Bedrock habilitado en tu cuenta
   - Permisos IAM para invocar modelos (p. ej. `bedrock:InvokeModel`)

---

## 🚀 Cómo Usar el Proyecto

### **1. Configurar credenciales**

```bash
cp env.example .env
nano .env   # o tu editor preferido
```

### **2. Ejecutar la aplicación**

```bash
# Opción A: run.py (recomendado)
python3 run.py

# Opción B: Streamlit directo
streamlit run src/app/app.py
```

### **3. Usar la interfaz**

1. Abre **http://localhost:8501** en el navegador.
2. Elige el tab:
   - **📚 Unidad Didáctica:** área, grado, competencia (opcional) → Generar → mejorar con el chat si quieres → descargar TXT/DOCX.
   - **📖 Sesión de Aprendizaje:** título de unidad (de una generada antes), título de sesión → Generar → mejorar con el chat → descargar.
3. Los archivos se pueden guardar en `~/Desktop/content_edu_outputs/` o en la ruta que configures al descargar.

---

## 📁 Ubicación de salidas

Los documentos generados se pueden exportar desde la propia interfaz. Si usas la ruta por defecto del proyecto, los archivos suelen guardarse en:

```
~/Desktop/content_edu_outputs/
```

Ejemplos de nombres:
- `unidad_didactica_ciencia_tecnologia.docx`
- `sesion_aprendizaje_3ro_secundaria.docx`

---

## ✅ Verificación rápida

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. Credenciales AWS
python3 -c "import os; print('AWS_REGION:', os.getenv('AWS_REGION', 'NO CONFIGURADO'))"

# 3. Ejecutar
python3 run.py
```

---

## 📝 Documentación adicional

- **`../README.md`** – Visión general del proyecto
- **`DETALLES_TECNICOS.md`** – Conexión AWS, esquema del proyecto, RAG, prompting, modelos
- **`DOCKER.md`** – Ejecución con Docker
- **`../data/README.md`** – Estructura de los JSON usados por el RAG (currículo y orientaciones CNEB)

---

**Última actualización:** 2026-02-05
