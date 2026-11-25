export type Vector = [number, number, number]
export type MissionId = 'G1' | 'G2' | 'G3'
export type ViewId = 'mission' | 'map' | 'camera' | 'code' | 'logs' | 'system'
export type FollowMode = 'chase' | 'orbit' | 'side' | 'top'
export interface Bounds { east_min: number; east_max: number; north_min: number; north_max: number }
export interface SceneObject { type: string; name?: string; position_enu: Vector; size?: number[]; color?: string | number[]; yaw?: number }
export interface Target { id: string; kind?: string; color: string; center_enu: Vector; vertices_enu?: number[][]; side_m?: number }
export interface Scene {
  home_enu?: Vector
  field_bounds?: Bounds
  view_bounds?: Bounds
  pylons?: { name?: string; position_enu: Vector }[]
  targets?: Target[]
  objects?: SceneObject[]
  route?: Vector[]
  planned_route?: Vector[]
  camera?: { hfov_rad?: number; image_px?: number[] }
}
export interface GcsEvent { timestamp?: number | string; time?: string; level?: string; message: string; id?: number | string }
export interface Detection { kind: string; color?: string; confidence?: number | null; bbox?: number[]; position_enu?: Vector; u?: number; v?: number }
export interface ConfirmedDetection extends Detection { observations?: number; last_seen?: number | string }
export interface Gripper { attached: boolean; pwm?: number | null; swing_deg?: number | null; payload_mass_kg?: number | null; mass_kg?: number | null; reject_reason?: string | null; position_enu?: Vector; payload_position_enu?: Vector; payload_id?: string | null; state?: string; command_source?: string }
export interface MissionStep { id: string; label: string; status?: string }
export interface GcsState {
  connected: boolean
  simulation: { running: boolean; status?: string; run_path?: string }
  vehicle: {
    armed?: boolean; mode?: string | null; position_enu?: Vector | null; velocity_enu?: Vector | null; attitude_deg?: Vector | null
    altitude_m?: number | null; speed_mps?: number | null; vertical_speed_mps?: number | null; heading_deg?: number | null
    latitude?: number | null; longitude?: number | null; battery_percent?: number | null; battery_voltage?: number | null
    gps_fix?: number | string | null; satellites?: number | null; ekf_ok?: boolean | null; servo_pwm?: Record<string, number | null>; last_heartbeat_age_s?: number | null
  }
  mission: { id?: MissionId | null; phase?: string; phase_label?: string; step_index?: number; steps?: MissionStep[]; elapsed_s?: number | null; paused?: boolean; status?: string }
  camera: { available: boolean; frame_id?: number | string; width?: number; height?: number; age_s?: number | null; source?: string; confidence_description?: string }
  follow_camera?: { available: boolean; frame_id?: number | string; width?: number; height?: number; age_s?: number | null; source?: string; mode?: FollowMode; requested_mode?: FollowMode }
  detections: Detection[]
  confirmed_detections?: ConfirmedDetection[]
  grippers: { red?: Gripper; blue?: Gripper }
  scene: Scene
  events: GcsEvent[]
  trail?: Vector[]
  telemetry_history?: { timestamp: number; altitude_m?: number; speed_mps?: number; swing_deg?: number }[]
}
export interface Command { action: string; mission?: MissionId; channel?: number; pwm?: number; altitude_m?: number; mode?: FollowMode }
export type SendCommand = (command: Command) => Promise<void>

export interface CodeFunction { name: string; line: number; end_line: number; explanation?: string }
export interface CodeFile { file: string; sha256: string; line_count: number; trace_enabled: boolean; functions: CodeFunction[]; note?: string }
export interface CodeSource { file: string; sha256: string; lines: string[]; functions: CodeFunction[]; trace_enabled: boolean; note?: string; source_changed?: boolean; disk_sha256?: string }
export type TraceLane = 'mission' | 'vision'
export interface TraceFrame { file: string; function: string; line: number; lineno?: number }
export interface TraceEvent extends TraceFrame {
  seq: number; event: 'line' | 'call' | 'return' | 'exception'; wall_time?: number; elapsed_s?: number
  lane: TraceLane; phase?: string; exception_type?: string
  context?: { mission?: string; phase?: string; phase_label?: string; status?: string; step_index?: number; goal_enu?: Vector; [key: string]: unknown }
  stack?: TraceFrame[]; age_s?: number; wait?: { kind?: string; description?: string; elapsed_s?: number; timeout_s?: number; distance_m?: number; altitude_error_m?: number; speed_mps?: number; goal_enu?: Vector } | null
}
export interface CodeTrace {
  run_id?: string | null; mission_id?: MissionId | null; status?: string; active?: boolean; seq: number; oldest_seq?: number; dropped?: number
  events: TraceEvent[]; current?: TraceEvent | null; lanes?: { mission?: TraceEvent | null; vision?: TraceEvent | null }
  source_sha256?: Record<string, string>; sample_interval_ms?: number; skipped?: number
}

export const EMPTY_STATE: GcsState = {
  connected: false,
  simulation: { running: false, status: 'idle' },
  vehicle: {}, mission: { status: 'idle', phase: 'idle', phase_label: 'Görev bekleniyor', steps: [] },
  camera: { available: false }, detections: [], confirmed_detections: [], grippers: {}, scene: {}, events: [], trail: [],
}
