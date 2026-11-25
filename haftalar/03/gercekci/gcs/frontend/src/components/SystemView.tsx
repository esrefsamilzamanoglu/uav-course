import { Activity, Camera, Check, Cpu, HardDrive, Radio, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import type { GcsState } from '../types'
import { number } from '../format'
import '../system.css'

export function SystemView({ state, serverAvailable }: { state: GcsState; serverAvailable: boolean }) {
  const v = state.vehicle
  const plannerReady = serverAvailable && state.connected && state.simulation.running
  const values = [
    ['Uçuş modu', v.mode ?? '—'], ['ARM durumu', state.connected ? v.armed ? 'ARM' : 'DISARM' : '—'],
    ['EKF', v.ekf_ok == null ? '—' : v.ekf_ok ? 'Sağlıklı' : 'Kontrol edin'], ['Heartbeat yaşı', `${number(v.last_heartbeat_age_s, 2)} s`],
    ['Doğu / Kuzey / Yukarı', v.position_enu ? v.position_enu.map(x => number(x, 2)).join(' / ') + ' m' : '—'],
    ['Roll / Pitch / Yaw', v.attitude_deg ? v.attitude_deg.map(x => number(x, 1)).join(' / ') + '°' : '—'],
    ['Düşey hız', `${number(v.vertical_speed_mps)} m/s`], ['Batarya doluluğu', v.battery_percent == null ? '—' : `${number(v.battery_percent, 0)} %`],
  ]
  return <div className="system-view">
    <section className="panel system-status"><div className="panel-heading"><h2><Activity size={21} />Sistem durumu</h2></div>
      <div className="system-services">{[{ name: 'Yerel GCS sunucusu', ok: serverAvailable, Icon: HardDrive }, { name: 'ArduPilot / SITL', ok: state.connected, Icon: Radio }, { name: 'Gazebo simülasyonu', ok: state.simulation.running, Icon: Cpu }, { name: 'Gerçek RGB sensörü', ok: state.camera.available, Icon: Camera }].map(({ name, ok, Icon }) => <div className="service-row" key={name}><Icon size={21} /><strong>{name}</strong><span className={`service-status ${ok ? 'ready' : ''}`}>{ok ? <Check size={14} /> : <span className="status-dot" />}{ok ? 'Hazır' : 'Bekleniyor'}</span></div>)}</div>
    </section>
    <section className="panel planner-connection">
      <div className="panel-heading"><h2><Radio size={21} />Mission Planner</h2><span className={`service-status ${plannerReady ? 'ready' : ''}`}>{plannerReady ? 'Bağlantıya hazır' : 'Simülasyon bekleniyor'}</span></div>
      <dl className="system-readouts">
        <div><dt>Bağlantı türü</dt><dd>TCP</dd></div>
        <div><dt>Sunucu / IP</dt><dd>127.0.0.1</dd></div>
        <div><dt>Mission Planner portu</dt><dd>5762</dd></div>
        <div><dt>ROTA GCS portu</dt><dd>5760 · ayrı bağlantı</dd></div>
      </dl>
      <p className="planner-instructions">Mission Planner → TCP → CONNECT → 127.0.0.1 → 5762. ROTA açık kalabilir; G1, G2 ve G3 aynı uçuş üzerinden izlenir.</p>
      <p className="planner-instructions">Görevler Python’dan GUIDED komutlarıyla yürütülür; Mission Planner’ın AUTO görev listesi bu adımları göstermez. Görev sürerken uçuş komutlarını ROTA’dan verin.</p>
      <p className="planner-instructions">“Bağlantıya hazır” simülatörün durumudur. Mission Planner’ın bağlandığını kendi telemetri ekranından doğrulayın.</p>
    </section>
    <section className="panel"><div className="panel-heading"><h2><ShieldCheck size={21} />Araç ve sensörler</h2></div><dl className="system-readouts">{values.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
    <section className="panel"><div className="panel-heading"><h2><SlidersHorizontal size={21} />ArduPilot servo çıkışları</h2></div><dl className="system-readouts">{Object.entries(v.servo_pwm ?? {}).length ? Object.entries(v.servo_pwm ?? {}).map(([channel, pwm]) => <div key={channel}><dt>SERVO{channel}</dt><dd>{number(pwm, 0)} µs</dd></div>) : <div className="empty-system">Servo telemetrisi bekleniyor.</div>}</dl></section>
  </div>
}
