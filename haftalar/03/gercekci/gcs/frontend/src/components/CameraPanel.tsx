import { Box, Camera, ChevronDown, Crosshair, VideoOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { GcsState } from '../types'
import { number } from '../format'

export function CameraPanel({ state, expanded = false }: { state: GcsState; expanded?: boolean }) {
  const [imageError, setImageError] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const camera = state.camera
  useEffect(() => setImageError(false), [camera.available, camera.frame_id])
  const stale = typeof camera.age_s === 'number' && camera.age_s > 2
  const available = camera.available && !stale && !imageError
  const width = camera.width ?? 960
  const height = camera.height ?? 720
  const last = state.detections.at(-1)
  const payloadDetection = last?.kind.endsWith('_payload') ?? false
  const detectionLabel = `${last?.color === 'red' ? 'Kırmızı' : 'Mavi'} ${payloadDetection ? 'yük' : 'hedef'}`
  const confidenceLabel = payloadDetection ? 'Renk/boyut uyumu' : 'Şekil uyumu'
  const fallbackLabel = payloadDetection ? 'Renk + boyut doğrulandı' : 'Renk + şekil doğrulandı'
  const hfov = state.scene.camera?.hfov_rad
  return <section className={`panel camera-panel ${expanded ? 'expanded' : ''}`}>
    <div className="panel-heading"><h2><Camera size={21} />Canlı kamera</h2><button className="camera-source" aria-expanded={showInfo} aria-label="Kamera bilgisini göster" onClick={() => setShowInfo(!showInfo)}><span>Kamera:</span><strong>cam/0</strong><ChevronDown size={15} /></button></div>
    {showInfo ? <div className="camera-info"><strong>{camera.source ?? 'Gazebo RGB sensörü'}</strong><span>{camera.available ? `${width} × ${height}${hfov == null ? '' : ` · yatay ${number(hfov * 180 / Math.PI, 0)}°`} · kare yaşı ${number(camera.age_s, 2)} s` : 'Görüntü bekleniyor'}</span><span>{camera.confidence_description ?? 'Tespitler renk ve şekil kurallarına dayanır.'}</span></div> : null}
    <div className="camera-viewport" data-testid="onboard-camera">
      {available ? <><img src={`/api/camera.jpg?seq=${encodeURIComponent(String(camera.frame_id ?? 'current'))}`} alt="Gazebo üzerindeki aşağı bakan kameranın canlı görüntüsü" onError={() => setImageError(true)} /><svg className="detection-overlay" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" aria-label="Görüntü işleme tespitleri">{state.detections.map((d, i) => d.bbox?.length === 4 ? <g key={`${d.kind}-${i}`}><rect x={d.bbox[0]} y={d.bbox[1]} width={d.bbox[2]} height={d.bbox[3]} rx="2" fill="none" stroke={d.color === 'red' ? '#ff6069' : '#4be0d6'} strokeWidth="3" /><circle cx={d.bbox[0] + d.bbox[2] / 2} cy={d.bbox[1] + d.bbox[3] / 2} r="5" fill="none" stroke="#fff" strokeWidth="2" /></g> : null)}</svg>{last ? <div className="detection-label">{payloadDetection ? <Box size={22} color={last.color === 'red' ? '#ff6069' : '#4b8bff'} data-testid="payload-detection-icon" aria-hidden="true" /> : <span className={`target-symbol ${last.color === 'red' ? 'triangle' : 'hexagon'}`} />}<div><strong>Tespit: {detectionLabel}</strong><span>{typeof last.confidence === 'number' ? `${confidenceLabel}: %${number(last.confidence * 100, 0)}` : fallbackLabel}</span></div></div> : null}<div className="camera-live"><span />CANLI</div></> : <div className="camera-empty"><VideoOff size={34} strokeWidth={1.35} /><strong>Kamera bekleniyor</strong><span>{state.simulation.running ? 'Gazebo RGB sensöründen görüntü alınıyor…' : 'Simülasyonu başlattığınızda gerçek görüntü burada açılır.'}</span></div>}
    </div>
    {expanded ? <div className="camera-detail"><span><Crosshair size={16} />{state.detections.length} geçerli tespit</span><span>{camera.available ? `${width} × ${height} RGB` : 'Görüntü yok'}</span><span>Kare yaşı: {number(camera.age_s, 2)} s</span></div> : null}
  </section>
}
