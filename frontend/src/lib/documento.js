import { api } from './api'
import { toast, confirmar, mensajeDeError } from './notify'

// Campos de contenido real; todo lo demás (done, id, type, contenido_crudo, ...) es metadata del evento SSE
export const CONTENT_FIELDS = [
  'situacion_significativa',
  'propositos_de_aprendizaje',
  'valores_y_enfoques_transversales',
  'secuencia_de_sesiones',
  'materiales_basicos',
  'rubrica_unidad',
  'datos_informativos',
  'reto',
  'secuencia_didactica',
  'reflexion_sobre_la_actividad',
  'rubrica_sesion',
]

export const SECTION_LABELS = {
  situacion_significativa: "I. SITUACIÓN SIGNIFICATIVA",
  propositos_de_aprendizaje: "II. PROPÓSITOS DE APRENDIZAJE",
  valores_y_enfoques_transversales: "III. ENFOQUES TRANSVERSALES / VALORES",
  secuencia_de_sesiones: "IV. SECUENCIA DE SESIONES",
  materiales_basicos: "MATERIALES BÁSICOS",
  rubrica_unidad: "V. RÚBRICA ANALÍTICA DE UNIDAD",
  datos_informativos: "DATOS INFORMATIVOS",
  reto: "RETO",
  secuencia_didactica: "SECUENCIA DIDÁCTICA",
  reflexion_sobre_la_actividad: "REFLEXIÓN SOBRE LA ACTIVIDAD",
  rubrica_sesion: "RÚBRICA DE SESIÓN",
}

// Solo titulo + secciones de contenido conocidas — nunca metadata del evento SSE (done, id, type, ...)
export const pickExportableFields = (doc) => {
  const out = { titulo: doc.titulo || 'Documento' }
  for (const key of CONTENT_FIELDS) {
    if (doc[key] !== undefined) out[key] = doc[key]
  }
  return out
}

// Exporta un documento a DOCX o PDF y lo descarga. Con errores críticos de estructura pide
// confirmación explícita (p. ej. para una revisión interna) en vez de bloquear sin salida.
// `contenido` es el documento tal como lo usa el Editor (titulo + secciones).
export async function exportarDocumento(contenido, formato, criticos = []) {
  if (criticos.length > 0) {
    const seguir = await confirmar({
      titulo: 'Errores críticos de estructura',
      mensaje: `Este documento tiene ${criticos.length} error(es) crítico(s) de estructura. ¿Exportar de todas formas?`,
      detalle: criticos.map(c => c.mensaje),
      confirmar: 'Exportar de todas formas',
    })
    if (!seguir) return false
  }
  try {
    const res = await api.post(`/export/${formato}`, pickExportableFields(contenido), { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = window.document.createElement('a')
    link.href = url
    link.setAttribute('download', `${contenido.titulo || 'documento'}.${formato}`)
    window.document.body.appendChild(link)
    link.click()
    link.remove()
    return true
  } catch (err) {
    toast.error('Error al exportar: ' + mensajeDeError(err))
    return false
  }
}
