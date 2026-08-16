// Drive the agent from code with the Codex SDK — nobody types anything.
// Equivalent to the ./chat.sh demo, except a program hands out the task instead of a person.
//
// Run:  npm install && node agent/arm_agent.mjs
// PYTHON overrides the interpreter (default: python3).
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Codex } from "@openai/codex-sdk";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");
const PYTHON = process.env.PYTHON ?? "python3";

// 1) Create the client and attach the arm MCP server
//    (equivalent to the CLI's -c mcp_servers.arm...)
const codex = new Codex({
  config: {
    mcp_servers: {
      arm: {
        command: PYTHON,
        args: [path.join(REPO, "arm_mcp.py")],
        startup_timeout_sec: 60,
      },
    },
  },
});

// 2) Start a thread with sandbox and approval settings
//    (equivalent to the CLI's -c sandbox_mode / approval_policy)
const thread = codex.startThread({
  sandboxMode: "danger-full-access",
  approvalPolicy: "never",
  skipGitRepoCheck: true,
});

// 3) Hand out the task in code.
//
//    The arm is a black box on purpose: there is no inverse-kinematics tool, and the link
//    lengths are never disclosed. The only way to the answer is to move, look at where the
//    tip landed, and correct — twice over, for two targets in different directions.
const TARGETS = "(x = -0.50, z = 0.62)  then  (x = 0.62, z = 0.35)";
const goal = [
  "You control a two-joint robot arm through the `arm` MCP server.",
  "move_arm(angle1_deg, angle2_deg) sets both joint angles and returns the resulting tip position;",
  "get_state() reports the current pose; reset() returns to zero.",
  "",
  "You have NOT been told the link lengths, and there is no inverse-kinematics tool.",
  "Do not assume a geometry — discover what you need by moving and observing.",
  "",
  "Reach these two targets in order, each within a tolerance of 0.05:",
  "first (x = -0.50, z = 0.62), then (x = 0.62, z = 0.35).",
  "",
  "This is a live demonstration, so keep it tight:",
  "use at most FOUR moves per target, and make bold corrections rather than creeping up in small steps.",
  "Call reset() once between the two targets.",
  "Say one short line when each target is met.",
  "",
  "Finish with a single sentence on how you found them. Reply in English.",
].join(" ");

const pad = (v, n) => String(v).padStart(n);
const t0 = Date.now();
let calls = 0;

console.log("\x1b[1m=== Agent driven from code — nobody typing ===\x1b[0m\n");
console.log("  Task     reach two targets, tolerance 0.05, max 4 moves each");
console.log(`  Targets  ${TARGETS}`);
console.log("  Given    a forward tool only — no IK, no link lengths\n");

const { events } = await thread.runStreamed(goal);
for await (const ev of events) {
  if (ev.type !== "item.completed") continue;
  const it = ev.item;

  if (it.type === "mcp_tool_call") {
    calls += 1;
    let a = it.arguments;
    if (typeof a === "string") { try { a = JSON.parse(a); } catch { a = {}; } }
    a = a ?? {};
    if (it.tool === "reset") {
      console.log("  --  reset      ------- target 1 done, swinging back -------");
      continue;
    }
    const detail = it.tool === "move_arm"
      ? `j1=${pad(Number(a.angle1_deg).toFixed(1), 7)}   j2=${pad(Number(a.angle2_deg).toFixed(1), 7)}`
      : "";
    console.log(`  ${pad(calls, 2)}  ${it.tool.padEnd(10)} ${detail}`);
  } else if (it.type === "agent_message") {
    console.log(`\n\x1b[36m[agent]\x1b[0m ${it.text}\n`);
  }
}

const secs = ((Date.now() - t0) / 1000).toFixed(0);
console.log(`\x1b[1m=== done — ${calls} tool calls in ${secs}s ===\x1b[0m`);
