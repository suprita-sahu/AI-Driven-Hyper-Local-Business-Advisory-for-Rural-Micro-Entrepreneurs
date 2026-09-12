import os
import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from groq import Groq

from financial_engine import calculate_financial_structure

load_dotenv()

app = FastAPI(
    title="MoSJE Rural Enterprise Advisory API",
    description="Hyper-local AI Feasibility & Scheme Router using Groq LPU inference",
    version="1.0.0"
)

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("CRITICAL: GROQ_API_KEY is not set in environment or .env file.")

groq_client = Groq(api_key=GROQ_API_KEY)


# ----------------- Request / Response Models -----------------

class AdvisoryRequest(BaseModel):
    state: str = Field(..., example="Telangana")
    district: str = Field(..., example="Warangal")
    block_or_mandal: str = Field(..., example="Geesugonda")
    village_or_panchayat: str = Field(..., example="Dharmaram")
    business_category: str = Field(..., example="Dairy Milk Chilling Unit")
    available_margin_capital: float = Field(..., example=100000.0)
    preferred_language: str = Field(default="English", example="English")


class AdvisoryResponse(BaseModel):
    financial_roadmap: Dict[str, Any]
    feasibility_study: Dict[str, Any]


# ----------------- Core Advisory Endpoint -----------------

@app.post("/api/v1/generate-advisory", response_model=AdvisoryResponse)
async def generate_advisory(payload: AdvisoryRequest):
    # Step 1: Calculate Financial Structure deterministically
    try:
        fin_data = calculate_financial_structure(payload.available_margin_capital)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Step 2: Formulate Groq Prompt
    system_prompt = (
        "You are an institutional rural business consultant for India's Ministry of Social Justice and Empowerment (MoSJE).\n"
        "Your task is to generate a realistic, hyper-local feasibility report for a rural micro-enterprise.\n"
        "You MUST respond ONLY with valid JSON. Use this exact schema:\n"
        "{\n"
        '  "market_reach": {\n'
        '    "catchment_radius_km": "5-10 km",\n'
        '    "estimated_consumer_base": "number or description",\n'
        '    "primary_distribution_channels": ["channel 1", "channel 2"]\n'
        "  },\n"
        '  "opportunity_analysis": ["niche 1", "niche 2"],\n'
        '  "swot_analysis": {\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "opportunities": ["..."],\n'
        '    "threats": ["..."]\n'
        "  },\n"
        '  "localized_threats": ["threat 1", "threat 2"],\n'
        '  "competitor_mapping": {\n'
        '    "estimated_density_in_block": "Low / Moderate / High",\n'
        '    "notes": "localized competitor context"\n'
        "  },\n"
        '  "product_market_value_and_pricing": {\n'
        '    "pricing_strategy": "strategy details",\n'
        '    "suggested_price_points": "price guidance",\n'
        '    "purchasing_power_alignment": "alignment notes"\n'
        "  }\n"
        "}\n"
        f"Language requirement: All analytical text and explanations must be in {payload.preferred_language}. Keep JSON keys strictly in English."
    )

    user_prompt = f"""
Evaluate the following micro-enterprise feasibility:
- Location: Village/Panchayat: {payload.village_or_panchayat}, Block/Mandal: {payload.block_or_mandal}, District: {payload.district}, State: {payload.state}
- Proposed Business: {payload.business_category}
- Beneficiary Contribution (10%): ₹{fin_data['user_margin_capital']:,.2f}
- Sanctioned Concessional Loan (90%): ₹{fin_data['sanctioned_loan_amount']:,.2f}
- Total Project Budget: ₹{fin_data['total_project_cost']:,.2f}
- Scheme Routed: {fin_data['scheme_details']['name']}

Evaluate local haats/shandies, mandi proximity, seasonal power/water supplies, and regional purchasing power.
"""

    # Step 3: Run Inference via Groq LPU
    try:
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2500
        )
        report_json = json.loads(completion.choices[0].message.content)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Groq generation failed: {str(exc)}"
        )

    return AdvisoryResponse(
        financial_roadmap=fin_data,
        feasibility_study=report_json
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)