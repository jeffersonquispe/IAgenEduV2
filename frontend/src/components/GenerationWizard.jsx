import { useState, useEffect, useRef } from 'react'
import { Wand2, Loader2, CheckCircle2, Circle, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { api } from '../lib/api'
import { toast, confirmar, mensajeDeError } from '../lib/notify'
import Modal from './ui/Modal'
import Button from './ui/Button'
import { InputField, SelectField } from './ui/Field'

const stripMarkdownForPreview = (text) => {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/^#+\s+/gm, '')
    .replace(/^(---+|===+)$/gm, '')
    .replace(/^\s*[-*•]\s+/gm, '')
    .replace(/\|.+?\|/g, match => {
      const cells = match.split('|').map(c => c.trim()).filter(c => c)
      return cells.join(' — ')
    })
}

// HU-43: mismas reglas que valida el servidor (GenerationService.normalizar_recurso_previo).
const MAX_LARGO_RECURSO_PREVIO = 500
const PATRON_RECURSO_PREVIO = /^https?:\/\/[^\s<>"'`{}|\\^]+$/i
const errorRecursoPrevio = (valor) => {
  const v = (valor || '').trim()
  if (!v) return null
  if (v.length > MAX_LARGO_RECURSO_PREVIO) return `Máximo ${MAX_LARGO_RECURSO_PREVIO} caracteres.`
  if (!PATRON_RECURSO_PREVIO.test(v)) return 'Debe ser un enlace que empiece con http:// o https:// y no tenga espacios.'
  return null
}

// HU-46: datos informativos opcionales de la Unidad (mismas reglas que el servidor,
// core/datos_informativos.py). Dejarlos vacíos nunca bloquea el avance.
const MAX_LARGO_SECCIONES = 100
const errorFechas = (inicio, termino) =>
  inicio && termino && termino < inicio ? 'La fecha de término no puede ser anterior a la de inicio.' : null

// HU-45: Lineamientos.docx restringe la Unidad a "Competencia (Máximo hasta
// 2 competencias)" — evita diluir el foco pedagógico de la unidad.
const MAX_COMPETENCIAS_UNIDAD = 2

// Etapas visibles de una generación. El servidor informa `status` y `etapa` (generando | validando).
const ETAPAS = [
  { id: 'cola', titulo: 'En cola', detalle: 'Esperando turno para generar.' },
  { id: 'generando', titulo: 'Generando con IA', detalle: 'Redactando el documento con el contexto curricular oficial.' },
  { id: 'validando', titulo: 'Validando y estructurando', detalle: 'Revisando la estructura y dando formato.' },
]
const indiceEtapa = (etapaActual) => Math.max(0, ETAPAS.findIndex(e => e.id === etapaActual))

export default function GenerationWizard({ isOpen, onClose, type, onComplete }) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [validando, setValidando] = useState(false)
  const [etapaActual, setEtapaActual] = useState('cola')
  const [intento, setIntento] = useState(false)   // ya intentó avanzar: se muestran los errores en línea
  const [streamText, setStreamText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  // Contador de ejecución: cerrar el wizard lo incrementa y el bucle de polling
  // de esa ejecución termina (el job sigue en el servidor). Un contador, y no un
  // booleano, evita que un bucle viejo reviva si se inicia otra generación.
  const ejecucion = useRef(0)

  const [dataOptions, setDataOptions] = useState({
    areas: [], grados: [], temas_por_area: {}
  })
  const [competenciasPorArea, setCompetenciasPorArea] = useState([])
  const [temasDisponibles, setTemasDisponibles] = useState([])
  const [unidadesDisponibles, setUnidadesDisponibles] = useState([])

  const [formData, setFormData] = useState({
    area: '',
    grado: '',
    competencias: [],
    temas: '',
    num_sesiones: 6,
    producto_final: '',
    unidad_id: '',
    titulo_unidad: '',
    tema: '',
    metodologia: 'ERCA',
    recurso_previo: '',
    secciones: '',
    fecha_inicio: '',
    fecha_termino: '',
  })

  useEffect(() => {
    if (!isOpen) return
    api.get('/data/options').then(res => {
      setDataOptions({ areas: res.data.areas, grados: res.data.grados, temas_por_area: res.data.temas_por_area || {} })
    }).catch(console.error)
  }, [isOpen])

  // HU-22: unidades ya generadas por el docente, para elegir en vez de retipear el título.
  useEffect(() => {
    if (!isOpen || type !== 'sesion') return
    api.get('/data/unidades')
      .then(res => setUnidadesDisponibles(res.data || []))
      .catch(() => setUnidadesDisponibles([]))
  }, [isOpen, type])

  useEffect(() => {
    if (!formData.area) { setCompetenciasPorArea([]); return }
    api.get(`/data/competencias?area=${encodeURIComponent(formData.area)}`)
      .then(res => setCompetenciasPorArea(res.data || []))
      .catch(() => setCompetenciasPorArea([]))
    setFormData(f => ({ ...f, competencias: [], tema: '' }))
    setTemasDisponibles([])
  }, [formData.area])

  useEffect(() => {
    if (!formData.area || !formData.grado) { setTemasDisponibles([]); return }
    api.get(`/data/temas?area=${encodeURIComponent(formData.area)}&grado=${encodeURIComponent(formData.grado)}`)
      .then(res => setTemasDisponibles(res.data.temas || []))
      .catch(() => setTemasDisponibles([]))
  }, [formData.area, formData.grado])

  // Al desmontar el componente se detiene el polling de una generación en curso (el job sigue en
  // el servidor). Va ANTES del `return` anticipado: todos los hooks deben ejecutarse en cada render,
  // abierto o cerrado; si no, React lanza "Rendered more hooks than during the previous render".
  useEffect(() => () => { ejecucion.current++ }, [])

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

  const handleUnidadSelect = e => {
    const unidadId = e.target.value
    const unidad = unidadesDisponibles.find(u => u.id === unidadId)
    setFormData(f => ({ ...f, unidad_id: unidadId, titulo_unidad: unidad ? unidad.title : f.titulo_unidad }))
  }

  const toggleCompetencia = (valor) => setFormData(f => {
    const ya = f.competencias.includes(valor)
    if (ya) return { ...f, competencias: f.competencias.filter(v => v !== valor) }
    if (f.competencias.length >= MAX_COMPETENCIAS_UNIDAD) return f
    return { ...f, competencias: [...f.competencias, valor] }
  })

  // Errores en línea (mismas reglas que antes; ya no se avisan con alert).
  const errorSesiones = type === 'unidad' && !(Number.parseInt(formData.num_sesiones, 10) >= 1)
    ? 'Indica al menos 1 sesión.' : null
  const errorPaso = (n) => {
    if (n === 1 && !(formData.area && formData.grado)) return 'Elige el área curricular y el grado para continuar.'
    if (n === 2 && type === 'unidad') return errorSesiones || errorFechas(formData.fecha_inicio, formData.fecha_termino)
    if (n === 2 && type === 'sesion' && formData.metodologia === 'Aula Invertida') {
      const e = errorRecursoPrevio(formData.recurso_previo)
      return e && `Recurso previo: ${e}`
    }
    return null
  }

  const handleNext = () => {
    if (errorPaso(step)) { setIntento(true); return }
    setIntento(false)
    setStep(s => Math.min(s + 1, totalSteps))
  }
  const handleBack = () => { setIntento(false); setStep(s => Math.max(s - 1, 1)) }

  // HU-33: la generación corre como job en segundo plano. Se crea el job (202) y
  // se consulta su estado cada pocos segundos; si el docente cierra el wizard o la
  // pestaña, el trabajo NO se pierde: sigue en el servidor y el Dashboard lo
  // muestra. El texto parcial del polling mantiene la vista previa en vivo.
  const generarComoJob = async (endpoint, payload) => {
    setIsStreaming(true)
    setValidando(false)
    setEtapaActual('cola')
    setStreamText('')
    const miEjecucion = ++ejecucion.current

    const INTERVALO_MS = 2500
    const TIMEOUT_MS = 15 * 60 * 1000
    const MAX_ERRORES_RED_SEGUIDOS = 5

    try {
      const { data: creado } = await api.post(endpoint, payload)
      const jobId = creado.job_id
      const inicio = Date.now()
      let erroresRed = 0

      while (ejecucion.current === miEjecucion) {
        await new Promise(r => setTimeout(r, INTERVALO_MS))
        if (ejecucion.current !== miEjecucion) return

        let job
        try {
          job = (await api.get(`/generate/jobs/${jobId}`)).data
          erroresRed = 0
        } catch (err) {
          // Un corte momentáneo de red no debe tirar una generación que sigue viva.
          if (++erroresRed >= MAX_ERRORES_RED_SEGUIDOS) throw err
          continue
        }

        if (job.texto_parcial) setStreamText(stripMarkdownForPreview(job.texto_parcial))
        setValidando(job.etapa === 'validando')
        setEtapaActual(job.status === 'pending' ? 'cola' : job.etapa === 'validando' ? 'validando' : 'generando')

        if (job.status === 'done') {
          onComplete(job.resultado)
          onClose()
          return
        }
        if (job.status === 'failed') {
          toast.error('Error en generación: ' + (job.error || 'falló sin detalle'))
          return
        }
        if (Date.now() - inicio > TIMEOUT_MS) {
          toast.info('La generación sigue en curso. Puedes cerrar esta ventana: aparecerá en tu panel cuando termine.')
          return
        }
      }
    } catch (err) {
      console.error('[generarComoJob] Error:', err)
      toast.error('Error en generación: ' + mensajeDeError(err))
    } finally {
      // Si el wizard se cerró (o arrancó otra ejecución), handleClose ya limpió el
      // estado; no pisar el de la ejecución nueva.
      if (ejecucion.current === miEjecucion) {
        setIsStreaming(false)
        setValidando(false)
      }
    }
  }

  // Cerrar durante una generación detiene el polling, no el trabajo: el job sigue
  // en el servidor y aparece en el Dashboard.
  const hayDatos = Boolean(formData.area || formData.grado || formData.tema || formData.temas || formData.producto_final)
  const pedirCierre = async () => {
    if (hayDatos && !isStreaming && !(await confirmar({
      titulo: 'Descartar configuración',
      mensaje: 'Si cierras ahora se perderá lo que llevas escrito. ¿Cerrar de todas formas?',
      confirmar: 'Cerrar y descartar',
      cancelar: 'Seguir editando',
      peligro: true,
    }))) return
    handleClose()
  }

  const handleClose = () => {
    ejecucion.current++
    setIsStreaming(false)
    setValidando(false)
    onClose()
  }

  const handleGenerateUnidad = async () => {
    const competenciasTexto = competenciasPorArea
      .filter(c => formData.competencias.includes(String(c.numero)))
      .map(c => `COMPETENCIA ${c.numero}. ${c.nombre}`)

    const payload = {
      area: formData.area,
      grado: formData.grado,
      competencias: competenciasTexto,
      temas: formData.temas,
      num_sesiones: formData.num_sesiones,
      producto_final: formData.producto_final,
      modo: 'completo',
    }

    // HU-46: solo se envían los datos informativos que el docente completó.
    const errorDeFechas = errorFechas(formData.fecha_inicio, formData.fecha_termino)
    if (errorDeFechas) { setIntento(true); setStep(2); return }
    if (formData.secciones.trim()) payload.secciones = formData.secciones.trim()
    if (formData.fecha_inicio) payload.fecha_inicio = formData.fecha_inicio
    if (formData.fecha_termino) payload.fecha_termino = formData.fecha_termino

    await generarComoJob('/generate/unidad/jobs', payload)
  }

  const handleGenerateSesion = async () => {
    const payload = {
      area: formData.area,
      grado: formData.grado,
      unidad_id: formData.unidad_id || undefined,
      titulo_unidad: formData.titulo_unidad,
      tema: formData.tema,
      metodologia: formData.metodologia,
      modo: 'completo',
    }

    // HU-43: el enlace solo aplica a Aula Invertida; vacío = comportamiento anterior.
    if (formData.metodologia === 'Aula Invertida' && formData.recurso_previo.trim()) {
      const error = errorRecursoPrevio(formData.recurso_previo)
      if (error) { setIntento(true); setStep(2); return }
      payload.recurso_previo = formData.recurso_previo.trim()
    }

    await generarComoJob('/generate/sesion/jobs', payload)
  }

  const statusMessage = validando ? 'Validando y estructurando...' : 'Generando con IA...'

  return (
    <Modal titulo={`Generador de ${type === 'unidad' ? 'Unidad Didáctica' : 'Sesión de Aprendizaje'}`}
      onClose={pedirCierre} cerrarConClicFuera={false}>
        <div role="progressbar" aria-label="Progreso del asistente" aria-valuemin={1} aria-valuemax={totalSteps} aria-valuenow={step}
          className="absolute top-0 left-0 h-1 bg-accent transition-all duration-500" style={{ width: `${(step / totalSteps) * 100}%` }} />

        <div className="p-8">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h2 className="text-2xl font-bold">Generador de {type === 'unidad' ? 'Unidad Didáctica' : 'Sesión de Aprendizaje'}</h2>
              <p className="text-fg-muted text-sm">Paso {step} de {totalSteps}: {steps[step - 1].title}</p>
            </div>
            <button onClick={pedirCierre} aria-label="Cerrar" className="p-2 hover:bg-surface-2 rounded-full transition-colors"><X size={20} /></button>
          </div>

          <div className="min-h-[280px] mb-8">
            {(loading || isStreaming) ? (
              <div role="status" aria-live="polite" className="flex flex-col gap-5 pt-2">
                <ol className="space-y-3">
                  {ETAPAS.map((e, i) => {
                    const actual = indiceEtapa(etapaActual)
                    const hecha = i < actual
                    const enCurso = i === actual
                    return (
                      <li key={e.id} aria-current={enCurso ? 'step' : undefined}
                        className={`flex items-start gap-3 ${enCurso || hecha ? '' : 'opacity-50'}`}>
                        {hecha ? <CheckCircle2 className="w-5 h-5 text-success-text shrink-0 mt-0.5" aria-hidden="true" />
                          : enCurso ? <Loader2 className="w-5 h-5 text-accent-text animate-spin shrink-0 mt-0.5" aria-hidden="true" />
                          : <Circle className="w-5 h-5 text-fg-subtle shrink-0 mt-0.5" aria-hidden="true" />}
                        <div>
                          <p className="font-bold text-sm">{e.titulo}{hecha && <span className="sr-only"> (completado)</span>}</p>
                          {enCurso && <p className="text-xs text-fg-muted">{e.detalle}</p>}
                        </div>
                      </li>
                    )
                  })}
                </ol>
                <p className="text-xs text-fg-subtle">
                  Puedes cerrar esta ventana: la generación continúa y aparecerá en tu panel cuando termine.
                </p>
                {isStreaming && streamText && (
                  <details className="w-full">
                    <summary className="text-xs font-bold text-accent-text cursor-pointer">Ver avance del texto</summary>
                    <div className="mt-2 bg-surface-2 rounded-xl p-4 max-h-40 overflow-y-auto text-xs text-fg-muted whitespace-pre-wrap break-words">
                      {streamText}
                    </div>
                  </details>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {step === 1 && (
                  <div className="grid grid-cols-2 gap-6">
                    <SelectField label="Área Curricular" name="area" value={formData.area}
                      onChange={handleChange} options={dataOptions.areas} />
                    <SelectField label="Grado" name="grado" value={formData.grado}
                      onChange={handleChange} options={dataOptions.grados} />
                    {intento && errorPaso(1) && (
                      <p role="alert" className="col-span-2 text-sm text-danger-text">{errorPaso(1)}</p>
                    )}
                    {formData.area && (
                      <div className="col-span-2 bg-accent/10 border border-accent/20 rounded-xl px-4 py-3 text-sm text-accent-text">
                        Las competencias disponibles se cargarán automáticamente para <strong>{formData.area}</strong>.
                      </div>
                    )}
                  </div>
                )}

                {step === 2 && type === 'unidad' && (
                  <div className="space-y-5">
                    <fieldset className="space-y-2">
                      <legend className="text-sm font-bold text-fg-muted">
                        Competencias de <span className="text-accent-text">{formData.area}</span>
                        {' '}— elige hasta {MAX_COMPETENCIAS_UNIDAD}
                      </legend>
                      {competenciasPorArea.length === 0 ? (
                        <div className="text-fg-subtle text-sm bg-surface-2 p-4 rounded-xl">
                          No se encontraron competencias para esta área. Selecciona otra área en el paso anterior.
                        </div>
                      ) : (
                        <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                          {competenciasPorArea.map(c => {
                            const valor = String(c.numero)
                            const marcada = formData.competencias.includes(valor)
                            const bloqueada = !marcada && formData.competencias.length >= MAX_COMPETENCIAS_UNIDAD
                            return (
                              <label key={c.numero}
                                className={`flex items-start gap-3 rounded-xl border p-3 text-sm transition-colors ${
                                  marcada ? 'border-accent bg-accent/10' : 'border-line'
                                } ${bloqueada ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-surface-2'}`}>
                                <input type="checkbox" className="mt-1 accent-[rgb(var(--accent))]"
                                  checked={marcada} disabled={bloqueada} onChange={() => toggleCompetencia(valor)} />
                                <span><span className="font-bold">{c.numero}.</span> {c.nombre}</span>
                              </label>
                            )
                          })}
                        </div>
                      )}
                      <p className="text-xs text-fg-subtle" aria-live="polite">
                        {formData.competencias.length} de {MAX_COMPETENCIAS_UNIDAD} seleccionada(s)
                        {formData.competencias.length >= MAX_COMPETENCIAS_UNIDAD && ' — para cambiar una, desmarca otra primero'}
                        {' '}· elegir pocas competencias enfoca mejor el aprendizaje de la unidad.
                      </p>
                    </fieldset>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label htmlFor="wizard-temas" className="text-sm font-bold text-fg-muted">
                          Temáticas / contenidos
                        </label>
                        <input id="wizard-temas" name="temas" list="wizard-temas-sugeridos" value={formData.temas}
                          onChange={handleChange} placeholder="Ej. El ecosistema, la célula..."
                          className="w-full bg-surface border border-line rounded-xl px-4 py-2 text-fg placeholder:text-fg-subtle focus:outline-none focus:border-accent transition-colors" />
                        <datalist id="wizard-temas-sugeridos">
                          {temasDisponibles.map((t, i) => <option key={i} value={t} />)}
                        </datalist>
                        {temasDisponibles.length > 0 && (
                          <p className="text-xs text-fg-subtle">Empieza a escribir para ver temas sugeridos para {formData.grado}.</p>
                        )}
                      </div>
                      <div className="space-y-1">
                        <InputField label="Cantidad de sesiones" name="num_sesiones" type="number" min={1}
                          value={formData.num_sesiones} onChange={handleChange}
                          aria-invalid={Boolean(errorSesiones)} />
                        {intento && errorSesiones && <p role="alert" className="text-xs text-danger-text">{errorSesiones}</p>}
                      </div>
                    </div>

                    <InputField
                      label="Producto Final de Unidad"
                      name="producto_final"
                      value={formData.producto_final}
                      onChange={handleChange}
                      placeholder="Ej. Maqueta, ensayo argumentativo, infografía, prototipo..."
                    />
                    <p className="text-xs text-fg-subtle italic">El producto final gobierna la rúbrica analítica generada.</p>

                    <details className="rounded-xl border border-line p-4" open={Boolean(formData.secciones || formData.fecha_inicio || formData.fecha_termino)}>
                      <summary className="cursor-pointer text-sm font-bold text-fg-muted">Datos informativos (opcional)</summary>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                      <InputField label="Secciones " name="secciones"
                        value={formData.secciones} onChange={handleChange}
                        maxLength={MAX_LARGO_SECCIONES} placeholder="Ej. 3ro A y 3ro B" />
                      <InputField label="Fecha de inicio " name="fecha_inicio" type="date"
                        value={formData.fecha_inicio} onChange={handleChange} />
                      <InputField label="Fecha de término " name="fecha_termino" type="date"
                        value={formData.fecha_termino} min={formData.fecha_inicio || undefined}
                        onChange={handleChange} />
                    </div>
                    {errorFechas(formData.fecha_inicio, formData.fecha_termino)
                      ? <p role="alert" className="text-xs text-danger-text mt-2">{errorFechas(formData.fecha_inicio, formData.fecha_termino)}</p>
                      : <p className="text-xs text-fg-subtle italic mt-2">Se incluyen en los Datos Informativos junto con la UGEL y la coordinación de tu perfil institucional.</p>}
                    </details>
                  </div>
                )}

                {step === 2 && type === 'sesion' && (
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label htmlFor="wizard-unidad" className="text-sm font-bold text-fg-muted">Unidad Didáctica a la que pertenece</label>
                      <select
                        id="wizard-unidad"
                        name="unidad_id"
                        value={formData.unidad_id}
                        onChange={handleUnidadSelect}
                        className="w-full bg-surface border border-line rounded-xl px-4 py-2 text-fg focus:outline-none focus:border-accent transition-colors"
                      >
                        <option value="">— Sin unidad asociada —</option>
                        {unidadesDisponibles.map(u => (
                          <option key={u.id} value={u.id}>{u.title}</option>
                        ))}
                      </select>
                      {formData.unidad_id ? (
                        <p className="text-xs text-fg-subtle">
                          Las competencias de esta unidad se reutilizarán automáticamente.
                        </p>
                      ) : (
                        <InputField label="Título de la Unidad (si no está en la lista)" name="titulo_unidad"
                          value={formData.titulo_unidad} onChange={handleChange}
                          placeholder="Ej. Cuidamos el medio ambiente" />
                      )}
                    </div>
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
                    <p className="text-xs text-fg-subtle italic">La metodología define la estructura de Inicio/Desarrollo/Cierre.</p>
                    {formData.metodologia === 'Aula Invertida' && (
                      <div className="space-y-1">
                        <InputField label="Recurso previo (enlace, opcional)" name="recurso_previo" type="url"
                          value={formData.recurso_previo} onChange={handleChange}
                          maxLength={MAX_LARGO_RECURSO_PREVIO}
                          aria-invalid={Boolean(errorRecursoPrevio(formData.recurso_previo))}
                          placeholder="https://www.youtube.com/watch?v=..." />
                        {errorRecursoPrevio(formData.recurso_previo)
                          ? <p role="alert" className="text-xs text-danger-text">{errorRecursoPrevio(formData.recurso_previo)}</p>
                          : <p className="text-xs text-fg-subtle italic">Video o lectura que los estudiantes revisan en casa. Si lo dejas vacío, la sesión citará una referencia genérica.</p>}
                      </div>
                    )}
                  </div>
                )}

                {step === 3 && (
                  <div className="bg-accent/10 border border-accent/20 p-6 rounded-2xl space-y-5">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="text-success-text w-7 h-7 mt-0.5" />
                      <div>
                        <h3 className="font-bold text-lg text-fg">Resumen de Configuración</h3>
                        <p className="text-fg-muted text-sm">Revisa antes de iniciar la generación.</p>
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
                        {(formData.secciones.trim() || formData.fecha_inicio || formData.fecha_termino) && (
                          <PreviewItem label="Datos informativos"
                            value={[
                              formData.secciones.trim() && `Secciones: ${formData.secciones.trim()}`,
                              formData.fecha_inicio && `Inicio: ${formData.fecha_inicio}`,
                              formData.fecha_termino && `Término: ${formData.fecha_termino}`,
                            ].filter(Boolean).join(' · ')} />
                        )}
                      </div>
                    )}
                    {type === 'sesion' && (
                      <div className="space-y-3">
                        <PreviewItem label="Unidad" value={formData.titulo_unidad} />
                        <PreviewItem label="Tema" value={formData.tema} />
                        <PreviewItem label="Metodología" value={formData.metodologia} />
                        {formData.metodologia === 'Aula Invertida' && formData.recurso_previo.trim() && (
                          <PreviewItem label="Recurso previo" value={formData.recurso_previo.trim()} />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex justify-between pt-6 border-t border-line">
            <button onClick={handleBack} disabled={step === 1 || isStreaming}
              className="flex items-center gap-2 text-fg-muted hover:text-fg disabled:opacity-30 transition-colors font-bold">
              <ChevronLeft size={20} /> Atrás
            </button>

            <div className="flex gap-3">
              {step < totalSteps ? (
                <button onClick={handleNext}
                  disabled={isStreaming}
                  className="bg-surface-2 hover:bg-line px-6 py-2 rounded-xl transition-all flex items-center gap-2 font-bold disabled:opacity-50">
                  Siguiente <ChevronRight size={20} />
                </button>
              ) : (
                <button
                  onClick={type === 'unidad' ? handleGenerateUnidad : handleGenerateSesion}
                  disabled={isStreaming}
                  className="bg-accent hover:bg-accent-hover text-white px-7 py-2 rounded-xl transition-all flex items-center gap-2 font-bold">
                  {isStreaming ? 'Generando...' : 'Generar'} <Wand2 size={18} />
                </button>
              )}
            </div>
          </div>
        </div>
    </Modal>
  )
}

function PreviewItem({ label, value }) {
  return (
    <div className="bg-surface/60 p-3 rounded-xl border border-line">
      <span className="text-xs font-bold text-fg-subtle uppercase tracking-wider mb-1 block">{label}</span>
      <p className="text-fg text-sm font-medium leading-snug">{value || 'No especificado'}</p>
    </div>
  )
}
