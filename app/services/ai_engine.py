import logging
import httpx
import re
from datetime import datetime, timezone
from typing import Dict, Any

from app.models.dtm_result import DTMReport
from app.config import Settings

logger = logging.getLogger(__name__)

def build_remediation_prompt(report: DTMReport) -> str:
    system_prompt = (
        "You are a senior BIW (Body-in-White) manufacturing engineer at an automotive OEM. "
        "You specialize in door hemming, stamping, and panel joining processes. "
        "You are reviewing a DTM (Design-to-Manufacturing) compliance report and must provide "
        "precise, actionable engineering fix advice."
    )
    
    failed_rules = [r for r in report.rules if r.status == "FAIL"]
    
    user_prompt = f"Door type: {report.door_type}\nOverall status: {report.overall_status}\n\n"
    if not failed_rules:
        user_prompt += "No rules failed. Please confirm the design is ready for manufacturing."
    else:
        user_prompt += "FAILED RULES:\n"
        for r in failed_rules:
            coords = ", ".join([f"({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f})" for c in r.defect_coordinates])
            user_prompt += (
                f"- Rule: {r.rule_name}\n"
                f"  Measured: {r.measured_value} {r.unit} (Threshold: {r.threshold} {r.unit})\n"
                f"  Severity: {r.severity}\n"
                f"  Coordinates: [{coords}]\n\n"
            )
        
        user_prompt += (
            "Please provide:\n"
            "1. Root cause analysis for each failure.\n"
            "2. Specific fix steps in CATIA V5 / SolidWorks.\n"
            "3. Tooling implications.\n"
            "4. Estimated rework risk level (LOW/MEDIUM/HIGH).\n"
        )
        
    return {"system": system_prompt, "user": user_prompt}

def fallback_response(report: DTMReport) -> str:
    failed_rules = [r for r in report.rules if r.status == "FAIL"]
    if not failed_rules:
        return "No failures detected. The design is compliant."
        
    advice = "AUTOMATED FALLBACK REMEDIATION ADVICE\n\n"
    for r in failed_rules:
        advice += f"Rule: {r.rule_name} (Severity: {r.severity})\n"
        if "Corner Fillet" in r.rule_name:
            advice += "Fix: Modify the die punch radius in the stamping tool to achieve the minimum required radius.\n"
        elif "Hem Flange Width" in r.rule_name or "Flange Extent" in r.rule_name:
            advice += "Fix: Adjust the flange trim line in the CAD model to ensure proper flange extent limits.\n"
        elif "Gap" in r.rule_name or "Interface" in r.rule_name or "Clearance" in r.rule_name:
            advice += "Fix: Adjust panel offset surfaces in CAD to satisfy gap and clearance requirements.\n"
        else:
            advice += "Fix: Review the CAD geometry in this region against standard BIW design guidelines.\n"
        advice += "\n"
        
    advice += "Tooling Implications: Moderate tooling update required.\nRisk Level: MEDIUM\n"
    return advice

async def call_lm_studio_api(prompt: Dict[str, str], config: Settings, report: DTMReport) -> str:
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": False
    }
    
    try:
        # timeout is 300 seconds for slow local models
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(config.lmstudio_model_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                msg = data["choices"][0]["message"]
                content = msg.get("content")
                if content is None:
                    # Model might return null content if it hits a safety filter or only returns reasoning
                    reasoning = msg.get("reasoning_content")
                    if reasoning:
                        return reasoning.strip()
                    logger.error(f"LM Studio API Error: returned null content. Raw: {data}")
                    return fallback_response(report)
                
                content = content.strip()
                # Local reasoning models often swallow the opening <think> tag, so we split by the closing tag
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                else:
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                
                # Also strip raw <think> tags if they are dangling at the end
                content = content.replace("<think>", "").strip()
                return content
            elif "error" in data:
                logger.error(f"LM Studio API Error: {data['error']}")
                return fallback_response(report)
            else:
                return str(data)
    except Exception as e:
        import traceback
        logger.error(f"Failed to call LM Studio Inference API: {e}\n{traceback.format_exc()}")
        return fallback_response(report)

async def generate_remediation_report(report: DTMReport, config: Settings) -> Dict[str, Any]:
    prompt = build_remediation_prompt(report)
    
    ai_advice = await call_lm_studio_api(prompt, config, report)
    
    failed_rules = [r for r in report.rules if r.status == "FAIL"]
    summary = [{"rule": r.rule_name, "fix_priority": r.severity} for r in failed_rules]
    
    return {
        "job_id": report.job_id,
        "ai_advice": ai_advice,
        "failed_rules_summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
