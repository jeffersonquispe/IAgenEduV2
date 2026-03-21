import { useState, useEffect, useCallback } from 'react'
import { Wand2, Loader2, CheckCircle2, ChevronLeft, ChevronRight, X, Zap } from 'lucide-react'
import axios from 'axios'

const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}` })

export default function GenerationWizard({ isOpen, onClose, type, onComplete }) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [streamText, setStreamText] = useState('')  // SSE preview text
  const [isStreaming, setIsStreaming] = useState(false)

  const [dataOptions, setDataOptions] = useState({
    areas: [], grados: [], temas_por_area: {}
  })
  // Competencias filtered by selected area
  const [competenciasPorArea, setCompetenciasPorArea] = useState([])
  // Temas filtered by area + grado
  const [temasDisponibles, setTemasDisponibles] = useState([])

  const [formData, setFormData] = useState({
    area: '',
    grado: '',
    competencias: [],
    temas: '',
    num_sesiones: 6,
    producto_final: '',
    titulo_unidad: '',
    tema: '',
    metodologia: 'ERCA',
  })

  // Base options
  useEffect(() => {
    if (!isOpen) return
    axios.get('/api/data/options').then(res => {
      setDataOptions({ areas: res.data.areas, grados: res.data.grados, temas_por_area: res.data.temas_por_area || {} })
    }).catch(console.error)
  }, [isOpen])

  // When area changes → fetch competencias for that area
  useEffect(() => {
    if (!formData.area) { setCompetenciasPorArea([]); return }
    axios.get(`/api/data/competencias?area=${encodeURIComponent(formData.area)}`)
      .then(res => setCompetenciasPorArea(res.data || []))
      .catch(() => setCompetenciasPorArea([]))
    setFormData(f => ({ ...f, competencias: [], tema: '' }))
    setTemasDisponibles([])
  }, [formData.area])

  // When area + grado change → fetch temas
  useEffect(() => {
    if (!formData.area || !formData.grado) { setTemasDisponibles([]); return }
    axios.get(`/api/data/temas?area=${encodeURIComponent(formData.area)}&grado=${encodeURIComponent(formData.grado)}`)
      .then(res => setTemasDisponibles(res.data.temas || []))
      .catch(() => setTemasDisponibles([]))
  }, [formData.area, formData.grado])

  if (!isOpen) return null

  const steps = type === 'unidad'
    ? [
        { id: 1, title: 'Área y Grado', fields: ['area', 'grado'] },
        { id: 2, title: 'Competencias y Contexto', fields: ['competencias'] },
        { id: 3, title: 'Confirmar y Generar', fields: [] },
      ]
    : [
        { id: 1, title: 'Área y Grado', fields: ['area', 'grado'] },
        { id: 2, title: 'Temática y Metodología', fields: ['tema', 'metodologia'] },
        { id: 3, title: 'Confirmar y Generar', fields: [] },
      ]
  const totalSteps = steps.length

  const handleChange = e => setFormData({ ...formData, [e.target.name]: e.target.value })

  const handleMultiSelect = e => {
    const values = [...e.target.options].filter(o => o.selected).map(o => o.value)
    setFormData({ ...formData, [e.target.name]: values })
  }

  const handleNext = () => setStep(s => Math.min(s + 1, totalSteps))
  const handleBack = () => setStep(s => Math.max(s - 1, 1))

  // Standard generation
  const handleGenerate = async () => {
    setLoading(true)
    try {
      const endpoint = type === 'unidad' ? '/api/generate/unidad' : '/api/generate/sesion'
      const competenciasTexto = competenciasPorArea
        .filter(c => formData.competencias.includes(String(c.numero)))
        .map(c => `COMPETENCIA ${c.numero}. ${c.nombre}`)

      const payload = type === 'unidad'
        ? {
            area: formData.area, grado: formData.grado,
            competencias: competenciasTexto,
            temas: formData.temas, num_sesiones: formData.num_sesiones,
            producto_final: formData.producto_final,
          }
        : {
            area: formData.area, grado: formData.grado,
            titulo_unidad: formData.titulo_unidad,
            tema: formData.tema, metodologia: formData.metodologia,
          }

      const res = await axios.post(endpoint, payload, { headers: authHeader() })
      onComplete(res.data)
      onClose()
    } catch (err) {
      if (err.response?.status === 401) alert("Tu sesión ha expirado. Por favor, inicia sesión de nuevo.")
      else alert("Error en la generación: " + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  // Streaming generation (only for unidad)
  const handleGenerateStream = async () => {
    setIsStreaming(true)
    setStreamText('')
    const competenciasTexto = competenciasPorArea
      .filter(c => formData.competencias.includes(String(c.numero)))
      .map(c => `COMPETENCIA ${c.numero}. ${c.nombre}`)

    const payload = {
      area: formData.area, grado: formData.grado,
      competencias: competenciasTexto,
      temas: formData.temas, num_sesiones: formData.num_sesiones,
      producto_final: formData.producto_final,
    }

    try {
      const response = await fetch('/api/generate/unidad/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify(payload),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let docId = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const text = decoder.decode(value)
        // Parse SSE lines
        for (const line of text.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.chunk) {
                fullText += data.chunk
                setStreamText(fullText)
              }
              if (data.done && data.id) {
                docId = data.id
              }
            } catch {}
          }
        }
      }

      if (docId) {
        onComplete({ id: docId, contenido_crudo: fullText, titulo: `Unidad Didáctica - ${formData.area}` })
        onClose()
      }
    } catch (err) {
      alert('Error en streaming: ' + err.message)
    } finally {
      setIsStreaming(false)
    }
  }

  const isStep1Valid = formData.area && formData.grado

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl relative overflow-hidden">
        {/* Progress bar */}
        <div className="absolute top-0 left-0 h-1 bg-indigo-500 transition-all duration-500" style={{ width: `${(step / totalSteps) * 100}%` }} />

        <div className="p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-2xl font-bold">Generador de {type === 'unidad' ? 'Unidad Didáctica' : 'Sesión de Aprendizaje'}</h2>
              <p className="text-slate-400 text-sm">Paso {step} de {totalSteps}: {steps[step - 1].title}</p>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors"><X size={20} /></button>
          </div>

          <div className="min-h-[280px] mb-8">
            {(loading || isStreaming) ? (
              <div className="flex flex-col items-center justify-center h-full pt-6 gap-4">
                <Loader2 className="w-12 h-12 text-indigo-500 animate-spin" />
                <p className="text-lg font-medium animate-pulse">Generando con IA...</p>
                {isStreaming && streamText && (
                  <div className="w-full bg-slate-800 rounded-xl p-4 max-h-48 overflow-y-auto text-xs text-slate-300 font-mono whitespace-pre-wrap">
                    {streamText}
                  </div>
                )}
                {!isStreaming && <p className="text-slate-500 text-sm">Esto puede tomar hasta 30 segundos</p>}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Step 1: Area + Grado */}
                {step === 1 && (
                  <div className="grid grid-cols-2 gap-6">
                    <SelectField label="Área Curricular" name="area" value={formData.area}
                      onChange={handleChange} options={dataOptions.areas} />
                    <SelectField label="Grado" name="grado" value={formData.grado}
                      onChange={handleChange} options={dataOptions.grados} />
                    {formData.area && (
                      <div className="col-span-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl px-4 py-3 text-sm text-indigo-300">
                        Las competencias disponibles se cargarán automáticamente para <strong>{formData.area}</strong>.
                      </div>
                    )}
                  </div>
                )}

                {/* Step 2: Competencias (Unidad) or Tema+Metodología (Sesión) */}
                {step === 2 && type === 'unidad' && (
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label className="text-sm font-bold text-slate-400">
                        Competencias de <span className="text-indigo-400">{formData.area}</span>
                        {' '}— Mantén Ctrl/Cmd para elegir varias
                      </label>
                      {competenciasPorArea.length === 0 ? (
                        <div className="text-slate-500 text-sm bg-slate-800 p-4 rounded-xl">
                          No se encontraron competencias para esta área. Selecciona otra área en el paso anterior.
                        </div>
                      ) : (
                        <select
                          multiple
                          name="competencias"
                          value={formData.competencias}
                          onChange={handleMultiSelect}
                          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors h-40"
                        >
                          {competenciasPorArea.map(c => (
                            <option key={c.numero} value={String(c.numero)}>
                              {c.numero}. {c.nombre}
                            </option>
                          ))}
                        </select>
                      )}
                      <p className="text-xs text-slate-500">{formData.competencias.length} competencia(s) seleccionada(s)</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {temasDisponibles.length > 0 ? (
                        <div className="space-y-2">
                          <label className="text-sm font-bold text-slate-400">Temas sugeridos para {formData.grado}</label>
                          <select
                            name="temas"
                            value={formData.temas}
                            onChange={handleChange}
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors"
                          >
                            <option value="">Selecciona un tema o escribe abajo...</option>
                            {temasDisponibles.map((t, i) => <option key={i} value={t}>{t}</option>)}
                          </select>
                        </div>
                      ) : null}
                      <InputField label="Temáticas / Contenidos adicionales" name="temas"
                        value={formData.temas} onChange={handleChange}
                        placeholder="Ej. El ecosistema, la célula..." />
                      <InputField label="Cantidad de Sesiones" name="num_sesiones" type="number"
                        value={formData.num_sesiones} onChange={handleChange} />
                    </div>

                    <InputField
                      label="Producto Final de Unidad"
                      name="producto_final"
                      value={formData.producto_final}
                      onChange={handleChange}
                      placeholder="Ej. Maqueta, ensayo argumentativo, infografía, prototipo..."
                    />
                    <p className="text-xs text-slate-500 italic">El producto final gobierna la rúbrica analítica generada.</p>
                  </div>
                )}

                {step === 2 && type === 'sesion' && (
                  <div className="space-y-5">
                    <InputField label="Título de la Unidad" name="titulo_unidad"
                      value={formData.titulo_unidad} onChange={handleChange}
                      placeholder="Ej. Cuidamos el medio ambiente" />
                    {temasDisponibles.length > 0 ? (
                      <SelectField label={`Tema sugerido para ${formData.area} - ${formData.grado}`}
                        name="tema" value={formData.tema} onChange={handleChange}
                        options={temasDisponibles} />
                    ) : (
                      <InputField label="Tema de la Sesión" name="tema"
                        value={formData.tema} onChange={handleChange}
                        placeholder="Ej. Las plantas medicinales" />
                    )}
                    <SelectField label="Metodología Activa" name="metodologia"
                      value={formData.metodologia} onChange={handleChange}
                      options={['ERCA', 'ABP', 'Aula Invertida']} />
                    <p className="text-xs text-slate-500 italic">La metodología define la estructura de Inicio/Desarrollo/Cierre.</p>
                  </div>
                )}

                {/* Step 3: Summary */}
                {step === 3 && (
                  <div className="bg-indigo-500/10 border border-indigo-500/20 p-6 rounded-2xl space-y-5">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="text-emerald-400 w-7 h-7 mt-0.5" />
                      <div>
                        <h3 className="font-bold text-lg text-white">Resumen de Configuración</h3>
                        <p className="text-slate-400 text-sm">Revisa antes de iniciar la generación.</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <PreviewItem label="Área" value={formData.area} />
                      <PreviewItem label="Grado" value={formData.grado} />
                      <PreviewItem label="Tipo" value={type === 'unidad' ? 'Unidad Didáctica' : 'Sesión de Aprendizaje'} />
                      {type === 'unidad' && <PreviewItem label="N° Sesiones" value={formData.num_sesiones} />}
                    </div>
                    {type === 'unidad' && (
                      <div className="space-y-3">
                        <PreviewItem label="Competencias"
                          value={competenciasPorArea.filter(c => formData.competencias.includes(String(c.numero))).map(c => `${c.numero}. ${c.nombre}`).join(' | ') || 'Ninguna seleccionada'} />
                        <PreviewItem label="Temáticas" value={formData.temas || 'La IA elegirá temas apropiados'} />
                        <PreviewItem label="Producto Final" value={formData.producto_final || 'La IA definirá un producto apropiado'} />
                      </div>
                    )}
                    {type === 'sesion' && (
                      <div className="space-y-3">
                        <PreviewItem label="Unidad" value={formData.titulo_unidad} />
                        <PreviewItem label="Tema" value={formData.tema} />
                        <PreviewItem label="Metodología" value={formData.metodologia} />
                      </div>
                    )}
                    {type === 'unidad' && (
                      <div className="bg-indigo-900/30 rounded-xl px-4 py-3 flex items-center gap-2 text-sm text-indigo-300">
                        <Zap size={16} />
                        <span>Puedes generar con <strong>streaming</strong> para ver el texto aparecer en tiempo real.</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex justify-between pt-6 border-t border-slate-800">
            <button onClick={handleBack} disabled={step === 1 || loading || isStreaming}
              className="flex items-center gap-2 text-slate-400 hover:text-white disabled:opacity-30 transition-colors font-bold">
              <ChevronLeft size={20} /> Atrás
            </button>

            <div className="flex gap-3">
              {step < totalSteps ? (
                <button onClick={handleNext}
                  disabled={loading || isStreaming || (step === 1 && !isStep1Valid)}
                  className="bg-slate-800 hover:bg-slate-700 px-6 py-2 rounded-xl transition-all flex items-center gap-2 font-bold disabled:opacity-50">
                  Siguiente <ChevronRight size={20} />
                </button>
              ) : (
                <>
                  {type === 'unidad' && (
                    <button onClick={handleGenerateStream} disabled={loading || isStreaming}
                      className="border border-indigo-500 text-indigo-400 hover:bg-indigo-500/10 px-5 py-2 rounded-xl transition-all flex items-center gap-2 font-bold disabled:opacity-50">
                      <Zap size={16} /> Streaming
                    </button>
                  )}
                  <button onClick={handleGenerate} disabled={loading || isStreaming}
                    className="bg-indigo-600 hover:bg-indigo-500 px-7 py-2 rounded-xl transition-all flex items-center gap-2 font-bold shadow-lg shadow-indigo-500/20">
                    {loading ? 'Generando...' : 'Generar'} <Wand2 size={18} />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function InputField({ label, ...props }) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-bold text-slate-400">{label}</label>
      <input className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors" {...props} />
    </div>
  )
}

function SelectField({ label, options, ...props }) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-bold text-slate-400">{label}</label>
      <select className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 focus:outline-none focus:border-indigo-500 transition-colors appearance-none" {...props}>
        <option value="" disabled>Selecciona una opción...</option>
        {options.map((opt, i) => (
          <option key={i} value={typeof opt === 'object' ? opt.value : opt}>
            {typeof opt === 'object' ? opt.label : opt}
          </option>
        ))}
      </select>
    </div>
  )
}

function PreviewItem({ label, value }) {
  return (
    <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
      <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 block">{label}</label>
      <p className="text-slate-200 text-sm font-medium leading-snug">{value || 'No especificado'}</p>
    </div>
  )
}
