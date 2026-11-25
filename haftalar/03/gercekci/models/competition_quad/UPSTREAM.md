# Upstream flight model

The rotor joints, IMU, native collision geometry, LiftDrag systems, actuator
controls and coordinate transforms are derived from ArduPilot's Gazebo Iris
model, via this repository's already working week-2 world.

Source: https://github.com/ArduPilot/ardupilot_gazebo

License: LGPL-3.0; preserved in UPSTREAM-LICENSE.txt.

The white canopy, camera housing, motor decorations, double cargo suspension,
gripper links, and associated generated geometry are authored by
`../../world/build_world.py`. They are added to the native model, not substituted
for its functioning motor/IMU links.
