import { useEffect, useState } from 'react'
import { Camera, VideoOff } from 'lucide-react'
import type { FollowMode, GcsState, SendCommand } from '../types'
import { number } from '../format'

const MODES: { id: FollowMode; label: string }[] = [{ id: 'chase', label: 'Takip' }, { id: 'orbit', label: 'Yörünge' }, { id: 'side', label: 'Yandan' }, { id: 'top', label: 'Üstten' }]

export function FollowCameraPanel({ state, pending, send }: { state: GcsState; pending: string | null; send: SendCommand }) {
  const camera = state.follow_camera
  const [imageError, setImageError] = useState(false)
  useEffect(() => setImageError(false), [camera?.available, camera?.frame_id])
  const stale = typeof camera?.age_s === 'number' && camera.age_s > 2
  const available = camera?.available && !stale && !imageError
  const requested = camera?.requested_mode
  return <section className="panel follow-panel">
    <div className="panel-heading"><h2><Camera size={19} />3. kişi görüntüsü</h2><span className="video-source-tag">Gazebo</span></div>
    <div className="camera-viewport follow-viewport" data-testid="follow-camera">
      {available ? <><img src={`/api/follow.jpg?seq=${encodeURIComponent(String(camera.frame_id ?? 'current'))}`} alt={`Gerçek Gazebo üçüncü kişi kamerası · ${MODES.find(m => m.id === camera.mode)?.label ?? 'takip'}`} onError={() => setImageError(true)} /><div className="camera-live"><span />CANLI</div><span className="follow-mode-label">{MODES.find(m => m.id === camera.mode)?.label ?? 'Mod bekleniyor'}</span></> : <div className="camera-empty"><VideoOff size={30} strokeWidth={1.4} /><strong>{stale ? 'Dış kamera güncel değil' : 'Dış kamera bekleniyor'}</strong><span>{stale ? `Son kare ${number(camera?.age_s, 1)} s önce alındı.` : 'Gazebo takip kamerasının gerçek görüntüsü burada açılır.'}</span></div>}
    </div>
    <div className="follow-mode-controls" role="group" aria-label="Üçüncü kişi kamera açısı">{MODES.map(mode => <button key={mode.id} className={camera?.mode === mode.id ? 'selected' : ''} aria-pressed={camera?.mode === mode.id} disabled={!state.simulation.running || pending !== null} onClick={() => { void send({ action: 'camera_follow', mode: mode.id }).catch(() => undefined) }}>{mode.label}</button>)}</div>
    {requested && requested !== camera?.mode ? <p className="follow-feedback">{MODES.find(m => m.id === requested)?.label} açısı istendi; gerçek kare geri bildirimi bekleniyor.</p> : null}
  </section>
}
