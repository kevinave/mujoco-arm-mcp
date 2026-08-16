# Running the demo

Three things to run, in increasing order of setup. Each one is also what produces the
corresponding screenshot in [`docs/images/`](images/).

Everything below assumes you are in the repository root and that `$PY` points at a Python
interpreter with `mujoco` and `mcp` installed:

```bash
cd /path/to/mujoco-arm-mcp
export PY=./.venv/bin/python          # or wherever your environment lives
```

On macOS the GUI must be started through `mjpython`, which ships with the `mujoco` package and
lives next to `python` in the same environment:

```bash
export MJPY="$(dirname $PY)/mjpython"
```

---

## 1 · Protocol check — no window needed

Confirms the server is a real MCP server: it handshakes, advertises its tools, and answers a remote
call.

```bash
$PY test_client.py
```

Expected output:

```
1. Handshake OK

2. Server exposes 3 tools:
     - move_arm: Rotate both joints to the given angles and return the resulting tip position.
     - get_state: Read the current state without moving: both joint angles and the tip position.
     - reset: Return the arm to its initial pose (both joints at zero, pointing straight up).

3. Remote call  move_arm(angle1_deg=45, angle2_deg=-30):
     -> Moved. Tip at x=..., z=...
```

> 📸 **`protocol-test.png`** — screenshot the terminal.

---

## 2 · The live window

**Terminal A** — start the viewer and leave it running:

```bash
$MJPY viewer_server.py
```

A MuJoCo window opens with the arm pointing straight up. That pose is not worth photographing, so
**Terminal B** — move it:

```bash
$PY test_client.py
```

The arm eases over to `j1 = 45°`, `j2 = −30°`. Drag inside the window first to frame the arm
reasonably.

> 📸 **`viewer.png`** — screenshot the window alone (`Cmd+Shift+4`, then `Space`, then click it).

---

## 3 · The agent, closing the loop

Leave the viewer from step 2 running. In **Terminal B**:

```bash
npm install
PYTHON=$PY node agent/arm_agent.mjs
```

The agent is told to reach two targets within a tolerance of `0.05`, at most four moves each. It
has no inverse kinematics and has not been told the link lengths, so it has to measure them first —
and every call prints as it happens while the arm moves in the window:

```
   1  get_state
   2  move_arm   j1=    0.0   j2=   90.0

[agent] The probe exposed the two link contributions directly: 0.60 and 0.40.

   3  move_arm   j1=  -68.1   j2=   76.2
   4  move_arm   j1=  -76.1   j2=   74.0

[agent] First target met.
```

> 🎥 **`agent-run.gif`** — screen-record this rather than screenshotting it. Capture the terminal and
> the MuJoCo window side by side, from before you press Enter until the final message appears.
>
> Most of a run is the model thinking, with nothing moving on screen, so convert by dropping the
> static frames first and only then speeding up — otherwise the pauses survive and the motion does
> not:
>
> ```bash
> ffmpeg -i recording.mov -filter_complex \
>   "[0:v]mpdecimate=hi=64*10:lo=64*4:frac=0.002,setpts=N/(20*TB),setpts=PTS/1.6[v]; \
>    [v]split=2[a][b];[a]crop=1590:1794:0:0[t];[b]crop=1210:1794:2090:0[s]; \
>    [t][s]hstack=2,scale=1200:-2:flags=lanczos,fps=15, \
>    tpad=stop_mode=clone:stop_duration=1.5[out]" -map "[out]" -y trimmed.mp4
>
> ffmpeg -i trimmed.mp4 -vf palettegen=stats_mode=diff -y palette.png
> ffmpeg -i trimmed.mp4 -i palette.png \
>   -lavfi "[0:v][1:v]paletteuse=dither=bayer:bayer_scale=3" -y agent-run.gif
> ```
>
> The two `crop` values cut the MuJoCo control panels out of the middle and restack the terminal
> next to the 3D view; adjust them to your own window layout. One 80-second recording came out as a
> 15-second, 1.8 MB GIF this way — the static frames were 72% of it.

This step needs a working `codex` login, since the SDK drives a real Codex thread.

Interactive equivalent, if you would rather type at it than run a script:

```bash
PYTHON=$PY ./chat.sh "Put the tip at x=0.3, z=0.7"
```

---

## 4 · Replay (optional)

Every `move_arm` call is appended to `trajectory.log`, so a finished run can be played back as one
continuous motion, pausing at each pose the agent tried:

```bash
$MJPY replay_viewer.py
```

Note that `arm_mcp.py` truncates the log on startup, so replay shows the most recent run only.

---

## Where the screenshots go

Drop the files in `docs/images/` using exactly these names — the README references them directly:

| File | From |
|:--|:--|
| `viewer.png` | step 2 |
| `agent-run.gif` | step 3 |
| `protocol-test.png` | step 1 |
