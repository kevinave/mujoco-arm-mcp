"""Shared foundation for the arm demo: model definition, forward kinematics, socket helpers.

Everything else (arm_mcp / viewer_server / replay_viewer) imports from here, so the robot has
exactly one definition. The XML used to be duplicated in three files.
"""
import json
import math

# ── Geometry: base height, upper arm length, forearm length ──
BASE_Z, L1, L2 = 0.1, 0.5, 0.4

# ── The robot: single source of truth ──
XML = """
<mujoco>
  <worldbody>
    <geom type="plane" size="2 2 0.1" rgba="0.85 0.87 0.8 1"/>
    <light pos="0 0 3" dir="0 0 -1"/>
    <body name="link1" pos="0 0 0.1">
      <joint name="j1" type="hinge" axis="0 1 0"/>
      <geom type="capsule" fromto="0 0 0 0 0 0.5" size="0.05" rgba="0.2 0.6 0.9 1"/>
      <body name="link2" pos="0 0 0.5">
        <joint name="j2" type="hinge" axis="0 1 0"/>
        <geom type="capsule" fromto="0 0 0 0 0 0.4" size="0.04" rgba="0.95 0.55 0.2 1"/>
        <site name="tip" pos="0 0 0.4" size="0.03" rgba="1 0.2 0.2 1"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


def fk(j1_deg, j2_deg):
    """Forward kinematics: two joint angles (degrees) -> tip position (x, z).

    Analytic solution; agrees with MuJoCo's own numbers.
    """
    a1, a2 = math.radians(j1_deg), math.radians(j2_deg)
    x1 = L1 * math.sin(a1)
    z1 = BASE_Z + L1 * math.cos(a1)
    x = x1 + L2 * math.sin(a1 + a2)
    z = z1 + L2 * math.cos(a1 + a2)
    return round(x, 3), round(z, 3)


# ── Socket protocol: newline-framed JSON ──
# A newline marks the end of one message, and the reader keeps reading until it sees one.
# TCP does not preserve message boundaries, so "one recv returns one message" is a bug
# that only surfaces under load.
def send_json(sock, obj):
    """Send one object as a single JSON message, newline-framed."""
    sock.sendall((json.dumps(obj) + "\n").encode())


def recv_json(sock):
    """Read exactly one JSON message (up to the newline) and parse it."""
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:              # peer closed the connection
            break
        buf += chunk
    return json.loads(buf.decode().strip())
