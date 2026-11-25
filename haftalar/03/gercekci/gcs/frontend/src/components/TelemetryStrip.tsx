import { Battery, Cpu, Gauge, Mountain, RadioTower, Waypoints } from 'lucide-react'
import type { GcsState } from '../types'
import { number } from '../format'

export function TelemetryStrip({ state }: { state: GcsState }) {
  const v = state.vehicle
  const grippers = [state.grippers.red, state.grippers.blue]
  const swingValues = grippers.filter(gripper => gripper?.attached).map(gripper => gripper?.swing_deg).filter((x): x is number => typeof x === 'number')
  const swing = swingValues.length ? Math.max(...swingValues.map(Math.abs)) : null
  const noAttachedLoad = grippers.every(gripper => gripper != null && !gripper.attached)
  const fixLabels: Record<number, string> = { 0: 'Yok', 1: 'Fix yok', 2: '2D', 3: '3D', 4: 'DGPS', 5: 'RTK F.', 6: 'RTK' }
  const gps = v.gps_fix == null ? '—' : `${typeof v.gps_fix === 'number' ? fixLabels[v.gps_fix] ?? `Fix ${v.gps_fix}` : v.gps_fix} (${v.satellites ?? '—'})`
  const entries = [
    { label: 'İrtifa', value: `${number(v.altitude_m)}${v.altitude_m == null ? '' : ' m'}`, Icon: Mountain },
    { label: 'Hız', value: `${number(v.speed_mps)}${v.speed_mps == null ? '' : ' m/s'}`, Icon: Gauge },
    { label: 'Batarya', value: `${number(v.battery_voltage)}${v.battery_voltage == null ? '' : ' V'}`, Icon: Battery },
    { label: 'GPS', value: gps, Icon: RadioTower, good: typeof v.gps_fix === 'number' && v.gps_fix >= 3 },
    { label: 'EKF', value: v.ekf_ok == null ? '—' : v.ekf_ok ? 'Sağlıklı' : 'Kontrol edin', Icon: Cpu, good: v.ekf_ok === true, warn: v.ekf_ok === false },
    { label: 'Yük salınımı', value: noAttachedLoad ? 'Yük yok' : `${number(swing)}${swing == null ? '' : '°'}`, Icon: Waypoints },
  ]
  return <section className={`telemetry-strip ${state.connected ? '' : 'telemetry-stale'}`} aria-label="Canlı sensör verileri">{entries.map(({ label, value, Icon, good, warn }) => <div className="telemetry-item" key={label}><Icon size={22} strokeWidth={1.65} /><div><span>{label}</span><strong className={`${good ? 'text-success' : ''} ${warn ? 'text-warning' : ''}`}>{state.connected ? value : '—'}</strong></div></div>)}</section>
}
