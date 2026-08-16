"""Protocol-level test: connect to arm_mcp over stdio as a real MCP client —
handshake, list tools, call one remotely. Passing proves it is a genuine MCP
server that any agent can attach to. Each answer is asserted, so a regression
exits non-zero instead of printing something quietly wrong.

Run:  python test_client.py
"""
import asyncio
import os
import re
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import arm_common

HERE = Path(__file__).resolve().parent

# Launch the server as a subprocess — exactly how an agent would start it
server = StdioServerParameters(
    command=sys.executable,
    args=[str(HERE / "arm_mcp.py")],
)


async def main():
    # Silence the server subprocess's stderr so the transcript stays readable
    with open(os.devnull, "w") as devnull:
        await run(devnull)


async def run(errlog):
    async with stdio_client(server, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            # 1) handshake
            await session.initialize()
            print("1. Handshake OK\n")

            # 2) list the tools the server advertises — this is how an agent discovers them
            tools = (await session.list_tools()).tools
            print(f"2. Server exposes {len(tools)} tools:")
            for t in tools:
                print(f"     - {t.name}: {t.description.splitlines()[0]}")
            print()
            assert len(tools) == 3, f"expected 3 tools, got {len(tools)}"
            assert {t.name for t in tools} == {"move_arm", "get_state", "reset"}, \
                f"unexpected tool names: {sorted(t.name for t in tools)}"

            # 3) call a tool over the protocol (not a direct function call)
            print("3. Remote call  move_arm(angle1_deg=45, angle2_deg=-30):")
            r = await session.call_tool("move_arm", {"angle1_deg": 45, "angle2_deg": -30})
            text = r.content[0].text
            print("     ->", text)

            # The tip the server reports must be the tip the kinematics predict —
            # the same check whether the reply came from the live window or headless.
            m = re.search(r"x=(-?[0-9.]+), z=(-?[0-9.]+)", text)
            assert m, f"no tip coordinates in reply: {text!r}"
            fk_x, fk_z = arm_common.fk(45, -30)
            assert abs(float(m.group(1)) - fk_x) <= 1e-3, f"x={m.group(1)}, fk says {fk_x}"
            assert abs(float(m.group(2)) - fk_z) <= 1e-3, f"z={m.group(2)}, fk says {fk_z}"

            print("\n4. Remote call  get_state():")
            r = await session.call_tool("get_state", {})
            print("     ->", r.content[0].text)

            print("\nAll assertions passed: 3 tools, expected names, tip matches fk(45, -30).")


asyncio.run(main())
