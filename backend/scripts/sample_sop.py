"""Seed a sample Hindi SOP for Press 1 (machine 1, Line A)."""
import json
import httpx

STEPS = [
    ("मशीन चालू करने से पहले बिजली का स्विच बंद कर दें।", True, "power_off"),
    ("सत्रह नंबर का बोल्ट लगाकर प्लेट को कस दें।", False, "measure"),
    ("प्लेट कसने के बाद ही मशीन चालू करें।", False, "power_on"),
    ("पैडल को पैर से धीरे धीरे दबाएं।", False, "moving_parts"),
    ("काम खत्म होने के बाद मशीन को साफ करके रिपोर्ट लिखें।", False, "clean"),
]

payload = {
    "machine_id": 1,
    "title": "Press 1 - रोज का संचालन",
    "language": "hi",
    "transcript": " ".join(text for text, _, _ in STEPS),
    "steps": [
        {"step_number": i, "text": text, "is_safety_warning": warn, "icon": icon}
        for i, (text, warn, icon) in enumerate(STEPS, start=1)
    ],
}

sop = httpx.post("http://localhost:8001/api/sop", json=payload, timeout=60).raise_for_status().json()
print(f"SOP {sop['id']} v{sop['version']} for machine {sop['machine_id']}")
for step in sop["steps"]:
    print(f"  {step['step_number']}. {step['text']}  {'[safety]' if step['is_safety_warning'] else ''}")
