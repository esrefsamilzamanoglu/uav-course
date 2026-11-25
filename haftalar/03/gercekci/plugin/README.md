# Physical payload plugin and actual Gazebo camera bridge

`PayloadMechanics.cc` runs inside Gazebo Jetty 10.5.0. It never sets the UAV or payload pose or velocity. The payload is attached by a Gazebo `DetachableJoint` between its physical link and the gripper end link. Removing this constraint releases the payload into gravity, collisions and friction. The carrier's two orthogonal revolute tether joints allow the attached mass to swing and transfer forces to the airframe.

The launcher compiles the plugin and bridge from source with `build.ps1`. It first uses the repository's `windows/.pixi/envs/default` installation, then the teacher workstation's `~/gz-ws` fallback when present. Outputs are `.local/build/PayloadMechanics.dll` and `.local/build/realistic_bridge.exe`.

## Servo control

The live chain is:

`GCS MAV_CMD_DO_SET_SERVO → ArduPilot SERVO9/10 → SITL JSON actuator output → ArduPilotPlugin COMMAND control → /uav/servo/9 or /10 → PayloadMechanics`.

Native controls use zero-based channels 8/9, `servo_min=1000`, `servo_max=2000`, `multiplier=1000`, `offset=1`, so the transmitted Gazebo `Double` is the actual 1000–2000 μs PWM. Backend telemetry forwarding must stay disabled in this mode to avoid a second, delayed command source.

- PWM ≥1700: close and try to grasp.
- PWM ≤1300: open and remove the attachment constraint.
- Intermediate PWM: hold the current attachment state.
- Attachment requires gripper distance ≤0.16 m from the payload's upper contact reference, relative speed ≤0.60 m/s, valid physical link velocities, and a closed jaw when that actuated joint exists.
- Both physical payloads are eligible; the mechanism does not choose a load based on target coordinates or a hardcoded colour assignment.
- `initial_closed` models the ground crew's preloaded mechanical clamp. Telemetry calls it `mechanical preload default` until an actual servo topic message is received.

The attachment is a proximity latch with a rigid local constraint. Finger movement and payload/cable dynamics are physical, but detailed deformable foam, grip-force closure and cable elasticity are not modelled.

## Bridge contract

```text
realistic_bridge --output-dir RUNTIME/bridge --udp-port 9109
```

The bridge inherits the simulation's `GZ_PARTITION` and native library `PATH`. It subscribes to actual camera sensors `/course/realistic/camera/image`, `/course/realistic/overview/image` and `/course/realistic/follow/image`, actual onboard camera pose `/uav/camera/pose`, external camera feedback `/uav/follow/state`, and physical state `/uav/gripper/state`.

| File | Contents |
| --- | --- |
| `latest.ppm` | Atomic P6 RGB frame from the 960×720 / 8 Hz onboard Gazebo sensor |
| `camera.json` | Frame ID/time, dimensions, nearest camera position and quaternion, pose time mismatch |
| `overview.ppm`, `overview.json` | Static observer camera for the GCS map background; never used as onboard perception |
| `follow.ppm`, `follow.json` | Actual 640×360 / 8 Hz spectator sensor; native mode, eye and target matched to the frame within 0.1 s |
| `follow-control.json` | Mode request input, restricted to `chase`, `orbit`, `side`, `top` |
| `follow-state.json` | Latest native spectator camera mode and actual pose feedback |
| `state.json` | Latest physical vehicle, gripper and payload positions, masses, velocities, attachment status, PWM and swing |
| `mechanics.jsonl` | Timestamped physical state evidence |

Atomic replacement may briefly make a Windows reader return `PermissionError`; polling consumers should retry on `OSError`. No image is synthesised by this bridge. Camera pose follows the actual base-link orientation and the physical sensor offset, including roll/pitch/yaw.

The bridge's localhost UDP `{ "servo": 9, "pwm": 1100 }` input is only for isolated physics fixtures. It publishes the same transport message, but does not constitute ArduPilot integration evidence.

## External follow camera

The dedicated `follow_observer` model has no aircraft or payload mass. Its sensor looks along local +X. `FollowCamera.hh` computes a smoothed eye/target pose from the actual base-link world pose and simulation time; yaw follows the shortest wrapped angle. Camera motion is confined to `follow_observer`; the fixed `map_observer`, onboard sensor and aircraft/payload poses are not moved by this feature.

The Python `FollowCamera` helper atomically writes the requested mode. The bridge publishes that allowlisted value on `/uav/follow/mode`; the native system acknowledges its applied mode on `/uav/follow/state`. `follow.json` reports the mode associated with the actual rendered frame. Requested and acknowledged modes remain separate until a matching new frame arrives. The helper rejects stale frames and mismatched image/metadata pairs.

The configured 8 Hz is simulation time. On the tested workstation the live stream measured about 3.6 wall-clock frames/s with a real-time factor near 0.46; hardware and scene load change this value. The native C++ geometry test checks optical aiming, wrapped angles, mode validation, smoothing, orbit progress and frozen simulation time.

## Physical acceptance test

Run `tests/physics/run_physics.py` with the course Python environment. It launches an isolated Gazebo partition, anchors a carrier, excites a real 0.30 kg pendulum with a short force pulse, releases it with PWM, and checks rejection when the payload is too far away. It uses no SITL ports and no pose/velocity injection. Results and the real state trace are retained in `tests/physics/evidence/`.

The current native DART backend supports the detachable joint itself, but not the optional `SetFixedJointWeldChildToParentFeature`; the plugin deliberately does not request that optional extension.

Primary API reference: [Gazebo DetachableJointInfo](https://gazebosim.org/api/sim/10/structgz_1_1sim_1_1components_1_1DetachableJointInfo.html). The source also follows the installed Gazebo headers and the official ArduPilot Gazebo plugin's COMMAND actuator implementation.
