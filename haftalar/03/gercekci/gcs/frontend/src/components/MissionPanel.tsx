import { ArrowDownToLine, ArrowUpFromLine, Check, Circle, Code2, Flag, LockKeyhole, Pause, Play } from 'lucide-react'
import type { Command, GcsState, MissionId, MissionStep, SendCommand } from '../types'
import { duration } from '../format'

const MISSIONS: Record<MissionId, { name: string; description: string; steps: string[] }> = {
  G1: { name: 'Sekiz uçuşu', description: 'Direkler çevresinde iki tur', steps: ['Hazırlık ve kalkış', 'Direk 2 dışından geçiş', 'Birinci sonsuz turu', 'İkinci sonsuz turu', 'Dış dönüş ve bitiş', 'İniş ve DISARM'] },
  G2: { name: 'Hedef ve yük', description: 'İki hedefi bul, yükleri bırak', steps: ['Hazırlık ve kalkış', 'Direk 2 dışından giriş', 'Tek RGB ile hedef arama', 'İlk hedefe uygun yük bırakma', 'İkinci hedefe uygun yük bırakma', 'Dönüş ve iniş'] },
  G3: { name: 'Geri al ve taşı', description: 'İlk yükü yeniden kavra ve aktar', steps: ['Hazırlık ve kalkış', 'Direk 2 dış geçişi', 'Hedefleri bul ve iki yükü bırak', 'İlk yükü RGB ile bul ve kavra', 'Diğer hedefe taşı ve bırak', 'Dönüş ve iniş'] },
}

export function MissionPanel({ state, selected, setSelected, pending, send, openCode }: { state: GcsState; selected: MissionId; setSelected: (id: MissionId) => void; pending: string | null; send: SendCommand; openCode: () => void }) {
  const mission = state.mission
  const running = mission.status === 'running' || mission.status === 'paused'
  const activeId = running && mission.id ? mission.id : selected
  const locked = running || Boolean(state.vehicle.armed) || pending === 'mission_start'
  const paused = running && (mission.paused || mission.status === 'paused')
  const steps: MissionStep[] = running && mission.steps?.length ? mission.steps : MISSIONS[activeId].steps.map((label, i) => ({ id: String(i), label }))
  const disabled = !state.connected || pending !== null
  const run = (command: Command) => { void send(command).catch(() => undefined) }
  return <section className="panel mission-panel">
    <div className="panel-heading"><h2><Flag size={21} />Görev seçimi</h2><button className="text-button teaching-link" onClick={openCode}><Code2 size={15} />Canlı Kod</button></div>
    <div className="mission-choices" role="group" aria-label="Başlatılacak görev">
      {(['G1', 'G2', 'G3'] as const).map(id => <button key={id} className={`mission-choice ${activeId === id ? 'selected' : ''}`} aria-label={`${id} ${MISSIONS[id].name}`} aria-pressed={activeId === id} disabled={locked} onClick={() => setSelected(id)}><strong>{id}</strong><span>{MISSIONS[id].name}</span><small>{MISSIONS[id].description}</small></button>)}
    </div>
    <div className={`mission-context ${running ? 'is-running' : ''}`} data-testid="mission-context">
      <div><span className="eyebrow">{running ? 'ÇALIŞAN GÖREV' : 'SEÇİLEN PLAN'}</span><strong>{activeId} · {running ? mission.phase_label ?? MISSIONS[activeId].name : MISSIONS[activeId].name}</strong></div><time className="mission-clock">{running ? duration(mission.elapsed_s) : 'Ön izleme'}</time>
    </div>
    {locked ? <p className="mission-selection-note"><LockKeyhole size={12} />{running ? 'Görev sürerken seçim kilitli. Bekletme görevi değiştirmez.' : 'Motorlar ARM; görev seçimi güvenli DISARM sonrasında açılır.'}</p> : <p className="mission-selection-note">{mission.id && mission.status && mission.status !== 'idle' ? `Son oturum: ${mission.id} · ${mission.status === 'completed' ? 'tamamlandı' : mission.status === 'failed' ? 'başarısız' : mission.status}. Bu liste seçilen yeni planı gösterir.` : 'Bir görev seçin; başlat düğmesi yalnız bu planı çalıştırır.'}</p>}
    <ol className="mission-timeline">{steps.map((step, index) => {
      const done = running && (step.status === 'completed' || step.status === 'done' || index < (mission.step_index ?? -1))
      const current = running && !done && (step.status === 'active' || step.status === 'running' || index === mission.step_index)
      return <li key={step.id} className={`${done ? 'done' : ''} ${current ? 'current' : ''}`}><span className="step-marker">{done ? <Check size={13} strokeWidth={3} /> : current ? <span /> : <Circle size={18} />}</span><span className="step-label">{index + 1}. {step.label}</span><span className={`step-status ${done ? 'completed' : ''} ${current ? 'running' : ''}`}>{done ? 'Tamamlandı' : current ? paused ? 'Bekletildi' : 'Devam ediyor' : running ? 'Bekliyor' : 'Plan'}</span></li>
    })}</ol>
    <div className="mission-actions"><button className="button button-primary" disabled={disabled || running} onClick={() => run({ action: 'mission_start', mission: selected })}><Play size={17} />{pending === 'mission_start' ? 'Başlatılıyor…' : `${selected} Görevini Başlat`}</button><button className="button button-quiet" disabled={disabled || !running} onClick={() => run({ action: 'mission_pause' })}>{paused ? <Play size={17} /> : <Pause size={17} />}{paused ? 'Devam Et' : 'Beklet'}</button><button className="button button-quiet" disabled={disabled} onClick={() => run({ action: 'land' })}><ArrowDownToLine size={18} />İniş</button></div>
    <div className="preflight-actions"><span className={`arm-state ${state.vehicle.armed ? 'armed' : ''}`}><span />{state.connected ? state.vehicle.armed ? 'Motorlar ARM' : 'Motorlar güvenli' : 'Telemetri bekleniyor'}</span><button className="text-button" disabled={disabled || state.vehicle.armed} onClick={() => run({ action: 'arm' })}><LockKeyhole size={13} />ARM</button><button className="text-button" disabled={disabled || !state.vehicle.armed} onClick={() => run({ action: 'takeoff', altitude_m: 8 })}><ArrowUpFromLine size={14} />Kalkış · 8 m</button></div>
  </section>
}
