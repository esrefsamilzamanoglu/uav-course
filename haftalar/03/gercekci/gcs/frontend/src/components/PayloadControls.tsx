import { Box, LockKeyhole, LockKeyholeOpen, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import type { Command, GcsState, SendCommand } from '../types'
import { number } from '../format'

export function PayloadControls({ state, pending, send }: { state: GcsState; pending: string | null; send: SendCommand }) {
  const [selected, setSelected] = useState<'red' | 'blue'>('red')
  const disabled = !state.connected || pending !== null
  const channel = selected === 'red' ? 9 : 10
  const run = (command: Command) => { void send(command).catch(() => undefined) }
  const current = state.grippers[selected]
  const measuredPwm = state.vehicle.servo_pwm?.[String(channel)]
  const reasons: Record<string, string> = { open: 'Tutucu açık · yük serbest.', too_far: 'Yakalama için yüke yaklaşın.', too_fast: 'Yakalama için bağıl hızı azaltın.', holding: 'Fiziksel yük bağlı.' }
  return <section className="panel payload-panel">
    <div className="panel-heading"><h2><Box size={23} />Yük ve Tutucu <span>(Gripper)</span></h2></div>
    <div className="payload-rows" role="group" aria-label="Kontrol edilecek yük">{(['red', 'blue'] as const).map(color => {
      const g = state.grippers[color]
      const pwm = g?.pwm ?? state.vehicle.servo_pwm?.[color === 'red' ? '9' : '10']
      const closed = state.connected && pwm != null && pwm >= 1700
      const open = state.connected && pwm != null && pwm <= 1300
      const mass = g?.payload_mass_kg ?? g?.mass_kg
      return <button key={color} className={`payload-row ${selected === color ? 'selected' : ''}`} onClick={() => setSelected(color)} aria-pressed={selected === color} aria-label={`${color === 'red' ? 'Kırmızı' : 'Mavi'} yük tutucusunu seç`}><Box size={23} className={`payload-icon ${color}`} /><strong>{color === 'red' ? 'Kırmızı yük' : 'Mavi yük'}<small className={state.connected && g?.attached ? 'is-attached' : ''}>{!state.connected || !g ? 'Telemetri bekleniyor' : g.attached ? 'Yük bağlı' : 'Yük serbest'}</small></strong><span className="payload-mass">{mass == null ? '— g' : `${Math.round(mass * 1000)} g`}</span><span className="payload-divider" />{closed ? <LockKeyhole size={16} /> : <LockKeyholeOpen size={16} />}<span className="payload-state-label">Tutucu:</span><span className={`state-pill ${closed ? 'closed' : open ? 'open' : 'unknown'}`}>{state.connected ? closed ? 'Kapalı' : open ? 'Açık' : '—' : '—'}</span></button>
    })}</div>
    <div className="servo-heading"><h3><SlidersHorizontal size={19} />Servo Kontrolü <span>(Tutucu)</span></h3><span className="channel-readout" title="ArduPilot SERVO_OUTPUT_RAW ölçümü">CH {channel} · {state.connected ? measuredPwm === 0 ? 'çıkış yok' : `${number(measuredPwm, 0)} µs` : '—'}</span></div>
    <div className="servo-actions"><button className="button button-primary" disabled={disabled} onClick={() => run({ action: 'servo', channel, pwm: 1100 })}><LockKeyholeOpen size={17} />Aç <span>(Open)</span></button><button className="button button-quiet" disabled={disabled} onClick={() => run({ action: 'servo', channel, pwm: 1900 })}><LockKeyhole size={17} />Kapat <span>(Close)</span></button></div>
    <div className="grip-feedback"><span className={`status-dot ${state.connected && current?.attached ? 'green' : ''}`} /><span>{!state.connected ? 'Servo geri bildirimi bekleniyor.' : current?.attached ? `${current.command_source?.includes('preload') ? 'Ön yükleme · ' : ''}Fiziksel yük bağlı · salınım ${number(current.swing_deg)}°` : current?.reject_reason ? reasons[current.reject_reason] ?? current.reject_reason : 'Bağlama için tutucu yükün yakınına gelmeli.'}</span></div>
  </section>
}
