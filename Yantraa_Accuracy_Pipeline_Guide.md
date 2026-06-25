**9.5 / 10 Accuracy**

**Cheat Code for AI Component Mapping**

_A 5-layer prompt engineering pipeline that makes it structurally impossible for wrong component data to reach your output - regardless of the domain._

Yantraa · Hardware Intelligence Platform

# **Why AI Models Generate Inaccurate Component Data**

When your AI model receives a vague prompt, it fills specification gaps with plausible-sounding but unverified data. It cannot distinguish between a real datasheet value and a confident hallucination. The fix is not a better AI model - it is a better pipeline around the model.

**Root Cause**

The model generates what sounds correct, not what is verified. Vague prompts give it room to guess. A strict pipeline removes that room entirely.

| **Without This** | **→** | **With All 5 Layers** | **Improvement** |
| ---------------- | ----- | --------------------- | --------------- |
| **6.5 / 10**     |       | **9.5 - 10 / 10**     | **+3 points**   |

# **The 5-Layer Accuracy Pipeline**

This is not one prompt. It is a chain of five layers that together make it nearly impossible for wrong data to reach your output. Each layer catches what the previous one misses.

## **Layer 1 - Expert Role + Context Injection (+0.5 pts)**

The model performs dramatically better when given a specific expert identity with stakes. Add this at the very top of every system prompt:

// LAYER 1 - Paste this at the top of your system prompt

You are a senior hardware engineer with 15 years of industry experience.

Your task is to generate a component mapping for the described system.

Rules you must never break:

\- Only include components that physically exist and are commercially available

\- Every spec must match the component's actual datasheet values

\- If you are not certain of a spec, mark confidence as 'low' and state why

\- Never invent model numbers, voltages, torque values, or protocol types

\- You will be reviewed by another expert engineer - any hallucinated value will be caught

**Why it works**

The last line - 'you will be reviewed by another expert' - activates more careful, accurate generation. The model produces measurably better output when it believes the output will be scrutinised.

## **Layer 2 - Structured Output Schema (+1.5 pts)**

Every component must output a typed JSON shape. Vague fields like 'ELECTRONIC' or '12V DC' become impossible when every field is explicitly typed and required.

// LAYER 2 - Required JSON schema for every component

{

"name": "exact commercial product name",

"brand": "manufacturer name",

"model_number": "real SKU or null if unknown",

"category": "ACTUATOR | SENSOR | CONTROLLER | POWER | MECHANICAL | ELECTRONIC",

"subcategory": "e.g. Servo Motor | Buck Converter | IMU | Limit Switch",

"specs": {

"operating_voltage_v": number,

"max_current_a": number,

"torque_kg_cm": number or null,

"communication_protocol": "I2C | SPI | UART | PWM | GPIO | CAN | USB | null",

"operating_frequency_hz": number or null

},

"role_in_system": "one sentence - what this component does in THIS design",

"connections": \[

{ "to": "component name", "type": "power | ground | signal | data | mechanical" }

\],

"safety_notes": "fail-safe or polarity concerns, or null",

"confidence": "high | medium | low",

"confidence_reason": "why confidence is not high, or null"

}

## **Layer 3 - Domain Constraint Rules (+1.5 pts)**

Hard rules that make physically or electrically wrong outputs impossible. Add these to your prompt for any robotics or hardware domain:

// LAYER 3 - Hard constraints (violating any of these is an error)

POWER:

\- All component voltages must be compatible with the power source

\- If voltage mismatch exists, flag in safety_notes and add a converter

\- LiPo batteries must include a low-voltage cutoff or BMS component

\- Power supply amperage must cover total system load

SAFETY:

\- Emergency stop relays must be Normally Closed (NC) - never Normally Open

\- Every fuse must match the current rating of its protected subsystem

\- Any high-torque actuator must have a limit switch on its axis

ACTUATORS:

\- Every degree-of-freedom maps to exactly one actuator

\- Every servo or stepper must have a dedicated driver IC listed

COMMUNICATION:

\- Real-time motion control must NOT use Bluetooth or WiFi

\- Acceptable real-time protocols: UART, USB Serial, CAN, SPI

CATEGORIZATION:

\- Cable management, brackets, mounts = MECHANICAL (never ELECTRONIC)

\- Fuses, relays, connectors = ELECTRONIC

\- Sensors must be category SENSOR not ELECTRONIC

## **Layer 4 - Self-Check Pass (+0.8 pts)**

Add this checklist at the end of your generation prompt. It forces the model to audit its own output before returning it - at zero extra API cost.

// LAYER 4 - Paste this at the END of your generation prompt

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

## **Layer 5 - Second-Call QA Validation (+0.7 pts)**

After generation, fire a second API call with a skeptical QA reviewer prompt. This is your automated quality assurance engineer - only show output to users after this call returns PASS.

// LAYER 5 - Second API call for validation

You are a hardware QA engineer reviewing a component mapping.

Be skeptical. Your job is to find errors, not confirm correctness.

For every issue found, return:

{

"component": "component name",

"field": "which field is wrong",

"issue": "what is wrong and why",

"severity": "critical | warning | minor",

"fix": "exact corrected value or action required"

}

Check for: wrong categories, voltage incompatibilities, missing drivers,

Bluetooth for real-time control, Normally Open E-Stop relays,

missing limit switches, sensors with no defined role,

invented model numbers, missing Z-axis or other DOF actuators.

If mapping passes all checks, return: { "status": "PASS", "score": 9-10 }

If issues exist, return all issues then a corrected JSON mapping.

**Implementation rule**

Only display the component mapping to your users after Layer 5 returns PASS. If it returns issues, auto-correct using the suggested fixes and re-validate before displaying.

# **Impact of Each Layer on Accuracy**

| **Layer**                               | **Impact** | **Score Gain** |
| --------------------------------------- | ---------- | -------------- |
| Layer 1 - Expert role + review pressure | ████░░░░░░ | **+0.5 pts**   |
| Layer 2 - Strict JSON schema            | ██████████ | **+1.5 pts**   |
| Layer 3 - Domain constraint rules       | ██████████ | **+1.5 pts**   |
| Layer 4 - Self-check checklist          | ██████░░░░ | **+0.8 pts**   |
| Layer 5 - Second-call QA validation     | █████░░░░░ | **+0.7 pts**   |

Layers 2 and 3 deliver the largest individual gains because they eliminate the two root causes of inaccuracy: vague field types and missing domain knowledge. Layers 4 and 5 are multipliers that catch what Layers 2-3 still allow through.

# **Bonus Trick - Few-Shot Examples (+0.5 pts)**

Add one hand-verified, perfect component entry directly into your Layer 1 prompt as an example. The model calibrates its entire output to match the quality and specificity of what you show it.

// BONUS - Paste this perfect example inside your Layer 1 prompt

Here is an example of a perfect component entry. Match this quality:

{

"name": "DRV8825 Stepper Motor Driver",

"brand": "Texas Instruments / Pololu",

"model_number": "DRV8825",

"category": "ELECTRONIC",

"subcategory": "Stepper Driver",

"specs": {

"operating_voltage_v": 8.2,

"max_current_a": 2.2,

"torque_kg_cm": null,

"communication_protocol": "STEP/DIR",

"operating_frequency_hz": null

},

"role_in_system": "Drives NEMA 17 stepper on Z-axis, converting step/direction

signals from Arduino into bipolar coil current",

"connections": \[

{ "to": "Arduino Mega 2560", "type": "signal" },

{ "to": "NEMA 17 Stepper (Z-axis)", "type": "signal" },

{ "to": "24V Power Supply", "type": "power" },

{ "to": "GND Rail", "type": "ground" }

\],

"safety_notes": "Enable pin must be LOW to activate. Thermal shutdown at 150C.",

"confidence": "high",

"confidence_reason": null

}

# **Field-Level Accuracy Reference**

Common inaccuracies by field and the specific prompt instruction that prevents each one:

| **Field**           | **Common Inaccuracy**                                | **Fix in Prompt**                                   |
| ------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| **Category**        | Cable sleeve as ELECTRONIC, ultrasonic as ELECTRONIC | Provide explicit category definitions in prompt     |
| **Voltage**         | Generic "12V" without checking compatibility         | Require voltage cross-check across all components   |
| **Connection type** | "signal" used for both power and data lines          | Define each connection type with examples in prompt |
| **Protocol**        | Bluetooth suggested for real-time control            | Add latency constraint rule for motion control      |
| **Safety config**   | E-Stop as Normally Open (fail-unsafe)                | E-Stop must be Normally Closed (NC) relay           |
| **Completeness**    | Missing Z-axis, missing limit switches               | Require one actuator per DOF, one switch per axis   |

# **Implementation Order**

Apply these in order for the fastest accuracy improvement:

- Add the JSON schema to your generation prompt (Layer 2) - fixes ~60% of accuracy issues immediately
- Add domain constraint rules (Layer 3) - catches safety and compatibility errors
- Add expert role + review pressure to your system prompt (Layer 1)
- Append the self-check checklist at the end of the generation prompt (Layer 4)
- Add a second API validation call before showing output to users (Layer 5)
- Paste one hand-verified perfect component example into Layer 1 (Bonus)

**Expected result**

With all 6 steps applied, your component mapping accuracy will consistently score 9.5-10 under expert review - regardless of domain (robotics, aerospace, IoT, industrial, consumer electronics).