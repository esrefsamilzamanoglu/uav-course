import { useCallback, useEffect, useState } from 'react'
import { EMPTY_STATE } from './types'
import type { Command, GcsState } from './types'

export function useGcs() {
  const [state, setState] = useState<GcsState>(EMPTY_STATE)
  const [serverAvailable, setServerAvailable] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [notification, setNotification] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setTimeout>
    let controller: AbortController | null = null
    async function poll() {
      controller = new AbortController()
      const timeout = setTimeout(() => controller?.abort(), 2400)
      try {
        const response = await fetch('/api/state', { signal: controller.signal, cache: 'no-store' })
        if (!response.ok) throw new Error(`Bağlantı yanıtı: ${response.status}`)
        const data = await response.json() as Partial<GcsState>
        if (active) {
          setState({ ...EMPTY_STATE, ...data,
            vehicle: data.vehicle ?? {}, simulation: data.simulation ?? EMPTY_STATE.simulation,
            mission: data.mission ?? EMPTY_STATE.mission, camera: data.camera ?? EMPTY_STATE.camera, follow_camera: data.follow_camera ?? { available: false },
            detections: data.detections ?? [], confirmed_detections: data.confirmed_detections ?? [], grippers: data.grippers ?? {}, scene: data.scene ?? {}, events: data.events ?? [],
          })
          setServerAvailable(true)
          setError(null)
        }
      } catch {
        if (active) {
          setServerAvailable(false)
          setState(previous => ({ ...previous, connected: false, camera: { ...previous.camera, available: false }, follow_camera: { ...previous.follow_camera, available: false } }))
          setError('Yerel görev sunucusuna ulaşılamıyor. Bağlantı yeniden deneniyor.')
        }
      } finally {
        clearTimeout(timeout)
        if (active) timer = setTimeout(poll, 250)
      }
    }
    void poll()
    return () => { active = false; clearTimeout(timer); controller?.abort() }
  }, [])
  const send = useCallback(async (command: Command) => {
    setPending(command.action)
    setNotification(null)
    try {
      const response = await fetch('/api/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(command) })
      const result = await response.json().catch(() => ({})) as { message?: string; error?: string; ok?: boolean }
      if (!response.ok || result.ok === false) throw new Error(result.error ?? result.message ?? 'Komut kabul edilmedi.')
      setNotification(result.message ?? 'Komut gönderildi; araç geri bildirimi bekleniyor.')
    } catch (caught) {
      setNotification(caught instanceof Error ? caught.message : 'Komut gönderilemedi.')
      throw caught
    } finally { setPending(null) }
  }, [])
  return { state, serverAvailable, error, pending, notification, send, clearNotification: () => setNotification(null) }
}
