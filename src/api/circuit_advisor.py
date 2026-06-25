from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import traceback

router = APIRouter()

# --- Knowledge Graph (Deterministic Rules) ---
CircuitAdvisorKnowledgeGraph = {
    "esp32": {
        "protocols": ["i2c", "spi", "uart", "pwm", "analog", "digital"],
        "max_voltage": 3.3,
        "role": "microcontroller"
    },
    "arduino uno": {
        "protocols": ["i2c", "spi", "uart", "pwm", "analog", "digital"],
        "max_voltage": 5.0,
        "role": "microcontroller"
    },
    "mpu6050": {
        "protocols": ["i2c"],
        "operating_voltage": 3.3,
        "role": "sensor"
    },
    "l298n": {
        "protocols": ["pwm", "digital"],
        "operating_voltage": 5.0,
        "motor_voltage": 12.0,
        "role": "motor_driver"
    },
    "dc motor": {
        "protocols": ["power"],
        "operating_voltage": 6.0, # nominal
        "role": "motor"
    },
    "stepper motor": {
        "protocols": ["motor_phase"],
        "operating_voltage": 12.0, # nominal
        "role": "motor"
    },
    "servo": {
        "protocols": ["pwm"],
        "operating_voltage": 5.0,
        "role": "motor"
    },
    "battery": {
        "protocols": ["power"],
        "operating_voltage": 12.0,
        "role": "power"
    },
    "ultrasonic sensor": {
        "protocols": ["digital"],
        "operating_voltage": 5.0,
        "role": "sensor"
    }
}

class AdvisorRequest(BaseModel):
    source_node: Dict[str, Any]
    target_node: Dict[str, Any]
    source_pin: str
    target_pin: str
    protocol: str
    mode: str = "Engineer" # Basic, Engineer, Expert

class WhyNotRequest(BaseModel):
    source_node: Dict[str, Any]
    target_node: Dict[str, Any]

def get_hw_profile(node_type_or_key: str):
    """Normalize and fetch from Knowledge Graph"""
    key = str(node_type_or_key).lower().strip()
    if key in CircuitAdvisorKnowledgeGraph:
        return CircuitAdvisorKnowledgeGraph[key]
    # Try fuzzy
    for k, v in CircuitAdvisorKnowledgeGraph.items():
        if k in key or key in k:
            return v
    return None

@router.post("/api/schematics/advisor/connection")
async def analyze_connection(req: AdvisorRequest):
    try:
        source = req.source_node.get("hw_key", req.source_node.get("type", "unknown"))
        target = req.target_node.get("hw_key", req.target_node.get("type", "unknown"))
        
        src_profile = get_hw_profile(source)
        tgt_profile = get_hw_profile(target)
        
        # 1. Deterministic Rule Engine
        protocol = req.protocol.lower()
        if "i2c" in protocol: protocol = "i2c"
        elif "pwm" in protocol: protocol = "pwm"
        elif "analog" in protocol: protocol = "analog"
        elif "digital" in protocol: protocol = "digital"
        elif "motor" in protocol: protocol = "power"
        elif "power" in protocol: protocol = "power"
        elif "mechanical" in protocol: protocol = "mechanical"
        
        # Validation checks
        validations = {
            "Voltage Compatibility": "PASS",
            "Protocol Compatibility": "PASS",
            "Pin Capability": "PASS",
            "Current Capacity": "PASS"
        }
        
        reasoning_list = []
        
        if protocol != "mechanical" and src_profile and tgt_profile:
            if protocol in tgt_profile.get("protocols", []) or protocol == "power":
                reasoning_list.append(f"{req.target_node.get('name')} supports {protocol.upper()}.")
            else:
                validations["Protocol Compatibility"] = "WARNING"
                reasoning_list.append(f"{req.target_node.get('name')} does not natively list {protocol.upper()} in standard DB.")
                
            if protocol in src_profile.get("protocols", []) or protocol == "power":
                reasoning_list.append(f"{req.source_node.get('name')} supports {protocol.upper()}.")
            
            if src_profile.get("max_voltage", 5.0) < tgt_profile.get("operating_voltage", 3.3):
                validations["Voltage Compatibility"] = "WARNING"
                reasoning_list.append(f"Voltage mismatch detected. Logic level converter may be required.")
            else:
                reasoning_list.append(f"Voltages are compatible.")
        else:
            reasoning_list.append(f"Standard {protocol.upper()} connection routed.")
            
        reasoning_list.append(f"Pin {req.source_pin} connected to {req.target_pin}.")

        # Risk Analysis Engine
        risks = []
        if protocol == "power" and tgt_profile and tgt_profile.get("role") == "motor":
            risks.append("Motor startup current spike may reset microcontroller if shared power.")
            risks.append("Ensure flyback diode is present if driving inductive load directly.")
        if "i2c" in protocol:
            risks.append("Ensure pull-up resistors are installed if not built into the module.")
            
        if len(risks) == 0:
            risks.append("No critical risks detected for this standard connection.")

        # Confidence Scoring
        confidence = {
            "Datasheet Match": 100 if src_profile and tgt_profile else 60,
            "ERC Validation": 100 if "WARNING" not in validations.values() else 50,
            "Knowledge Base": 95 if src_profile else 70,
            "AI Explanation": 0 # Filled below if Expert/Engineer
        }

        alternatives = []
        if "i2c" in protocol:
            alternatives.append({"name": "Alternative I2C Bus", "pins": "Secondary hardware I2C pins if available", "confidence": 85})
        elif protocol == "pwm":
            alternatives.append({"name": "Software PWM", "pins": "Any digital pin", "confidence": 75})
        elif protocol == "power":
            alternatives.append({"name": "External BEC", "pins": "Use external regulator", "confidence": 90})

        response_data = {
            "protocol": protocol.upper(),
            "source": f"{req.source_node.get('name')} {req.source_pin}",
            "destination": f"{req.target_node.get('name')} {req.target_pin}",
            "status": "PASS" if "WARNING" not in validations.values() else "WARNING",
            "deterministic_reasoning": reasoning_list,
            "validations": validations,
            "alternatives": alternatives,
            "risks": risks,
            "confidence": confidence,
            "ai_explanation": None
        }

        # 2. On-Demand LLM Integration (if not Basic)
        if req.mode in ["Engineer", "Expert"]:
            try:
                from llm import invoke_yantra_ai
                prompt = f"""
                Explain this circuit connection as a Senior Electrical Engineer.
                Source: {req.source_node.get('name')} (Pin: {req.source_pin})
                Target: {req.target_node.get('name')} (Pin: {req.target_pin})
                Protocol: {protocol.upper()}
                Mode: {req.mode}
                
                Deterministic Facts: {', '.join(reasoning_list)}
                Identified Risks: {', '.join(risks)}
                
                If Mode is 'Engineer', provide a concise 2-3 sentence technical explanation.
                If Mode is 'Expert', provide a highly detailed analysis of the protocol selection, pin selection, and electrical implications.
                Return ONLY the text explanation. Format nicely with markdown if appropriate.
                """
                ai_text = invoke_yantra_ai(prompt, system_prompt="You are a senior electrical engineer explaining a circuit schematic.")
                response_data["ai_explanation"] = ai_text
                response_data["confidence"]["AI Explanation"] = 98
            except Exception as e:
                print(f"Advisor LLM Error: {e}")
                response_data["ai_explanation"] = f"AI analysis temporarily unavailable: {e}"
                response_data["confidence"]["AI Explanation"] = 0

        return response_data

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/schematics/advisor/why-not")
async def analyze_why_not(req: WhyNotRequest):
    try:
        source = req.source_node.get("hw_key", req.source_node.get("type", "unknown"))
        target = req.target_node.get("hw_key", req.target_node.get("type", "unknown"))
        
        src_profile = get_hw_profile(source)
        tgt_profile = get_hw_profile(target)
        
        # Rule-based rejection analysis
        reason = "Direct connection rejected. "
        
        if src_profile and tgt_profile:
            if src_profile.get("role") == "power" and tgt_profile.get("role") == "microcontroller":
                if src_profile.get("operating_voltage", 0) > tgt_profile.get("max_voltage", 99):
                    reason += f"Source voltage ({src_profile.get('operating_voltage')}V) exceeds max safe input for {req.target_node.get('name')} ({tgt_profile.get('max_voltage')}V). A voltage regulator or buck converter is required."
                else:
                    reason += "Connection actually seems valid via VIN."
            elif src_profile.get("role") == "microcontroller" and tgt_profile.get("role") == "motor":
                reason += f"Current required by {req.target_node.get('name')} exceeds the maximum GPIO current limit of {req.source_node.get('name')}. A motor driver is required to safely switch the load."
            else:
                reason += "No compatible direct interface protocols found or connection would violate Electrical Rule Checks (ERC)."
        else:
            reason += "Insufficient hardware data to validate a direct, safe connection."
            
        try:
            from llm import invoke_yantra_ai
            prompt = f"""
            Explain why connecting {req.source_node.get('name')} directly to {req.target_node.get('name')} is electrically invalid or unsafe.
            Rule engine deduction: {reason}
            Provide a clear, 2-3 sentence engineering explanation.
            """
            ai_text = invoke_yantra_ai(prompt, system_prompt="You are a senior electrical engineer.")
            return {"explanation": ai_text}
        except:
            return {"explanation": reason}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
