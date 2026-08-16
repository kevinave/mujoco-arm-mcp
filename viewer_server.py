"""Live viewer — the window half of the two-process design.

It owns a MuJoCo window (macOS requires the GUI on the main thread, so the viewer has to be its
own process) and listens on a socket in the background: whenever the MCP server receives a move
from the agent it forwards the angles here, and the arm eases toward them in real time.

Model, forward kinematics and the socket protocol come from arm_common (single definition).
Run (with window):  mjpython viewer_server.py
Self-test (none):   python  viewer_server.py --headless
Quit: close the window, or Ctrl-C.
"""
import sys
import socket
import threading
import time
import math

import arm_common   # shared: XML / fk / send_json / recv_json

HOST, PORT = "127.0.0.1", 8899

# Current target angles in degrees; written by the socket thread, eased toward by the main loop
_target = {"j1": 0.0, "j2": 0.0}
_lock = threading.Lock()


def _handle(conn):
    """Handle one command from the MCP server: move / reset / get."""
    try:
        msg = arm_common.recv_json(conn)
        cmd = msg.get("cmd")
        if cmd == "move":
            with _lock:
                _target["j1"] = float(msg["angle1"])
                _target["j2"] = float(msg["angle2"])
        elif cmd == "reset":
            with _lock:
                _target["j1"] = _target["j2"] = 0.0
        elif cmd == "get":
            pass                       # read-only: report state without moving
        else:
            raise ValueError(f"unknown command {cmd!r}")
        with _lock:
            j1, j2 = _target["j1"], _target["j2"]
        x, z = arm_common.fk(j1, j2)
        arm_common.send_json(conn, {"j1": j1, "j2": j2, "x": x, "z": z})
    except Exception as e:
        try:
            arm_common.send_json(conn, {"error": str(e)})
        except Exception:
            pass
    finally:
        conn.close()


def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    print(f"[viewer] listening on {HOST}:{PORT}, waiting for MCP commands...")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


def main():
    # Start the socket listener in the background (daemon thread)
    threading.Thread(target=_serve, daemon=True).start()

    if "--headless" in sys.argv:
        print("[viewer] headless self-test: socket only, no window. Ctrl-C to quit.")
        while True:
            time.sleep(1)

    # GUI mode: the viewer owns the main thread
    import mujoco
    import mujoco.viewer

    model = mujoco.MjModel.from_xml_string(arm_common.XML)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    print("[viewer] Window open. Drive the agent from another terminal and watch the arm move. Close the window to quit.")
    with mujoco.viewer.launch_passive(model, data) as v:
        while v.is_running():
            with _lock:
                t1 = math.radians(_target["j1"])
                t2 = math.radians(_target["j2"])
            # Ease toward the target: 8% of the remaining distance per frame
            data.qpos[0] += (t1 - data.qpos[0]) * 0.08
            data.qpos[1] += (t2 - data.qpos[1]) * 0.08
            mujoco.mj_forward(model, data)
            v.sync()
            time.sleep(0.01)


if __name__ == "__main__":
    main()
