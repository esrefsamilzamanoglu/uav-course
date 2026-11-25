import { useState } from 'react'
import { PanelsTopLeft } from 'lucide-react'
import type { GcsState, SendCommand } from '../types'
import { CameraPanel } from './CameraPanel'
import { FollowCameraPanel } from './FollowCameraPanel'

export function VideoDeck({ state, pending, send, expanded = false }: { state: GcsState; pending: string | null; send: SendCommand; expanded?: boolean }) {
  const [view, setView] = useState<'both' | 'onboard' | 'follow'>('both')
  return <section className={`video-deck ${expanded ? 'expanded' : ''} video-${view}`} aria-label="Canlı uçuş görüntüleri">
    <div className="video-deck-toolbar"><span><PanelsTopLeft size={14} />Canlı görüntüler</span><div role="group" aria-label="Görüntü düzeni">{([{ id: 'both', label: 'Birlikte' }, { id: 'onboard', label: 'Araç' }, { id: 'follow', label: '3. kişi' }] as const).map(item => <button key={item.id} aria-pressed={view === item.id} className={view === item.id ? 'selected' : ''} onClick={() => setView(item.id)}>{item.label}</button>)}</div></div>
    <div className="video-deck-feeds">{view !== 'follow' ? <CameraPanel state={state} expanded={expanded} /> : null}{view !== 'onboard' ? <FollowCameraPanel state={state} pending={pending} send={send} /> : null}</div>
  </section>
}
