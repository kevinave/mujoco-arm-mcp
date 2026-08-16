"""Minimal robot-arm MCP server.

Exposes three tools to an agent: move_arm / get_state / reset.
There is deliberately **no inverse kinematics** — the agent can only set angles and read where the
tip ended up, so reaching a given coordinate is a search it has to run itself.

Two modes:
  - If the live viewer (viewer_server.py) is running, commands go to it over a socket and the arm
    moves in the window in real time, so you can watch while talking to the agent.
  - If not, the server falls back to its own MuJoCo instance (numbers only, no window) and works
    exactly the same from the agent's point of view.

Model, forward kinematics and the socket protocol all come from arm_common (single definition).
Run:  python arm_mcp.py   (stdio MCP server; normally launched by the agent, not by hand)
"""
import math
import os
import socket
import mujoco
from mcp.server.fastmcp import FastMCP

import arm_common   # shared: XML / fk / send_json / recv_json

# Local simulation, used when the viewer is not running
_model = mujoco.MjModel.from_xml_string(arm_common.XML)
_data = mujoco.MjData(_model)
mujoco.mj_forward(_model, _data)   # settle the initial pose

# Trajectory log: truncated on start, one line per move, replayable afterwards
_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trajectory.log")
open(_LOG, "w").close()

# Where the live viewer listens (must match viewer_server.py)
_VIEWER = (os.environ.get("ARM_VIEWER_HOST", "127.0.0.1"),
           int(os.environ.get("ARM_VIEWER_PORT", "8899")))

mcp = FastMCP("arm")


def _tip():
    """Tip position (x, z) in the local simulation."""
    p = _data.site("tip").xpos
    return round(float(p[0]), 3), round(float(p[2]), 3)


def _ask_viewer(payload):
    """Forward a command to the live viewer and return its state; None if it is not running."""
    try:
        s = socket.create_connection(_VIEWER, timeout=1.0)
        arm_common.send_json(s, payload)
        resp = arm_common.recv_json(s)
        s.close()
        return None if "error" in resp else resp
    except Exception:
        return None


@mcp.tool()
def move_arm(angle1_deg: float, angle2_deg: float) -> str:
    """Rotate both joints to the given angles and return the resulting tip position.

    angle1_deg: upper arm, in degrees (0 = straight up, positive tilts toward +x).
    angle2_deg: forearm, in degrees, relative to the upper arm.
    """
    with open(_LOG, "a") as f:
        f.write(f"{angle1_deg},{angle2_deg}\n")
    r = _ask_viewer({"cmd": "move", "angle1": angle1_deg, "angle2": angle2_deg})
    if r:   # the live window has it
        return (f"Moved (live window). Tip at x={r['x']}, z={r['z']} "
                f"(angles j1={angle1_deg}deg, j2={angle2_deg}deg)")
    # local computation
    _data.qpos[0] = math.radians(angle1_deg)
    _data.qpos[1] = math.radians(angle2_deg)
    mujoco.mj_forward(_model, _data)
    x, z = _tip()
    return f"Moved. Tip at x={x}, z={z} (angles j1={angle1_deg}deg, j2={angle2_deg}deg)"


@mcp.tool()
def get_state() -> str:
    """Read the current state without moving: both joint angles and the tip position."""
    r = _ask_viewer({"cmd": "get"})
    if r:
        return f"Angles j1={r['j1']}deg, j2={r['j2']}deg; tip at x={r['x']}, z={r['z']} (live window)"
    j1 = round(math.degrees(float(_data.qpos[0])), 1)
    j2 = round(math.degrees(float(_data.qpos[1])), 1)
    x, z = _tip()
    return f"Angles j1={j1}deg, j2={j2}deg; tip at x={x}, z={z}"


@mcp.tool()
def reset() -> str:
    """Return the arm to its initial pose (both joints at zero, pointing straight up)."""
    r = _ask_viewer({"cmd": "reset"})
    if r:
        return f"Reset (live window). Tip at x={r['x']}, z={r['z']}"
    mujoco.mj_resetData(_model, _data)
    mujoco.mj_forward(_model, _data)
    x, z = _tip()
    return f"Reset. Tip at x={x}, z={z}"


if __name__ == "__main__":
    mcp.run()   # stdio transport
