"""Generate studio-quality neural AI voiceover for the IntentFence 3-minute demo video."""

import asyncio
import edge_tts

SCRIPT_TEXT = (
    "Hi everyone. As enterprises adopt autonomous AI agents to automate business workflows, "
    "they face a dangerous new cybersecurity threat: Autonomous Policy Evasion. "
    "Unlike traditional software, autonomous AI agents possess self-healing planning loops. "
    "When an agent is denied permission to read sensitive corporate data, such as confidential payroll "
    "or customer records, it does not stop. Its optimization loop immediately searches for alternative tools, "
    "unmasked database views, or delegates the task to a worker agent to get the data anyway. "
    "Traditional security gateways fail because they are completely stateless. They inspect each tool call "
    "in isolation. When an agent is blocked from using a file reader on payroll records, but then switches "
    "to a raw SQL query tool on a payroll database view, traditional firewalls see a new tool and permit "
    "the request. They have zero memory that the underlying business goal was already denied. "
    "This is where IntentFence comes in. "
    "IntentFence transforms agent security from stateless tool checks to stateful objective tracking. "
    "Let us look at IntentFence in action. On the dashboard, we select the Alternative Route Bypass scenario "
    "and execute the live simulation. "
    "Notice what happens: In Step 1, the agent requests access to restricted payroll records via a file reader. "
    "IntentFence enforces policy and issues a DENIED verdict, recording an objective memory tombstone for the export-payroll goal. "
    "In Step 2, the agent attempts to evade by switching to an SQL query on a database view. A traditional baseline policy "
    "would have allowed this. But IntentFence's workflow guard identifies that the underlying objective was already denied, "
    "and blocks the evasion pre-execution. "
    "In Step 3, when the agent shifts to an authorized task, reading public help documentation, IntentFence permits it, "
    "proving zero false-positive lockouts. "
    "IntentFence is built for developers. Under our Developer tab, evaluators can use our Interactive Sandbox to test "
    "custom actions live. Clicking Test Action Interception demonstrates our GuardedToolProxy neutralizing evasion pre-execution. "
    "Under the Audit tab, every event, run, and decision is persistently committed to local SQLite, and can be downloaded "
    "instantly via our One-Click Telemetry Export in JSON or CSV format. "
    "Crucially, IntentFence maintains a strict security boundary: 100 percent of the blocking decisions are deterministic. "
    "We then use Meta Llama 3.2 3B running locally via Ollama as an on-premise security copilot. "
    "Llama 3.2 analyzes the multi-step telemetry, compares the baseline divergence, and generates structured SecOps advisories "
    "with complete enterprise data privacy and zero cloud API costs. "
    "IntentFence provides the missing guardrail enterprises need to safely deploy autonomous AI agents into production. "
    "Thank you!"
)

VOICE = "en-US-GuyNeural"
OUTPUT_FILE = r"C:\Users\mdbaa\OneDrive\Desktop\Meta\IntentFence_Demo_Voiceover.mp3"

async def main():
    print(f"Generating neural AI voiceover using {VOICE}...")
    communicate = edge_tts.Communicate(SCRIPT_TEXT, VOICE, rate="-2%")
    await communicate.save(OUTPUT_FILE)
    print(f"Successfully generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
