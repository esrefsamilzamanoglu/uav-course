import { memo, useEffect, useRef, useState } from 'react'
import { ChevronDown, Crosshair, Expand, Hand, Home, Layers, MapPin, Minus, MousePointer2, Navigation, Plus, Route } from 'lucide-react'
import type { Bounds, GcsState, SceneObject, Target, Vector } from '../types'
import { eventTime, number } from '../format'

const DEFAULT_BOUNDS: Bounds = { east_min: -190, east_max: 190, north_min: -190, north_max: 190 }
const objectColor = (value: SceneObject['color'], fallback: string) => Array.isArray(value) ? `rgb(${value.slice(0, 3).map(x => Math.round(x * 255)).join(',')})` : value ?? fallback
interface VisionMarker { kind: string; color?: string; point: Vector; current: boolean; confirmed: boolean; observations: number | null; lastSeen?: number | string; confidence?: number | null }
const validPoint = (value: Vector | undefined): value is Vector => Array.isArray(value) && value.length >= 2 && Number.isFinite(value[0]) && Number.isFinite(value[1])
function observedMarkers(state: GcsState): VisionMarker[] {
  if (!state.connected) return []
  const markers = new Map<string, VisionMarker>()
  for (const detection of state.camera.available ? state.detections : []) {
    if (validPoint(detection.position_enu)) markers.set(detection.kind, { kind: detection.kind, color: detection.color, point: detection.position_enu, current: true, confirmed: false, observations: 1, confidence: detection.confidence })
  }
  for (const detection of state.confirmed_detections ?? []) {
    if (!validPoint(detection.position_enu)) continue
    const current = markers.get(detection.kind)
    markers.set(detection.kind, { kind: detection.kind, color: detection.color ?? current?.color, point: detection.position_enu, current: !!current, confirmed: true, observations: detection.observations ?? null, lastSeen: detection.last_seen, confidence: detection.confidence ?? current?.confidence })
  }
  return [...markers.values()]
}
const visionName = (marker: VisionMarker) => `${marker.color === 'red' || marker.kind.includes('red') ? 'Kırmızı' : 'Mavi'} ${marker.kind.includes('payload') ? 'yük' : 'hedef'}`

function ObjectShape({ object, x, y, scale }: { object: SceneObject; x: number; y: number; scale: number }) {
  const type = object.type.toLowerCase()
  const size = object.size ?? [3, 3]
  const width = Math.max(1.2, (size[0] ?? 3) * scale)
  const height = Math.max(1.2, (size[1] ?? size[0] ?? 3) * scale)
  const rotation = -(object.yaw ?? 0) * 180 / Math.PI
  if (type.includes('tree') || type.includes('bush') || type.includes('cypress')) return <g transform={`translate(${x},${y})`}><ellipse cx="2" cy="4" rx={width / 2 + 2} ry={height / 2 + 2} fill="#1e3e2e" opacity=".17" /><circle r={Math.max(3, width / 2)} fill={objectColor(object.color, '#446d43')} /><circle cx={-width / 8} cy={-width / 8} r={Math.max(2, width / 3)} fill="#618356" opacity=".6" /></g>
  if (type.includes('road') || type.includes('path') || type.includes('parking')) return <g transform={`translate(${x},${y}) rotate(${rotation})`}><rect x={-width / 2} y={-height / 2} width={width} height={height} fill={objectColor(object.color, '#8c9591')} /><path d={`M ${-width / 2} 0 H ${width / 2}`} stroke="#d8d9cb" strokeWidth=".7" strokeDasharray="4 5" opacity=".65" /></g>
  if (type.includes('building') || type.includes('house') || type.includes('hangar')) return <g transform={`translate(${x},${y}) rotate(${rotation})`}><rect x={-width / 2 + 3} y={-height / 2 + 4} width={width} height={height} fill="#3d493e" opacity=".2" /><rect x={-width / 2} y={-height / 2} width={width} height={height} fill={objectColor(object.color, '#9b7964')} stroke="#e4ded2" strokeWidth="1" /><path d={`M ${-width / 2} 0 H ${width / 2}`} stroke="#6c574a" strokeWidth="1" /></g>
  return <rect transform={`translate(${x},${y}) rotate(${rotation})`} x={-width / 2} y={-height / 2} width={width} height={height} rx={type.includes('car') || type.includes('vehicle') ? 1.4 : 0} fill={objectColor(object.color, '#a9b0a3')} stroke="#435847" strokeWidth=".5" opacity=".9" />
}

const StaticObjects = memo(function StaticObjects({ objects, bounds }: { objects: SceneObject[]; bounds: Bounds }) {
  const scale = 1000 / (bounds.east_max - bounds.east_min)
  return <g aria-hidden="true">{objects.map((object, index) => <ObjectShape key={object.name ?? index} object={object} x={(object.position_enu[0] - bounds.east_min) * scale} y={(bounds.north_max - object.position_enu[1]) * 1000 / (bounds.north_max - bounds.north_min)} scale={scale} />)}</g>
})

export function SceneMap({ state, expanded = false }: { state: GcsState; expanded?: boolean }) {
  const container = useRef<HTMLDivElement>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [tool, setTool] = useState<'select' | 'pan'>('select')
  const [showRoute, setShowRoute] = useState(true)
  const [showLegend, setShowLegend] = useState(true)
  const [selectedTarget, setSelectedTarget] = useState<Target | null>(null)
  const [selectedVisionKind, setSelectedVisionKind] = useState<string | null>(null)
  const [showPosition, setShowPosition] = useState(false)
  const [imageFailed, setImageFailed] = useState(false)
  const [imageReady, setImageReady] = useState(false)
  const [viewport, setViewport] = useState({ width: 900, height: 600 })
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null)
  const overviewTick = Math.floor(Date.now() / 4000)
  useEffect(() => { setImageFailed(false) }, [overviewTick, state.simulation.running])
  useEffect(() => { if (!state.simulation.running) setImageReady(false) }, [state.simulation.running])
  useEffect(() => {
    if (!container.current) return
    const observer = new ResizeObserver(entries => { const rect = entries[0].contentRect; setViewport({ width: rect.width, height: rect.height }) })
    observer.observe(container.current)
    return () => observer.disconnect()
  }, [])
  const scene = state.scene
  const bounds = scene.view_bounds ?? DEFAULT_BOUNDS
  const xy = (p: number[]) => [(p[0] - bounds.east_min) * 1000 / (bounds.east_max - bounds.east_min), (bounds.north_max - p[1]) * 1000 / (bounds.north_max - bounds.north_min)]
  const points = (path: number[][]) => path.map(p => xy(p).join(',')).join(' ')
  const route = scene.route ?? scene.planned_route ?? []
  const trail = state.trail ?? []
  const home = scene.home_enu
  const position = state.connected ? state.vehicle.position_enu : null
  const heading = state.vehicle.heading_deg ?? state.vehicle.attitude_deg?.[2] ?? 0
  const latitude = state.connected ? state.vehicle.latitude : null
  const longitude = state.connected ? state.vehicle.longitude : null
  const pixelsPerMetre = Math.max(viewport.width, viewport.height) / (bounds.east_max - bounds.east_min) * zoom
  const scaleDistance = [10, 20, 50, 100, 200].filter(value => value * pixelsPerMetre <= 180).at(-1) ?? 10
  const scaleWidth = scaleDistance * pixelsPerMetre
  const vision = observedMarkers(state)
  const selectedVision = vision.find(marker => marker.kind === selectedVisionKind)
  const pixelsPerSvgUnit = Math.max(viewport.width, viewport.height) / 1000 * zoom
  const hasScene = !!home || (scene.objects?.length ?? 0) > 0
  const fit = () => { setZoom(.8); setPan({ x: 0, y: 0 }) }
  const targetName = (t: Target) => t.color === 'red' ? 'Kırmızı üçgen' : 'Mavi altıgen'
  const fullscreen = () => { if (document.fullscreenElement) void document.exitFullscreen(); else void container.current?.requestFullscreen() }
  const objectKey = JSON.stringify(scene.objects ?? [])
  const objects = useRef({ key: '', data: [] as SceneObject[] })
  if (objects.current.key !== objectKey) objects.current = { key: objectKey, data: scene.objects ?? [] }
  return <section ref={container} className={`scene-map ${expanded ? 'expanded' : ''}`} aria-label="Yerel ENU saha haritası">
    <svg className={`scene-canvas ${tool === 'pan' ? 'can-pan' : ''}`} viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" onPointerDown={event => { if (tool === 'pan') { event.currentTarget.setPointerCapture(event.pointerId); drag.current = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y } } }} onPointerMove={event => { if (!drag.current) return; const rect = event.currentTarget.getBoundingClientRect(); const scale = 1000 / Math.max(rect.width, rect.height); setPan({ x: drag.current.panX + (event.clientX - drag.current.x) * scale, y: drag.current.panY + (event.clientY - drag.current.y) * scale }) }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}>
      <defs><pattern id="map-grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M 50 0 H 0 V 50" fill="none" stroke="#c7d4c0" strokeWidth=".5" opacity=".23" /></pattern><pattern id="grass" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#839574" /><path d="m5 7 1-2m17 8 2 1m-12 13 1-2m18 7 1-2m-29 3 2-1m25-21 1-3" stroke="#a6af8e" strokeWidth=".7" opacity=".4" /></pattern><filter id="map-shadow"><feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity=".25" /></filter></defs>
      <rect width="1000" height="1000" fill="url(#grass)" /><rect width="1000" height="1000" fill="url(#map-grid)" />
      <g transform={`translate(${500 + pan.x} ${500 + pan.y}) scale(${zoom}) translate(-500 -500)`}>
        {!imageReady || imageFailed ? <><StaticObjects objects={objects.current.data} bounds={bounds} />{scene.field_bounds ? (() => {
          const a = xy([scene.field_bounds.east_min, scene.field_bounds.north_max]); const b = xy([scene.field_bounds.east_max, scene.field_bounds.north_min]); return <rect x={a[0]} y={a[1]} width={b[0] - a[0]} height={b[1] - a[1]} fill="#6f8e5d" fillOpacity=".34" stroke="#d8e3ce" strokeWidth="2" />
        })() : null}</> : null}
        {state.simulation.running && !imageFailed ? <image href={`/api/map.jpg?frame=${overviewTick}`} width="1000" height="1000" preserveAspectRatio="none" onLoad={() => setImageReady(true)} onError={() => { setImageFailed(true); setImageReady(false) }} /> : null}
        {showRoute && route.length > 1 ? <polyline points={points(route)} fill="none" stroke="#3be3ce" strokeWidth="3" strokeDasharray="8 8" strokeLinecap="round" vectorEffect="non-scaling-stroke" /> : null}
        {trail.length > 1 ? <polyline points={points(trail)} fill="none" stroke="#f5fcf6" strokeWidth="3" strokeLinecap="round" opacity=".9" vectorEffect="non-scaling-stroke" /> : null}
        {(scene.pylons ?? []).map((pylon, i) => { const [x, y] = xy(pylon.position_enu); return <g key={i} transform={`translate(${x},${y})`} filter="url(#map-shadow)"><path d="m0-14 8 24h-16z" fill="#ffac26" stroke="#fff" strokeWidth="1.7" /><path d="M-11 11H11" stroke="#fff" strokeWidth="3" /><text x="16" y="5" className="pylon-label">{pylon.name ?? `P${i + 1}`}</text></g> })}
        {(scene.targets ?? []).map(target => {
          const vertices = target.vertices_enu ?? []
          const [x, y] = xy(target.center_enu)
          const color = target.color === 'red' ? '#ff5f6c' : '#4c8eff'
          const select = () => { setSelectedTarget(target); setSelectedVisionKind(null) }
          return <g key={target.id} className="map-target" role="button" tabIndex={0} aria-label={`${targetName(target)} konumunu incele`} onClick={select} onKeyDown={event => { if (event.key === 'Enter') select() }}><circle cx={x} cy={y} r="13" fill="transparent" />{vertices.length ? <polygon points={points(vertices)} stroke={color} strokeWidth="2.3" fill={color} fillOpacity=".48" vectorEffect="non-scaling-stroke" /> : <circle cx={x} cy={y} r="6" fill={color} stroke="#fff" />}<circle cx={x} cy={y} r="1.6" fill="#fff" /></g>
        })}
        {vision.map(marker => {
          const [x, y] = xy(marker.point)
          const radius = 9 / pixelsPerSvgUnit
          const color = marker.current ? '#51e3ca' : '#f2f5e9'
          const select = () => { setSelectedVisionKind(marker.kind); setSelectedTarget(null) }
          return <g key={marker.kind} className={`vision-marker ${marker.current ? 'current' : 'last-seen'}`} data-testid="vision-marker" data-kind={marker.kind} data-east={marker.point[0]} data-north={marker.point[1]} transform={`translate(${x},${y})`} role="button" tabIndex={0} aria-label={`${visionName(marker)} görüntü tespiti`} onClick={select} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select() } }}>
            <circle r={22 / pixelsPerSvgUnit} fill="transparent" />
            <circle r={radius + 2 / pixelsPerSvgUnit} fill="#11362c66" stroke="#163c32" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <circle r={radius} fill="none" stroke={color} strokeWidth="2" strokeDasharray={marker.current ? undefined : '3 3'} vectorEffect="non-scaling-stroke" />
            <path d={`M ${-5 / pixelsPerSvgUnit} 0 H ${5 / pixelsPerSvgUnit} M 0 ${-5 / pixelsPerSvgUnit} V ${5 / pixelsPerSvgUnit}`} stroke={color} strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
            {!marker.current ? <text x={14 / pixelsPerSvgUnit} y={3 / pixelsPerSvgUnit} fontSize={10 / pixelsPerSvgUnit} className="vision-last-label">Son tespit</text> : null}
          </g>
        })}
        {home ? (() => { const [x, y] = xy(home); return <g transform={`translate(${x},${y})`}><circle r="6.5" fill="white" stroke="#1b2629" strokeWidth="2" /><rect x="-15" y="-34" width="62" height="22" rx="4" fill="white" fillOpacity=".96" /><path d="m-8-23 5-5 5 5m-8-1v7h6v-7" stroke="#1a2729" strokeWidth="1.5" fill="none" /><text x="6" y="-19" className="home-label">HOME</text></g> })() : null}
        {(['red', 'blue'] as const).map(color => { const gripper = state.grippers[color]; const payloadPosition = gripper?.payload_position_enu ?? (gripper?.attached ? gripper.position_enu : null); if (!payloadPosition || !state.connected) return null; const [x, y] = xy(payloadPosition); return <rect key={color} x={x - 3} y={y - 3} width="6" height="6" rx="1" fill={color === 'red' ? '#f45b66' : '#5087f5'} stroke="white" strokeWidth="1" /> })}
        {position ? (() => { const [x, y] = xy(position); return <g transform={`translate(${x},${y}) rotate(${heading})`} filter="url(#map-shadow)"><circle r="18" fill="#1c9d89" opacity=".14" /><path d="M0-14 10 12 0 7-10 12z" fill="#f9ffff" stroke="#167f6e" strokeWidth="2.4" /></g> })() : null}
      </g>
    </svg>
    {!hasScene ? <div className="map-empty"><Crosshair size={35} strokeWidth={1.2} /><strong>Saha verisi bekleniyor</strong><span>Yerel görev sunucusu bağlandığında parkur görüntülenir.</span></div> : null}
    <div className="map-readout"><Navigation size={23} /><dl><div><dt>{latitude == null ? 'Doğu' : 'Enlem'}</dt><dd>{latitude == null ? position ? `${number(position[0], 2)} m` : '—' : `${number(Math.abs(latitude), 6)}° ${latitude < 0 ? 'S' : 'N'}`}</dd></div><div><dt>{longitude == null ? 'Kuzey' : 'Boylam'}</dt><dd>{longitude == null ? position ? `${number(position[1], 2)} m` : '—' : `${number(Math.abs(longitude), 6)}° ${longitude < 0 ? 'W' : 'E'}`}</dd></div><div><dt>Mod</dt><dd>{state.connected ? state.vehicle.mode ?? '—' : 'Bağlantı bekleniyor'}</dd></div></dl><button className="readout-expander" aria-label="Konum ayrıntılarını göster" aria-expanded={showPosition} onClick={() => setShowPosition(!showPosition)}><ChevronDown size={16} /></button></div>
    {showPosition ? <div className="map-position-detail"><strong>Yerel konum · ENU</strong><span>Doğu {number(position?.[0], 2)} m</span><span>Kuzey {number(position?.[1], 2)} m</span><span>Yukarı {number(position?.[2], 2)} m</span></div> : null}
    <div className="map-toolbar" role="group" aria-label="Harita araçları"><button className={tool === 'select' ? 'selected' : ''} aria-label="Haritada seç" title="Seç" onClick={() => setTool('select')}><MousePointer2 size={20} /></button><button className={tool === 'pan' ? 'selected' : ''} aria-label="Haritayı kaydır" title="Kaydır" onClick={() => setTool('pan')}><Hand size={20} /></button><button aria-label="Sahayı ortala" title="Sahayı ortala" onClick={fit}><MapPin size={21} /></button><button className={showRoute ? 'route-visible' : ''} aria-pressed={showRoute} aria-label="Planlanan rotayı göster veya gizle" title="Rota" onClick={() => setShowRoute(!showRoute)}><Route size={21} /></button><button aria-pressed={showLegend} aria-label="Harita açıklamasını göster veya gizle" title="Katman açıklamaları" onClick={() => setShowLegend(!showLegend)}><Layers size={21} /></button><button aria-label="Haritayı tam ekran aç" title="Tam ekran" onClick={fullscreen}><Expand size={20} /></button></div>
    <div className="map-north"><span>N</span><Navigation size={15} fill="currentColor" /></div>
    <div className="map-bottom-left"><div className="map-zoom"><button aria-label="Haritayı yakınlaştır" onClick={() => setZoom(z => Math.min(3, z + .2))}><Plus size={17} /></button><button aria-label="Haritayı uzaklaştır" onClick={() => setZoom(z => Math.max(.45, z - .2))}><Minus size={17} /></button></div><div className="map-scale" style={{ width: scaleWidth + 24 }}><div><span>0</span><span>{scaleDistance / 2} m</span><span>{scaleDistance} m</span></div><i /></div><span className="map-source">{imageReady && !imageFailed ? 'Gazebo · canlı saha görünümü' : 'Yerel saha planı · ENU'}</span></div>
    {showLegend ? <div className="map-legend"><div><i className="legend-route" /><span>Planlanan rota</span></div><div><i className="legend-trail" /><span>Uçuş izi (gerçek)</span></div><div><Navigation size={17} className="legend-vehicle" /><span>Araç (İHA)</span></div><div><i className="legend-pylon" /><span>Pilon (2 adet, 150 m)</span></div><div><i className="target-symbol hexagon" /><span>Mavi hedef alanı</span></div><div><i className="target-symbol triangle" /><span>Kırmızı hedef alanı</span></div><div><Crosshair size={16} className="legend-detection" /><span>Tespit (kamera)</span></div><div><Home size={16} /><span>HOME (başlangıç)</span></div></div> : null}
    {selectedTarget ? <div className="map-selection"><button aria-label="Hedef ayrıntısını kapat" onClick={() => setSelectedTarget(null)}>×</button><strong>{targetName(selectedTarget)}</strong><span>Doğu {number(selectedTarget.center_enu[0], 2)} m · Kuzey {number(selectedTarget.center_enu[1], 2)} m</span></div> : null}
    {selectedVision ? <div className="map-selection vision-selection" data-testid="vision-popup"><button aria-label="Tespit ayrıntısını kapat" onClick={() => setSelectedVisionKind(null)}>×</button><strong><Crosshair size={14} />{visionName(selectedVision)} · {selectedVision.current ? 'Tespit' : 'Son tespit'}</strong><span>Doğu {number(selectedVision.point[0], 2)} m · Kuzey {number(selectedVision.point[1], 2)} m</span><span>{selectedVision.observations == null ? 'Gözlem sayısı bekleniyor' : `${selectedVision.observations} gözlem`}{selectedVision.confidence == null ? '' : ` · Şekil uyumu %${number(selectedVision.confidence * 100, 0)}`}</span><small>{selectedVision.confirmed ? 'Doğrulanan görüntü konumu · medyan' : 'Kamera görüntüsünden ölçülen konum'}{selectedVision.lastSeen == null ? '' : ` · Son tespit ${eventTime(selectedVision.lastSeen)}`}</small></div> : null}
  </section>
}
