import { useState, useEffect, useMemo } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Save, FileText, Download, Sparkles, Wand2, ArrowLeft, Loader2, Table2, AlignLeft } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import { api } from '../lib/api'

// Campos de contenido real; todo lo demás (done, id, type, contenido_crudo, ...) es metadata del evento SSE
const CONTENT_FIELDS = [
  'situacion_significativa',
  'propositos_de_aprendizaje',
  'valores_y_enfoques_transversales',
  'secuencia_de_sesiones',
  'rubrica_unidad',
  'datos_informativos',
  'secuencia_didactica',
  'reflexion_sobre_la_actividad',
  'rubrica_sesion',
]

const SECTION_LABELS = {
  situacion_significativa: "I. SITUACIÓN SIGNIFICATIVA",
  propositos_de_aprendizaje: "II. PROPÓSITOS DE APRENDIZAJE",
  valores_y_enfoques_transversales: "III. ENFOQUES TRANSVERSALES / VALORES",
  secuencia_de_sesiones: "IV. SECUENCIA DE SESIONES",
  rubrica_unidad: "V. RÚBRICA ANALÍTICA DE UNIDAD",
  datos_informativos: "DATOS INFORMATIVOS",
  secuencia_didactica: "SECUENCIA DIDÁCTICA",
  reflexion_sobre_la_actividad: "REFLEXIÓN SOBRE LA ACTIVIDAD",
  rubrica_sesion: "RÚBRICA DE SESIÓN",
}

// Solo titulo + secciones de contenido conocidas — nunca metadata del evento SSE (done, id, type, ...)
const pickExportableFields = (doc) => {
  const out = { titulo: doc.titulo || 'Documento' }
  for (const key of CONTENT_FIELDS) {
    if (doc[key] !== undefined) out[key] = doc[key]
  }
  return out
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

  return rows.map(r => columnasUtiles.map(i => r[i] || ''))
}

function MarkdownTable({ rows }) {
  const [header, ...body] = rows
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-indigo-500/15">
            {header.map((cell, i) => (
              <th key={i} className="text-left font-bold text-indigo-300 p-3 border-b border-white/10 align-top whitespace-pre-wrap">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-white/[0.02]' : ''}>
              {row.map((cell, ci) => (
                <td key={ci} className="p-3 text-slate-300 align-top border-b border-white/5 whitespace-pre-wrap leading-relaxed">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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
    <div className="space-y-3 max-h-[28rem] overflow-y-auto pr-1">
      {sesiones.map((s, i) => (
        <div key={i} className="bg-white/[0.03] border border-white/10 rounded-xl p-4">
          <div className="font-bold text-indigo-300 text-sm mb-2">
            Sesión {s.numero}{s.titulo ? `: ${s.titulo}` : ''}
          </div>
          {s.criterio && (
            <div className="text-sm text-slate-400 mb-1.5 leading-relaxed">
              <span className="font-semibold text-slate-300">Criterio: </span>{s.criterio}
            </div>
          )}
          {s.actividades && (
            <div className="text-sm text-slate-400 leading-relaxed">
              <span className="font-semibold text-slate-300">Actividades: </span>{s.actividades}
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
  const [approved, setApproved] = useState(false)

  useEffect(() => {
    if (location.state?.content) {
      const normalized = normalizeDocument(location.state.content)
      console.log('[DEBUG] Raw content:', location.state.content)
      console.log('[DEBUG] Normalized document:', normalized)
      setDocument(normalized)
    } else {
      navigate('/')
    }
  }, [location, navigate])

  const handleFieldChange = (key, value) => {
    setDocument({ ...document, [key]: value })
  }

  const handleRefineField = async (key, instruction) => {
    if (!instruction) return
    setRefining(key)
    try {
      const res = await api.post('/generate/refine', {
        content: document[key],
        instruction: instruction
      })
      
      handleFieldChange(key, res.data.refined_content)
    } catch (err) {
      alert("Error al refinar: " + err.message)
    } finally {
      setRefining(null)
    }
  }

  const handleExport = async (format) => {
    try {
      const exportData = pickExportableFields(document)
      const res = await api.post(`/export/${format}`, exportData, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = window.document.createElement('a')
      link.href = url
      link.setAttribute('download', `${document.titulo || 'documento'}.${format}`)
      window.document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      alert("Error al exportar: " + err.message)
    }
  }

  if (!document) return null

  return (
    <div className="flex h-screen bg-dark">
      <Sidebar user={user} />
      
      <main className="flex-1 overflow-y-auto p-10 bg-slate-900/20">
        <div className="max-w-4xl mx-auto">
          <header className="flex justify-between items-center mb-10">
            <button onClick={() => navigate('/')} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors font-medium">
              <ArrowLeft size={18} /> Volver al Dashboard
            </button>
            <div className="flex gap-4">
              {!approved ? (
                <button 
                  onClick={() => setApproved(true)}
                  className="flex items-center gap-2 px-8 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-bold transition-all shadow-lg shadow-emerald-500/20">
                  <Save size={18} /> Aprobar Documento
                </button>
              ) : (
                <>
                  <button 
                    onClick={() => handleExport('docx')}
                    className="flex items-center gap-2 px-6 py-2 bg-slate-800 hover:bg-slate-700 rounded-xl font-bold transition-all border border-slate-700">
                    <Download size={18} /> DOCX
                  </button>
                  <button 
                    onClick={() => handleExport('pdf')}
                    className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold transition-all shadow-lg shadow-indigo-500/20">
                    <FileText size={18} /> PDF
                  </button>
                  <button 
                    onClick={() => setApproved(false)}
                    className="text-slate-500 hover:text-slate-300 text-sm font-medium">
                    Editar de nuevo
                  </button>
                </>
              )}
            </div>
          </header>

          <article className="glass rounded-[2rem] overflow-hidden shadow-2xl">
            <div className="bg-indigo-600/10 p-8 border-b border-white/5 flex justify-between items-center">
              <h1 className="text-2xl font-bold gradient-text">{document.titulo || 'Documento Generado'}</h1>
              <span className="bg-indigo-500/20 text-indigo-400 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">Editable</span>
            </div>

            <div className="p-8 space-y-12">
              {Object.entries(document).map(([key, value]) => {
                if (!CONTENT_FIELDS.includes(key)) return null

                return (
                  <EditableSection
                    key={key}
                    label={SECTION_LABELS[key] || key.replace(/_/g, ' ').toUpperCase()}
                    value={value}
                    isSecuenciaSesiones={key === 'secuencia_de_sesiones'}
                    isRefining={refining === key}
                    disabled={approved}
                    onChange={(val) => handleFieldChange(key, val)}
                    onRefine={(inst) => handleRefineField(key, inst)}
                  />
                )
              })}
            </div>
          </article>
        </div>
      </main>
    </div>
  )
}

function EditableSection({ label, value, onChange, onRefine, isRefining, disabled, isSecuenciaSesiones }) {
  const [instruction, setInstruction] = useState('')
  const [showRefine, setShowRefine] = useState(false)
  const [editarComoTexto, setEditarComoTexto] = useState(false)

  const tabla = useMemo(() => parseMarkdownTable(value), [value])
  const sesiones = useMemo(
    () => (isSecuenciaSesiones ? parseSecuenciaSesiones(value) : null),
    [value, isSecuenciaSesiones]
  )
  const vistaEstructurada = tabla || sesiones
  const mostrarEstructurado = vistaEstructurada && !editarComoTexto

  return (
    <div className="group relative">
      <div className="flex justify-between items-center mb-3">
        <label className="text-xs font-bold text-slate-500 tracking-[0.2em]">{label}</label>
        <div className="flex gap-2">
          {vistaEstructurada && (
            <button
              onClick={() => setEditarComoTexto(v => !v)}
              className="p-2 rounded-lg transition-all bg-slate-800 text-slate-400 hover:text-white"
              title={mostrarEstructurado ? "Editar como texto" : (tabla ? "Ver como tabla" : "Ver como tarjetas")}
            >
              {mostrarEstructurado ? <AlignLeft size={16} /> : <Table2 size={16} />}
            </button>
          )}
          {!disabled && (
            <button
              onClick={() => setShowRefine(!showRefine)}
              className={`p-2 rounded-lg transition-all ${showRefine ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
              title="Asistente IA"
            >
              <Sparkles size={16} />
            </button>
          )}
        </div>
      </div>

      {showRefine && !disabled && (
        <div className="mb-4 flex gap-2 animate-in fade-in slide-in-from-top-2">
          <input
            className="flex-1 bg-indigo-500/10 border border-indigo-500/30 rounded-xl px-4 py-2 text-sm focus:outline-none placeholder:text-slate-600"
            placeholder="Ej: 'Hazlo más corto', 'Usa un lenguaje más sencillo'..."
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
          />
          <button
            onClick={() => { onRefine(instruction); setShowRefine(false); setInstruction('') }}
            disabled={isRefining}
            className="bg-indigo-600 px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2"
          >
            {isRefining ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
            Refinar
          </button>
        </div>
      )}

      <div className="relative">
        {mostrarEstructurado ? (
          tabla ? <MarkdownTable rows={tabla} /> : <SecuenciaSesionesView sesiones={sesiones} />
        ) : (
          <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={`w-full bg-transparent border-none focus:ring-1 focus:ring-indigo-500/30 rounded-xl p-4 text-slate-300 resize-y leading-relaxed transition-all max-h-[28rem] overflow-y-auto ${!disabled ? 'hover:bg-white/5' : 'cursor-default opacity-80'}`}
            rows={estimarFilas(typeof value === 'string' ? value : '')}
          />
        )}
        {isRefining && (
          <div className="absolute inset-0 bg-dark/40 backdrop-blur-[1px] flex items-center justify-center rounded-xl">
             <Loader2 className="animate-spin text-indigo-500" />
          </div>
        )}
      </div>
    </div>
  )
}
