import { useEffect, useRef, useState } from 'react'
import type { CodeFile, CodeSource, CodeTrace, TraceEvent } from './types'

const EMPTY_TRACE: CodeTrace = { seq: 0, events: [], status: 'idle', active: false }
const SOURCE_CACHE = new Map<string, CodeSource>()

async function readJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { cache: 'no-store', signal })
  if (!response.ok) throw new Error(`Kod servisi yanıtı: ${response.status}`)
  return response.json() as Promise<T>
}

export function useCodeTrace() {
  const [files, setFiles] = useState<CodeFile[]>([])
  const [trace, setTrace] = useState<CodeTrace>(EMPTY_TRACE)
  const [history, setHistory] = useState<TraceEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const cursor = useRef(0)
  const runId = useRef<string | null | undefined>(undefined)
  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout>
    let controller: AbortController | null = null
    let catalogLoaded = false
    async function poll() {
      controller = new AbortController()
      const timeout = setTimeout(() => controller?.abort(), 2400)
      try {
        const [next, catalog] = await Promise.all([
          readJson<CodeTrace>(`/api/code/trace?after=${cursor.current}&limit=120`, controller.signal),
          catalogLoaded ? Promise.resolve(null) : readJson<{ files: CodeFile[] }>('/api/code/catalog', controller.signal),
        ])
        if (!active) return
        if (catalog) { setFiles(catalog.files ?? []); catalogLoaded = true }
        const changedRun = runId.current !== next.run_id
        runId.current = next.run_id
        cursor.current = next.seq ?? 0
        setTrace(next)
        setHistory(previous => {
          const samples = [next.current, next.lanes?.mission, next.lanes?.vision].filter((item): item is TraceEvent => Boolean(item)).map(item => ({ ...item, stack: undefined, wait: undefined }))
          const combined = [...(changedRun ? [] : previous), ...(next.events ?? []), ...samples]
          return [...new Map(combined.map(event => [`${event.lane}:${event.seq}`, event])).values()].sort((a, b) => a.seq - b.seq).slice(-300)
        })
        setError(null)
      } catch {
        if (active) setError('Kod izleme servisine ulaşılamıyor. Son kayıt canlı olarak gösterilmez.')
      } finally {
        clearTimeout(timeout)
        if (active) timer = setTimeout(poll, 250)
      }
    }
    void poll()
    return () => { active = false; clearTimeout(timer); controller?.abort() }
  }, [])
  return { files, trace, history, error }
}

export function useCodeSource(file: string, expectedSha?: string) {
  const [source, setSource] = useState<CodeSource | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    let timer: ReturnType<typeof setTimeout>
    const key = `${file}:${expectedSha ?? ''}`
    const candidate = SOURCE_CACHE.get(key)
    const cached = candidate && (!expectedSha || candidate.sha256 === expectedSha) ? candidate : null
    setSource(previous => cached ?? (previous?.file === file && (!expectedSha || previous.sha256 === expectedSha) ? previous : null))
    setLoading(!cached)
    setError(null)
    // Revalidate cached metadata: mid-run disk edits must remain visible.
    async function refresh() {
      try {
        const next = await readJson<CodeSource>(`/api/code/source?file=${encodeURIComponent(file)}`, controller.signal)
        if (!active) return
        if (next.file !== file || (expectedSha && next.sha256 !== expectedSha)) {
          const retained = expectedSha ? SOURCE_CACHE.get(`${file}:${expectedSha}`) : undefined
          setSource(previous => retained?.file === file && retained.sha256 === expectedSha ? retained
            : previous?.file === file && previous.sha256 === expectedSha ? previous : null)
          setError('Kaynak sürümü bu yürütme kaydıyla uyuşmuyor. Eşleşen eski kaynak varsa korunur; yoksa satırlar gösterilmez. Yeni sunucunun kaynağı için ekranı sürdürüp canlı satırı izleyin.')
          return
        }
        SOURCE_CACHE.set(key, next)
        SOURCE_CACHE.set(`${file}:${next.sha256}`, next)
        setSource(previous => previous?.sha256 === next.sha256 && previous.source_changed === next.source_changed && previous.disk_sha256 === next.disk_sha256 ? previous : next)
        setError(null)
      } catch { if (active) setError('Kaynak dosyası alınamadı. Yerel kod servisini kontrol edin.') }
      finally { if (active) { setLoading(false); timer = setTimeout(refresh, 4000) } }
    }
    void refresh()
    return () => { active = false; clearTimeout(timer); controller.abort() }
  }, [file, expectedSha])
  return { source, error, loading }
}
