import logging
import httpx
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
        
    return f"{system_prompt}\n\n{user_prompt}"

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

async def call_hf_inference_api(prompt: str, config: Settings, report: DTMReport) -> str:
    if not config.hf_api_token or config.hf_api_token == "your_token_here":
        logger.warning("HF_API_TOKEN is not configured. Using fallback.")
        return fallback_response(report)
        
    headers = {
        "Authorization": f"Bearer {config.hf_api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 800,
            "temperature": 0.3,
            "return_full_text": False
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(config.hf_model_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            elif isinstance(data, dict) and "error" in data:
                logger.error(f"HF API Error: {data['error']}")
                return fallback_response(report)
            else:
                return str(data)
    except Exception as e:
        logger.error(f"Failed to call HF Inference API: {e}")
        return fallback_response(report)

async def generate_remediation_report(report: DTMReport, config: Settings) -> Dict[str, Any]:
    prompt = build_remediation_prompt(report)
    
    ai_advice = await call_hf_inference_api(prompt, config, report)
    
    failed_rules = [r for r in report.rules if r.status == "FAIL"]
    summary = [{"rule": r.rule_name, "fix_priority": r.severity} for r in failed_rules]
    
    return {
        "job_id": report.job_id,
        "ai_advice": ai_advice,
        "failed_rules_summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
