const fs = require('fs');
const p = 'd:/FINAL YANTRA/yantraa-advance/frontend/src/components/ui/tabs/mapping-tab.tsx';
let code = fs.readFileSync(p, 'utf8');

const newFn = `async function fetchComponentsFromRAG(
    topic: string,
    aiResponseFallback: string,
    existingNodes: ComponentNode[]
): Promise<RawComponent[]> {
    const existingStr = existingNodes.length > 0 
        ? existingNodes.map(n => \`- \${n.label} (\${n.category})\`).join("\\n") 
        : "None";

    const prompt1 = \`
You are a senior hardware engineer with 15 years of industry experience.
Your task is to generate a component mapping for the described system.

Rules you must never break:
- Only include components that physically exist and are commercially available
- Every spec must match the component's actual datasheet values
- If you are not certain of a spec, mark confidence as 'low' and state why
- Never invent model numbers, voltages, torque values, or protocol types
- You will be reviewed by another expert engineer - any hallucinated value will be caught

Here is an example of a perfect component entry. Match this quality:
{
  "name": "DRV8825 Stepper Motor Driver",
  "brand": "Texas Instruments / Pololu",
  "model_number": "DRV8825",
  "category": "electronic",
  "subcategory": "Stepper Driver",
  "specs": {
    "operating_voltage_v": 8.2,
    "max_current_a": 2.2,
    "torque_kg_cm": null,
    "communication_protocol": "STEP/DIR",
    "operating_frequency_hz": null
  },
  "role_in_system": "Drives NEMA 17 stepper on Z-axis, converting step/direction signals from Arduino into bipolar coil current",
  "connections": [
    { "to": "Arduino Mega 2560", "type": "signal" },
    { "to": "NEMA 17 Stepper (Z-axis)", "type": "signal" },
    { "to": "24V Power Supply", "type": "power" },
    { "to": "GND Rail", "type": "ground" }
  ],
  "safety_notes": "Enable pin must be LOW to activate. Thermal shutdown at 150C.",
  "confidence": "high",
  "confidence_reason": null
}

POWER:
- All component voltages must be compatible with the power source
- If voltage mismatch exists, flag in safety_notes and add a converter
- LiPo batteries must include a low-voltage cutoff or BMS component
- Power supply amperage must cover total system load

SAFETY:
- Emergency stop relays must be Normally Closed (NC) - never Normally Open
- Every fuse must match the current rating of its protected subsystem
- Any high-torque actuator must have a limit switch on its axis

ACTUATORS:
- Every degree-of-freedom maps to exactly one actuator
- Every servo or stepper must have a dedicated driver IC listed

COMMUNICATION:
- Real-time motion control must NOT use Bluetooth or WiFi
- Acceptable real-time protocols: UART, USB Serial, CAN, SPI

CATEGORIZATION:
- Cable management, brackets, mounts = mechanical (never electronic)
- Fuses, relays, connectors = electronic
- Sensors must be category sensor not electronic

Existing components:
\${existingStr}

Topic: '\${topic}'

Output ONLY a JSON array of objects with the exact schema as the example above. Do not output any prose.

Before returning your answer, run this checklist on your own output:
□ Does every actuator have a paired driver?
□ Does every DOF have exactly one actuator?
□ Are all voltages compatible with the power source?
□ Is the E-Stop relay Normally Closed?
□ Does every sensor have a specific role_in_system?
□ Are all categories correctly assigned (no sensors as ELECTRONIC)?
□ Are all real-time control protocols deterministic (no Bluetooth)?
□ Does total current draw fit within power supply rating?
□ Are there limit switches on every moving axis?
□ Are there any invented model numbers? (if yes, set model_number to null)

If any checkbox fails, fix the issue before returning the JSON.
Do not return the output until all boxes pass.
\`.trim();

    const qaPrompt = \`
You are a hardware QA engineer reviewing a component mapping.
Be skeptical. Your job is to find errors, not confirm correctness.
Check for: wrong categories, voltage incompatibilities, missing drivers, Bluetooth for real-time control, Normally Open E-Stop relays, missing limit switches, sensors with no defined role, invented model numbers, missing Z-axis or other DOF actuators.

If mapping passes all checks, return EXACTLY: {"status": "PASS", "score": 10}
If issues exist, return all issues then a corrected JSON mapping (inside a "corrected_mapping" array field).
Format:
{
  "status": "FAIL",
  "issues": [ { "component": "...", "field": "...", "issue": "...", "severity": "...", "fix": "..." } ],
  "corrected_mapping": [ ... full corrected json array ... ]
}
\`.trim();

    try {
        const res1 = await fetch(\`\${API_BASE}/api/ask\`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: prompt1 }),
        });
        
        if (res1.ok) {
            const data1 = await res1.json();
            const generationResult = String(data1.response ?? "");
            
            // Layer 5: QA Validation
            const qaRequest = qaPrompt + "\\n\\nMapping to review:\\n" + generationResult;
            const res2 = await fetch(\`\${API_BASE}/api/ask\`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: qaRequest }),
            });
            
            if (res2.ok) {
                const data2 = await res2.json();
                const qaResult = String(data2.response ?? "");
                try {
                    const cleanedQa = qaResult.replace(/\`\`\`json\\s*/gi, "").replace(/\`\`\`/g, "").trim();
                    const qaParsed = JSON.parse(cleanedQa);
                    if (qaParsed.status === "PASS") {
                        const parsed1 = parseRAGJson(generationResult);
                        if (parsed1 && parsed1.length > 0) return parsed1;
                    } else if (qaParsed.corrected_mapping && Array.isArray(qaParsed.corrected_mapping)) {
                        const parsedCorrected = parseRAGJson(JSON.stringify(qaParsed.corrected_mapping));
                        if (parsedCorrected && parsedCorrected.length > 0) return parsedCorrected;
                    }
                } catch (qaErr) {
                    console.warn("QA validation output parsing failed, using original generated result.", qaErr);
                    const parsed1 = parseRAGJson(generationResult);
                    if (parsed1 && parsed1.length > 0) return parsed1;
                }
            } else {
                const parsed1 = parseRAGJson(generationResult);
                if (parsed1 && parsed1.length > 0) return parsed1;
            }
        }
    } catch (e) {
        console.error("AI Generation pipeline error", e);
    }

    return fallbackExtract(aiResponseFallback);
}`;

code = code.replace(/async function fetchComponentsFromRAG\([\s\S]*?\n\}\n/, newFn + '\n\n');

fs.writeFileSync(p, code, 'utf8');
console.log("Done mapping-tab.tsx Accuracy Pipeline rewrite.");
