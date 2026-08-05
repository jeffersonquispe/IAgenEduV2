import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Save, FileText, Download, Sparkles, Wand2, ArrowLeft, Loader2 } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import axios from 'axios'

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
      setDocument(normalizeDocument(location.state.content))
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
      const res = await axios.post('/api/generate/refine', {
        content: document[key],
        instruction: instruction
      }, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      
      handleFieldChange(key, res.data.refined_content)
    } catch (err) {
      alert("Error al refinar: " + err.message)
    } finally {
      setRefining(null)
    }
  }

  const handleExport = async (format) => {
    try {
      const res = await axios.post(`/api/export/${format}`, document, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
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
                if (key === 'id' || key === 'contenido_crudo' || key === 'titulo') return null
                
                const labels = {
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

                return (
                  <EditableSection 
                    key={key}
                    label={labels[key] || key.replace(/_/g, ' ').toUpperCase()}
                    value={value}
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

function EditableSection({ label, value, onChange, onRefine, isRefining, disabled }) {
  const [isEditing, setIsEditing] = useState(false)
  const [instruction, setInstruction] = useState('')
  const [showRefine, setShowRefine] = useState(false)

  return (
    <div className="group relative">
      <div className="flex justify-between items-center mb-3">
        <label className="text-xs font-bold text-slate-500 tracking-[0.2em]">{label}</label>
        <div className="flex gap-2">
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
        <textarea
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={`w-full bg-transparent border-none focus:ring-1 focus:ring-indigo-500/30 rounded-xl p-4 text-slate-300 resize-none min-h-[100px] leading-relaxed transition-all ${!disabled ? 'hover:bg-white/5' : 'cursor-default opacity-80'}`}
          rows={Math.max(3, (typeof value === 'string' ? value : '').split('\n').length)}
        />
        {isRefining && (
          <div className="absolute inset-0 bg-dark/40 backdrop-blur-[1px] flex items-center justify-center rounded-xl">
             <Loader2 className="animate-spin text-indigo-500" />
          </div>
        )}
      </div>
    </div>
  )
}
