"""Replay viewer: reads the trajectory the agent produced (trajectory.log) and plays the
path it searched back as one continuous motion in a MuJoCo window.
Run:  mjpython replay_viewer.py    Close the window to quit."""
import os, time, math
import mujoco, mujoco.viewer

import arm_common   # shared: the robot XML (single definition)

model = mujoco.MjModel.from_xml_string(arm_common.XML)
data = mujoco.MjData(model)

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trajectory.log")
pts = [(0.0, 0.0)]   # start from the initial pose
with open(LOG) as f:
    for line in f:
        line = line.strip()
        if line:
            a1, a2 = (float(v) for v in line.split(","))
            pts.append((math.radians(a1), math.radians(a2)))

print(f"Replaying {len(pts)-1} moves. Red dot = tip. Close the window to quit.")
with mujoco.viewer.launch_passive(model, data) as v:
    for i in range(len(pts) - 1):
        (s1, s2), (e1, e2) = pts[i], pts[i + 1]
        for k in range(61):                      # 60 interpolation steps per segment
            t = k / 60
            data.qpos[0] = s1 + (e1 - s1) * t
            data.qpos[1] = s2 + (e2 - s2) * t
            mujoco.mj_forward(model, data)
            v.sync()
            time.sleep(0.012)
            if not v.is_running(): break
        time.sleep(0.5)                          # pause at each pose the agent tried
        if not v.is_running(): break
    while v.is_running():                        # hold at the final pose until you close it
        v.sync(); time.sleep(0.1)
