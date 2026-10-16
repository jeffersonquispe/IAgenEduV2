import { useState, useEffect, useMemo, useRef, useId, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Save, FileText, Download, Sparkles, Wand2, ArrowLeft, Loader2, Pencil, Check, Undo2, ChevronDown, AlertTriangle } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { toast, confirmar, mensajeDeError } from '../lib/notify'

// Campos y etiquetas viven en lib/documento.js; se reexportan para Ejemplos.
import { CONTENT_FIELDS, SECTION_LABELS, pickExportableFields, exportarDocumento } from '../lib/documento'
export { CONTENT_FIELDS, SECTION_LABELS }

// Los errores de validación traen `seccion` como texto libre ("SECUENCIA DE SESIONES"); se enlaza con la
// sección del documento comparando nombres sin acentos ni numeración romana.
const normalizar = (t) => (t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase()
  .replace(/[^A-Z0-9 ]/g, ' ').replace(/\b(I|II|III|IV|V|VI)\b/g, ' ').replace(/\s+/g, ' ').trim()
const SINONIMOS_SECCION = {
  'MATRIZ AXIOLOGICA': 'valores_y_enfoques_transversales',
  'VALORES': 'valores_y_enfoques_transversales',
}
export function claveDeSeccion(seccion, clavesPresentes) {
  const n = normalizar(seccion)
  if (!n) return null
  const sinonimo = SINONIMOS_SECCION[n]
  if (sinonimo) return clavesPresentes.includes(sinonimo) ? sinonimo : null
  return clavesPresentes.find(k => {
    const l = normalizar(SECTION_LABELS[k])
    return l === n || l.includes(n) || n.includes(l)
  }) || null
}

const idSeccion = (clave) => `seccion-${clave}`
const irASeccion = (clave) => {
  const el = window.document.getElementById(idSeccion(clave))
  if (!el) return
  const reducir = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  el.scrollIntoView?.({ behavior: reducir ? 'auto' : 'smooth', block: 'start' })
  el.focus?.({ preventScroll: true })
}

// Resalta en el índice la sección que está en pantalla.
function useSeccionVisible(claves, raizRef) {
  const [visible, setVisible] = useState(claves[0] || null)
  const firma = claves.join('|')
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined' || !raizRef.current) return
    const obs = new IntersectionObserver((entradas) => {
      const e = entradas.find(x => x.isIntersecting)
      if (e) setVisible(e.target.dataset.clave)
    }, { root: raizRef.current, rootMargin: '-15% 0px -70% 0px' })
    claves.forEach(c => { const el = window.document.getElementById(idSeccion(c)); if (el) obs.observe(el) })
    return () => obs.disconnect()
  }, [firma])   // eslint-disable-line react-hooks/exhaustive-deps
  return visible
}

// Convierte una tabla Markdown (`| a | b |\n| -- | -- |\n| 1 | 2 |`) en filas de celdas.
// Devuelve null si el texto no parece ser mayormente una tabla (ej. párrafos normales).
const parseMarkdownTable = (text) => {
  if (!text) return null
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const tableLines = lines.filter(l => l.startsWith('|') && l.endsWith('|'))
  if (tableLines.length < 2 || tableLines.length / lines.length < 0.5) return null

  const isSeparatorRow = (l) => /^\|[\s:|-]+\|$/.test(l)
  const rows = tableLines
    .filter(l => !isSeparatorRow(l))
    .map(l => l.slice(1, -1).split('|').map(c => c.trim()))

  if (rows.length < 2) return null

  // Descarta columnas totalmente vacías (fila con celda extra al final, común en el formato del LLM)
  const maxCols = Math.max(...rows.map(r => r.length))
  const columnaVacia = Array.from({ length: maxCols }, (_, i) => rows.every(r => !r[i]))
  const columnasUtiles = columnaVacia.map((vacia, i) => !vacia ? i : -1).filter(i => i !== -1)
  if (columnasUtiles.length < 2) return null
  // Si el cuerpo solo tiene datos en una columna (p. ej. `ITEM | CONTENIDO` con todo en la primera
  // celda, resultado típico de refinar con IA) no es una tabla real: se muestra como texto.
  if (columnasUtiles.filter(i => rows.slice(1).some(r => r[i])).length < 2) return null

  return rows.map(r => columnasUtiles.map(i => r[i] || ''))
}

// Muestra **negrita** de Markdown como negrita; el resto del texto no se toca.
function Inline({ texto }) {
  return String(texto ?? '').split(/\*\*(.+?)\*\*/g).map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : p))
}

function MarkdownTable({ rows }) {
  const [header, ...body] = rows
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-accent/15">
            {header.map((cell, i) => (
              <th key={i} className="text-left font-bold text-accent-text p-3 border-b border-line align-top whitespace-pre-wrap">
                <Inline texto={cell} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-fg/[0.03]' : ''}>
              {row.map((cell, ci) => (
                <td key={ci} className="p-3 text-fg align-top border-b border-line whitespace-pre-wrap leading-relaxed">
                  <Inline texto={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Texto de la única columna con datos de una "tabla" degenerada (ver parseMarkdownTable); null si no aplica.
// Misma regla que aplanar_tabla_degenerada en core/markdown_table.py.
const aplanarTablaDegenerada = (text) => {
  if (!text) return null
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const tableLines = lines.filter(l => l.startsWith('|') && l.endsWith('|'))
  if (tableLines.length < 2 || tableLines.length / lines.length < 0.5) return null
  const rows = tableLines.filter(l => !/^\|[\s:|-]+\|$/.test(l)).map(l => l.slice(1, -1).split('|').map(c => c.trim()))
  const body = rows.slice(1)
  if (body.length === 0) return null
  const maxCols = Math.max(...body.map(r => r.length))
  const withData = Array.from({ length: maxCols }, (_, i) => i).filter(i => body.some(r => r[i]))
  if (withData.length !== 1) return null
  return body.map(r => r[withData[0]]).filter(Boolean).join('\n\n')
}

// Convierte el bloque de texto de "Secuencia de Sesiones"
// ("Sesión 1: Título...\nCriterio: ...\nActividades: ...\n\nSesión 2: ...")
// en tarjetas independientes, para que no sea una sola caja gigante que
// empuja el resto de secciones hacia abajo.
const parseSecuenciaSesiones = (text) => {
  if (!text) return null
  const bloques = text.split(/\n\s*\n/).map(b => b.trim()).filter(Boolean)
  if (bloques.length < 2) return null

  const sesiones = bloques.map((bloque, i) => {
    const lineas = bloque.split('\n')
    const primera = lineas[0] || ''
    const m = primera.match(/^Sesi[oó]n\s*(\d+)\s*:\s*(.*)$/i)
    const resto = lineas.slice(1).join('\n')
    const critMatch = resto.match(/Criterio:\s*([\s\S]*?)(?:\nActividades:|$)/i)
    const actMatch = resto.match(/Actividades:\s*([\s\S]*)$/i)
    return {
      numero: m ? m[1] : String(i + 1),
      titulo: m ? m[2] : primera,
      criterio: critMatch ? critMatch[1].trim() : '',
      actividades: actMatch ? actMatch[1].trim() : (!m ? resto.trim() : ''),
    }
  })

  if (sesiones.every(s => !s.titulo && !s.criterio && !s.actividades)) return null
  return sesiones
}

function SecuenciaSesionesView({ sesiones }) {
  return (
    <div className="space-y-3">
      {sesiones.map((s, i) => (
        <div key={i} className="bg-fg/[0.03] border border-line rounded-xl p-4">
          <div className="font-bold text-accent-text text-sm mb-2">
            Sesión {s.numero}{s.titulo ? `: ${s.titulo}` : ''}
          </div>
          {s.criterio && (
            <div className="text-sm text-fg-muted mb-1.5 leading-relaxed">
              <span className="font-semibold text-fg">Criterio: </span>{s.criterio}
            </div>
          )}
          {s.actividades && (
            <div className="text-sm text-fg-muted leading-relaxed">
              <span className="font-semibold text-fg">Actividades: </span>{s.actividades}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// Estima cuántas filas necesita un textarea a partir de cantidad de palabras
// (no solo saltos de línea — un párrafo largo sin \n igual necesita espacio),
// acotado a un máximo para que ningún campo domine la página; el resto se ve
// con scroll interno en vez de estirar todo el layout.
const CHARS_PER_ROW = 90
const MIN_ROWS = 3
const MAX_ROWS = 16

const estimarFilas = (text) => {
  if (!text) return MIN_ROWS
  const porSaltosDeLinea = text.split('\n').length
  const porLongitud = Math.ceil(text.length / CHARS_PER_ROW)
  return Math.min(Math.max(porSaltosDeLinea, porLongitud, MIN_ROWS), MAX_ROWS)
}

// Normaliza todos los campos para que sean strings
const normalizeDocument = (doc) => {
  if (!doc) return null
  const normalized = {}
  for (const [key, value] of Object.entries(doc)) {
    if (typeof value === 'string') {
      normalized[key] = value
    } else if (value === null || value === undefined) {
      normalized[key] = ''
    } else if (typeof value === 'object') {
      normalized[key] = JSON.stringify(value, null, 2)
    } else {
      normalized[key] = String(value)
    }
  }
  return normalized
}

export default function Editor({ user }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [document, setDocument] = useState(null)
  const [editingField, setEditingField] = useState(null)
  const [refining, setRefining] = useState(false)
  const mainRef = useRef(null)

  useEffect(() => {
    if (location.state?.content) {
      const normalized = normalizeDocument(location.state.content)
      setDocument(normalized)
    } else {
      navigate('/')
    }
  }, [location, navigate])

  const handleFieldChange = (key, value) => {
    setDocument({ ...document, [key]: value })
  }

  // Devuelve la propuesta de la IA; es la sección quien decide aceptarla (con vista previa) o descartarla.
  const handleRefineField = async (key, instruction) => {
    if (!instruction) return null
    setRefining(key)
    try {
      const res = await api.post('/generate/refine', {
        content: document[key],
        instruction: instruction
      })
      return res.data.refined_content
    } catch (err) {
      toast.error("Error al refinar: " + mensajeDeError(err))
      return null
    } finally {
      setRefining(null)
    }
  }

  // HU-30: resultado de validación guardado con el documento. normalizeDocument()
  // convierte los objetos en texto JSON, así que se vuelve a interpretar aquí.
  const validacion = useMemo(() => {
    const raw = document?.validacion
    if (!raw) return null
    try { return typeof raw === 'string' ? JSON.parse(raw) : raw } catch { return null }
  }, [document?.validacion])
  const criticos = (validacion?.detalle || []).filter(d => d.tipo === 'CRITICO')
  const advertencias = (validacion?.detalle || []).filter(d => d.tipo === 'ADVERTENCIA')

  // HU-30: al editar o refinar, el aviso se actualiza. Se recalcula en el servidor (sin IA) sobre
  // las secciones actuales; lo que no se puede reevaluar desde ahí se conserva. Espera a que el
  // docente deje de escribir y descarta respuestas que lleguen fuera de orden.
  const firmaContenido = useMemo(
    () => (document ? JSON.stringify(CONTENT_FIELDS.map(k => document[k] ?? '')) : ''),
    [document]
  )
  const ultimaFirmaValidada = useRef(null)
  const peticionValidacion = useRef(0)
  const validacionRef = useRef(null)
  validacionRef.current = validacion
  const documentoRef = useRef(null)
  documentoRef.current = document

  useEffect(() => {
    if (!documentoRef.current) return
    if (ultimaFirmaValidada.current === null) {      // primera carga: ya viene validado
      ultimaFirmaValidada.current = firmaContenido
      return
    }
    if (!validacionRef.current || firmaContenido === ultimaFirmaValidada.current) return

    const temporizador = setTimeout(async () => {
      const id = ++peticionValidacion.current
      const actual = documentoRef.current
      const esUnidad = actual.situacion_significativa !== undefined || actual.secuencia_de_sesiones !== undefined
      try {
        const res = await api.post('/generate/validar', {
          tipo: esUnidad ? 'unidad' : 'sesion',
          content: pickExportableFields(actual),
          detalle_previo: validacionRef.current?.detalle || [],
        })
        if (id !== peticionValidacion.current) return
        ultimaFirmaValidada.current = firmaContenido
        setDocument(d => (d ? { ...d, validacion: res.data } : d))
      } catch (err) {
        console.error('[revalidar] No se pudo actualizar la validación:', err)   // se conserva el estado anterior
      }
    }, 1200)
    return () => clearTimeout(temporizador)
  }, [firmaContenido])

  // --- Guardado de lo editado (versiones) ---------------------------------------------------
  // Hasta aquí lo editado vivía solo en esta pantalla. Con `id` el documento se guarda en el
  // servidor (PUT /data/documents/{id}), que registra una versión nueva y detecta si se guardó
  // desde otra pestaña (409). El guardado es manual: así el historial no se llena de versiones.
  const docId = document?.id || null
  const versionActual = Number.parseInt(document?.version, 10) || null
  const [firmaGuardada, setFirmaGuardada] = useState(null)   // contenido tal como está en el servidor
  const [guardando, setGuardando] = useState(false)
  const [guardadoEn, setGuardadoEn] = useState(null)
  const [errorGuardado, setErrorGuardado] = useState('')

  useEffect(() => {
    if (document && firmaGuardada === null) setFirmaGuardada(firmaContenido)   // lo recién cargado ya está guardado
  }, [document, firmaContenido, firmaGuardada])

  const hayCambios = Boolean(docId) && firmaGuardada !== null && firmaContenido !== firmaGuardada

  const guardar = async () => {
    if (!docId || guardando || !hayCambios) return
    const firmaEnviada = firmaContenido
    setGuardando(true)
    setErrorGuardado('')
    try {
      const res = await api.put(`/data/documents/${docId}`, {
        content: pickExportableFields(document),
        base_version: versionActual,
      })
      setFirmaGuardada(firmaEnviada)   // si siguió escribiendo mientras guardaba, sigue habiendo cambios
      setGuardadoEn(new Date())
      setDocument(d => (d ? {
        ...d,
        version: String(res.data.version),
        ...(res.data.validacion ? { validacion: res.data.validacion } : {}),
      } : d))
    } catch (err) {
      const detalle = err.response?.data?.detail
      setErrorGuardado(
        err.response?.status === 409
          ? (detalle?.message || 'Este documento cambió en otra pestaña. Recárgalo para ver la última versión.')
          : `No se pudo guardar: ${typeof detalle === 'string' ? detalle : err.message}`
      )
    } finally {
      setGuardando(false)
    }
  }

  const guardarRef = useRef(guardar)
  guardarRef.current = guardar

  useEffect(() => {      // Ctrl+S / Cmd+S
    const alPulsar = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        guardarRef.current()
      }
    }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [])

  useEffect(() => {      // el navegador avisa antes de cerrar o recargar con cambios sin guardar
    if (!hayCambios) return
    const avisar = (e) => { e.preventDefault(); e.returnValue = '' }
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [hayCambios])

  const confirmarSalida = useCallback(async () => {
    if (!hayCambios) return true
    return confirmar({
      titulo: 'Cambios sin guardar',
      mensaje: 'Tienes cambios sin guardar. ¿Salir sin guardarlos?',
      confirmar: 'Salir sin guardar',
      peligro: true,
    })
  }, [hayCambios])

  const volverAlDashboard = async () => {
    if (await confirmarSalida()) navigate('/')
  }

  const handleExport = (format) => exportarDocumento(document, format, criticos)

  const clavesPresentes = Object.keys(document || {}).filter(k => CONTENT_FIELDS.includes(k))
  const problemas = [...criticos, ...advertencias].map(d => ({ ...d, clave: claveDeSeccion(d.seccion, clavesPresentes) }))
  const nivelPorSeccion = {}
  for (const d of problemas) {
    if (!d.clave) continue
    if (d.tipo === 'CRITICO') nivelPorSeccion[d.clave] = 'CRITICO'
    else if (!nivelPorSeccion[d.clave]) nivelPorSeccion[d.clave] = 'ADVERTENCIA'
  }
  const seccionVisible = useSeccionVisible(clavesPresentes, mainRef)

  if (!document) return null

  const esUnidad = document.situacion_significativa !== undefined || document.secuencia_de_sesiones !== undefined

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-bg">
      <Sidebar user={user} onBeforeNavigate={confirmarSalida} />

      <main ref={mainRef} className="flex-1 min-h-0 overflow-y-auto">
        {/* Barra de acciones fija: siempre a mano en un documento largo */}
        <div className="sticky top-0 z-20 bg-bg/95 backdrop-blur border-b border-line px-4 sm:px-6 lg:px-10 py-3 flex items-center justify-between gap-2 sm:gap-3">
          <button onClick={volverAlDashboard} aria-label="Volver al Dashboard" className="flex items-center gap-2 text-fg-muted hover:text-fg transition-colors font-medium">
            <ArrowLeft size={18} aria-hidden="true" />
            <span className="hidden sm:inline">Volver al Dashboard</span>
            <span className="sm:hidden">Volver</span>
          </button>
          <div className="flex items-center gap-2 sm:gap-3">
            {docId && (
              <>
                <span role="status" className={`text-xs font-medium ${hayCambios || guardando ? '' : 'hidden sm:inline'} ${hayCambios ? 'text-warning-text' : 'text-success-text'}`}>
                  {guardando ? 'Guardando…'
                    : hayCambios ? 'Cambios sin guardar'
                    : guardadoEn ? `Guardado ${guardadoEn.toLocaleTimeString()}` : 'Sin cambios'}
                </span>
                <Button variant="secondary" onClick={guardar} disabled={!hayCambios || guardando} title="Guardar cambios (Ctrl+S)">
                  {guardando ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />} <span className="sr-only sm:not-sr-only">Guardar cambios</span>
                </Button>
              </>
            )}
            <MenuExportar onExport={handleExport} />
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-6 lg:px-10 py-8 flex gap-10 items-start">
          {/* Índice de secciones */}
          <nav aria-label="Secciones del documento" className="hidden xl:block w-56 shrink-0 sticky top-24 self-start">
            <p className="text-xs font-bold text-fg-subtle uppercase tracking-wider mb-3">Contenido</p>
            <ol className="space-y-1">
              {clavesPresentes.map(clave => {
                const nivel = nivelPorSeccion[clave]
                const activa = seccionVisible === clave
                return (
                  <li key={clave}>
                    <button type="button" onClick={() => irASeccion(clave)} aria-current={activa ? 'location' : undefined}
                      className={`w-full text-left flex items-start gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${
                        activa ? 'bg-accent/10 text-accent-text' : 'text-fg-muted hover:bg-surface-2 hover:text-fg'}`}>
                      <span className="flex-1">{SECTION_LABELS[clave]}</span>
                      {nivel && (
                        <>
                          <span aria-hidden="true" className={`mt-1 w-2 h-2 rounded-full shrink-0 ${nivel === 'CRITICO' ? 'bg-danger' : 'bg-warning'}`} />
                          <span className="sr-only">{nivel === 'CRITICO' ? 'con errores críticos' : 'con advertencias'}</span>
                        </>
                      )}
                    </button>
                  </li>
                )
              })}
            </ol>
          </nav>

          <div className="flex-1 min-w-0 max-w-4xl">
            {errorGuardado && (
              <p role="alert" className="mb-6 rounded-2xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger-text">
                {errorGuardado}
              </p>
            )}

            {validacion && (criticos.length > 0 || advertencias.length > 0) && (
              <div role="alert"
                className={`mb-6 rounded-2xl border p-5 text-sm ${
                  criticos.length > 0
                    ? 'bg-danger/10 border-danger/30 text-danger-text'
                    : 'bg-warning/10 border-warning/30 text-warning-text'
                }`}>
                <p className="font-bold mb-2 flex items-center gap-2">
                  <AlertTriangle size={16} aria-hidden="true" />
                  <span>
                    {criticos.length > 0
                      ? `El documento tiene ${criticos.length} error(es) crítico(s) de estructura`
                      : 'El documento tiene advertencias de calidad'}
                    {' '}(puntaje de validación: {validacion.puntaje_validacion}/100)
                  </span>
                </p>
                <ul className="list-disc pl-5 space-y-1">
                  {problemas.map((d, i) => (
                    <li key={i}>
                      {d.mensaje}
                      {d.clave && (
                        <button type="button" onClick={() => irASeccion(d.clave)} className="ml-2 font-bold underline">
                          Ir a la sección
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs opacity-80">
                  {criticos.length > 0 && 'Al exportar se te pedirá confirmación. '}
                  {validacion.revalidado
                    ? 'Actualizado con tus cambios. Los controles de estructura de la generación inicial se conservan.'
                    : 'Se actualiza cuando editas o refinas una sección.'}
                </p>
              </div>
            )}

            <article className="glass rounded-[2rem] overflow-hidden shadow-sm">
              <header className="p-8 border-b border-line">
                <p className="text-xs font-bold uppercase tracking-wider text-accent-text mb-2">
                  {esUnidad ? 'Unidad didáctica' : 'Sesión de aprendizaje'}
                  {versionActual ? ` · versión ${versionActual}` : ''}
                </p>
                <h1 className="text-2xl sm:text-3xl font-bold leading-tight">{document.titulo || 'Documento Generado'}</h1>
              </header>

              <div className="p-8 space-y-12">
                {clavesPresentes.map(key => (
                  <EditableSection
                    key={key}
                    id={idSeccion(key)}
                    clave={key}
                    label={SECTION_LABELS[key] || key.replace(/_/g, ' ').toUpperCase()}
                    value={document[key]}
                    issues={problemas.filter(d => d.clave === key)}
                    isSecuenciaSesiones={key === 'secuencia_de_sesiones'}
                    isRefining={refining === key}
                    disabled={false}
                    onChange={(val) => handleFieldChange(key, val)}
                    onRefine={(inst) => handleRefineField(key, inst)}
                  />
                ))}
              </div>
            </article>
          </div>
        </div>
      </main>
    </div>
  )
}

// Menú "Exportar": un solo punto de entrada para DOCX y PDF.
function MenuExportar({ onExport }) {
  const [abierto, setAbierto] = useState(false)
  const caja = useRef(null)

  useEffect(() => {
    if (!abierto) return
    const fuera = (e) => { if (caja.current && !caja.current.contains(e.target)) setAbierto(false) }
    const tecla = (e) => { if (e.key === 'Escape') setAbierto(false) }
    window.document.addEventListener('mousedown', fuera)
    window.document.addEventListener('keydown', tecla)
    return () => { window.document.removeEventListener('mousedown', fuera); window.document.removeEventListener('keydown', tecla) }
  }, [abierto])

  const elegir = (formato) => { setAbierto(false); onExport(formato) }

  return (
    <div ref={caja} className="relative">
      <Button onClick={() => setAbierto(a => !a)} aria-haspopup="menu" aria-expanded={abierto}>
        <Download size={18} aria-hidden="true" /> Exportar <ChevronDown size={16} aria-hidden="true" className="hidden sm:block" />
      </Button>
      {abierto && (
        <div role="menu" className="absolute right-0 mt-2 w-48 rounded-xl border border-line bg-surface shadow-lg p-1 z-30">
          <button role="menuitem" onClick={() => elegir('docx')} className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-surface-2">
            <FileText size={16} aria-hidden="true" /> Word (.docx)
          </button>
          <button role="menuitem" onClick={() => elegir('pdf')} className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-surface-2">
            <FileText size={16} aria-hidden="true" /> PDF
          </button>
        </div>
      )}
    </div>
  )
}

// Renderiza el contenido de una sección en modo lectura: tabla, tarjetas de sesiones o texto.
function Contenido({ value, isSecuenciaSesiones }) {
  const texto = typeof value === 'string' ? value : ''
  const tabla = useMemo(() => parseMarkdownTable(texto), [texto])
  const sesiones = useMemo(() => (isSecuenciaSesiones ? parseSecuenciaSesiones(texto) : null), [texto, isSecuenciaSesiones])
  if (!texto.trim()) return <p className="text-sm text-fg-subtle italic">Sin contenido todavía.</p>
  if (tabla) return <MarkdownTable rows={tabla} />
  if (sesiones) return <SecuenciaSesionesView sesiones={sesiones} />
  const plano = aplanarTablaDegenerada(texto)
  return <div className="whitespace-pre-wrap leading-7 text-fg max-w-[75ch]"><Inline texto={plano ?? texto} /></div>
}

const AJUSTES_RAPIDOS = ['Más breve', 'Lenguaje más sencillo', 'Más detalle', 'Agregar un ejemplo']

// Exportada para que la biblioteca de ejemplos (HU-44) muestre las secciones con el mismo
// visor en modo solo lectura (disabled).
export function EditableSection({ id, clave, label, value, onChange, onRefine, isRefining, disabled, isSecuenciaSesiones, issues = [] }) {
  const [editando, setEditando] = useState(false)
  const [showRefine, setShowRefine] = useState(false)
  const [instruction, setInstruction] = useState('')
  const [propuesta, setPropuesta] = useState(null)   // texto propuesto por la IA, a la espera de aceptar o descartar
  const [previo, setPrevio] = useState(null)         // valor anterior a aceptar una propuesta (para deshacer)
  const idTitulo = useId()
  const texto = typeof value === 'string' ? value : ''

  const solicitar = async (inst) => {
    const t = (inst || '').trim()
    if (!t || isRefining) return
    const r = await onRefine(t)
    if (typeof r === 'string' && r.trim()) { setPropuesta(r); setShowRefine(false); setInstruction('') }
  }
  const aceptar = () => { setPrevio(texto); onChange(propuesta); setPropuesta(null) }
  const deshacer = () => { onChange(previo); setPrevio(null) }
  const alEscribir = (v) => { setPrevio(null); onChange(v) }

  return (
    <section id={id} data-clave={clave} tabIndex={-1} aria-labelledby={idTitulo} className="group relative scroll-mt-24 focus:outline-none">
      <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
        <h2 id={idTitulo} className="text-sm font-bold text-fg-muted tracking-wider uppercase">{label}</h2>
        {!disabled && (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditando(v => !v)} aria-pressed={editando}>
              {editando ? <><Check size={16} aria-hidden="true" /> Listo</> : <><Pencil size={16} aria-hidden="true" /> Editar</>}
            </Button>
            <Button variant={showRefine ? 'primary' : 'secondary'} size="sm" onClick={() => setShowRefine(v => !v)}
              title="Asistente IA" aria-expanded={showRefine} aria-label={`Mejorar con IA: ${label}`}>
              <Sparkles size={16} aria-hidden="true" /> Mejorar con IA
            </Button>
          </div>
        )}
      </div>

      {issues.length > 0 && (
        <ul className={`mb-3 rounded-xl border px-3 py-2 text-xs space-y-1 ${
          issues.some(i => i.tipo === 'CRITICO') ? 'border-danger/30 bg-danger/10 text-danger-text' : 'border-warning/30 bg-warning/10 text-warning-text'}`}>
          {issues.map((d, i) => <li key={i}>{d.mensaje}</li>)}
        </ul>
      )}

      {showRefine && !disabled && (
        <div className="mb-4 space-y-2">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Ajustes rápidos">
            {AJUSTES_RAPIDOS.map(a => (
              <button key={a} type="button" onClick={() => solicitar(a)} disabled={isRefining}
                className="px-3 py-1 rounded-full border border-line text-xs font-semibold hover:border-accent hover:text-accent-text disabled:opacity-50 transition-colors">
                {a}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              aria-label={`Instrucción para ${label}`}
              className="flex-1 bg-accent/10 border border-accent/30 rounded-xl px-4 py-2 text-sm focus:outline-none placeholder:text-fg-subtle"
              placeholder="O escribe tu instrucción: 'Hazlo más corto', 'Usa un lenguaje más sencillo'..."
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') solicitar(instruction) }}
            />
            <Button size="sm" onClick={() => solicitar(instruction)} disabled={isRefining || !instruction.trim()}>
              {isRefining ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} aria-hidden="true" />}
              Proponer
            </Button>
          </div>
        </div>
      )}

      {propuesta !== null && (
        <div className="mb-4 rounded-2xl border border-accent/40 bg-accent/5 p-4 space-y-3">
          <p className="text-sm font-bold text-accent-text">Propuesta de la IA — revísala antes de aplicarla</p>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-bold text-fg-subtle uppercase mb-2">Actual</p>
              <div className="max-h-72 overflow-y-auto text-sm"><Contenido value={texto} isSecuenciaSesiones={isSecuenciaSesiones} /></div>
            </div>
            <div>
              <p className="text-xs font-bold text-fg-subtle uppercase mb-2">Propuesta</p>
              <div className="max-h-72 overflow-y-auto text-sm"><Contenido value={propuesta} isSecuenciaSesiones={isSecuenciaSesiones} /></div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setPropuesta(null)}>Descartar</Button>
            <Button size="sm" onClick={aceptar}><Check size={16} aria-hidden="true" /> Aceptar cambio</Button>
          </div>
        </div>
      )}

      {previo !== null && (
        <div role="status" className="mb-3 flex items-center gap-3 text-xs text-success-text">
          <span>Cambio aplicado.</span>
          <button type="button" onClick={deshacer} className="inline-flex items-center gap-1 font-bold underline">
            <Undo2 size={14} aria-hidden="true" /> Deshacer
          </button>
        </div>
      )}

      <div className="relative">
        {editando && !disabled ? (
          <textarea
            autoFocus
            aria-label={label}
            value={texto}
            onChange={(e) => alEscribir(e.target.value)}
            rows={estimarFilas(texto)}
            className="w-full bg-surface border border-line focus:border-accent rounded-xl p-4 text-fg resize-y leading-7 max-h-[28rem] overflow-y-auto focus:outline-none"
          />
        ) : (
          <Contenido value={texto} isSecuenciaSesiones={isSecuenciaSesiones} />
        )}
        {isRefining && (
          <div className="absolute inset-0 bg-bg/60 flex items-center justify-center rounded-xl" role="status" aria-label="Refinando sección">
            <Loader2 className="animate-spin text-accent-text" />
          </div>
        )}
      </div>
    </section>
  )
}
