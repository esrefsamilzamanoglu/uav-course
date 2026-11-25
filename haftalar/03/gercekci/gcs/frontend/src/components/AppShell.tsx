import { useEffect, useState } from 'react'
import { Camera, Clock3, Code2, Crosshair, FileText, Map, Play, Radio, Settings, Square } from 'lucide-react'
import type { Command, GcsState, SendCommand, ViewId } from '../types'

const NAV = [
  { id: 'mission' as const, title: 'Görev', Icon: Crosshair },
  { id: 'map' as const, title: 'Harita', Icon: Map },
  { id: 'camera' as const, title: 'Kamera', Icon: Camera },
  { id: 'code' as const, title: 'Canlı Kod', Icon: Code2 },
  { id: 'logs' as const, title: 'Kayıtlar', Icon: FileText },
  { id: 'system' as const, title: 'Sistem', Icon: Settings },
]

function Brand() {
  return <div className="brand"><svg viewBox="0 0 40 40" aria-hidden="true"><ellipse cx="20" cy="20" rx="16" ry="11" transform="rotate(-28 20 20)" /><ellipse cx="20" cy="20" rx="16" ry="11" transform="rotate(37 20 20)" /><ellipse cx="20" cy="20" rx="11" ry="16" transform="rotate(8 20 20)" /><path d="m15 20 10-5-2 12-3-5z" /></svg><strong>ROTA GCS</strong></div>
}

export function AppHeader({ state, serverAvailable, pending, send }: { state: GcsState; serverAvailable: boolean; pending: string | null; send: SendCommand }) {
  const [clock, setClock] = useState(() => new Date())
  useEffect(() => { const interval = setInterval(() => setClock(new Date()), 1000); return () => clearInterval(interval) }, [])
  const running = state.simulation.running
  const run = (command: Command) => { void send(command).catch(() => undefined) }
  return <header className="app-header">
    <Brand />
    <div className="course-title">Döner Kanat <span>/</span> 2026</div>
    <div className="header-actions">
      <div className={`connection ${state.connected ? 'is-connected' : ''}`} title={state.connected ? 'ArduPilot telemetrisi alınıyor' : serverAvailable ? 'Sunucu hazır; araç bağlantısı bekleniyor' : 'Yerel sunucuya ulaşılamıyor'}><span className="status-dot" /><span>{state.connected ? 'Bağlı (ArduPilot / SITL)' : serverAvailable ? 'Araç bekleniyor' : 'Sunucu bekleniyor'}</span></div>
      <div className="header-clock"><Clock3 size={19} /><time>{clock.toLocaleTimeString('tr-TR', { hour12: false })}</time></div>
      <button className={`button header-start ${running ? 'button-quiet' : 'button-primary'}`} disabled={!serverAvailable || pending !== null} onClick={() => run({ action: running ? 'simulation_stop' : 'simulation_start' })}>{running ? <Square size={17} /> : <Play size={19} />}<span>{pending === 'simulation_start' ? 'Başlatılıyor…' : running ? 'Simülasyonu Durdur' : 'Simülasyonu Başlat'}</span></button>
    </div>
  </header>
}

export function Sidebar({ view, setView, connected }: { view: ViewId; setView: (value: ViewId) => void; connected: boolean }) {
  return <aside className="sidebar"><nav aria-label="Ana gezinme">{NAV.map(({ id, title, Icon }) => <button key={id} className={`nav-item ${view === id ? 'active' : ''}`} aria-current={view === id ? 'page' : undefined} onClick={() => setView(id)}><Icon size={24} strokeWidth={1.75} /><span>{title}</span></button>)}</nav><div className="rail-bottom"><Radio size={16} /><span>{connected ? 'Telemetri canlı' : 'Yerel istasyon'}</span><small>GAZEBO · ARDUPILOT</small></div></aside>
}
