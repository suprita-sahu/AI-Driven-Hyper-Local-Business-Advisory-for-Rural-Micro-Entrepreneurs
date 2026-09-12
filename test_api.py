import requests
import json

payload = {
    "state": "Telangana",
    "district": "Warangal",
    "block_or_mandal": "Geesugonda",
    "village_or_panchayat": "Dharmaram",
    "business_category": "Dairy Milk Chilling Unit",
    "available_margin_capital": 100000.0,
    "preferred_language": "English"
}

print("Sending request to FastAPI...")
response = requests.post("http://localhost:8000/api/v1/generate-advisory", json=payload)

if response.status_code == 200:
    print("\nSUCCESS! Financial Summary:")
    res_data = response.json()
    fin = res_data["financial_roadmap"]
    print(f"Scheme Selected: {fin['scheme_details']['name']}")
    print(f"Project Cost: Rs. {fin['total_project_cost']}")
    print(f"Sanctioned Loan: Rs. {fin['sanctioned_loan_amount']}")
    print(f"Quarterly EMI: Rs. {fin['quarterly_emi']}")
    print("\nSample Feasibility Reach:")
    print(json.dumps(res_data["feasibility_study"]["market_reach"], indent=2))
else:
    print(f"FAILED ({response.status_code}): {response.text}")