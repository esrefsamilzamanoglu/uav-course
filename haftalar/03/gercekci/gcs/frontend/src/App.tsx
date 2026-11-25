import { useState } from 'react'
import { CircleAlert, X } from 'lucide-react'
import { useGcs } from './api'
import type { MissionId, ViewId } from './types'
import { AppHeader, Sidebar } from './components/AppShell'
import { SceneMap } from './components/SceneMap'
import { VideoDeck } from './components/VideoDeck'
import { CodePanel } from './components/CodePanel'
import { MissionPanel } from './components/MissionPanel'
import { PayloadControls } from './components/PayloadControls'
import { TelemetryStrip } from './components/TelemetryStrip'
import { EventLog } from './components/EventLog'
import { SystemView } from './components/SystemView'

export default function App() {
  const { state, serverAvailable, error, pending, notification, send, clearNotification } = useGcs()
  const [view, setView] = useState<ViewId>('mission')
  const [selected, setSelected] = useState<MissionId>('G2')
  const activeMission = state.mission.status === 'running' || state.mission.status === 'paused'
  const selectedMission = activeMission && state.mission.id ? state.mission.id : selected
  const controls = { state, pending, send }
  const missionControls = { ...controls, selected: selectedMission, setSelected, openCode: () => setView('code') }
  return <div className="app-shell">
    <AppHeader {...controls} serverAvailable={serverAvailable} />
    <Sidebar view={view} setView={setView} connected={state.connected} />
    <main className={`workspace view-${view}`}>
      {view === 'mission' ? <><div className="left-stack"><SceneMap state={state} /><TelemetryStrip state={state} /><EventLog events={state.events} /></div><div className="inspector"><VideoDeck {...controls} /><MissionPanel {...missionControls} /><PayloadControls {...controls} /></div></> : null}
      {view === 'map' ? <div className="map-workspace"><SceneMap state={state} expanded /><TelemetryStrip state={state} /></div> : null}
      {view === 'camera' ? <><div className="camera-workspace"><VideoDeck {...controls} expanded /><TelemetryStrip state={state} /><EventLog events={state.events} /></div><div className="inspector"><MissionPanel {...missionControls} /><PayloadControls {...controls} /></div></> : null}
      {view === 'code' ? <div className="teaching-workspace"><div className="teaching-overview"><div className="teaching-map"><SceneMap state={state} /></div><VideoDeck {...controls} expanded /></div><CodePanel state={state} selected={selectedMission} /></div> : null}
      {view === 'logs' ? <div className="full-workspace"><EventLog events={state.events} expanded /></div> : null}
      {view === 'system' ? <div className="full-workspace"><SystemView state={state} serverAvailable={serverAvailable} /></div> : null}
    </main>
    {error ? <div className="connection-banner" role="status"><CircleAlert size={15} />{error}</div> : null}
    {notification ? <div className="command-notification" role="status"><span>{notification}</span><button aria-label="Bildirimi kapat" onClick={clearNotification}><X size={17} /></button></div> : null}
  </div>
}
