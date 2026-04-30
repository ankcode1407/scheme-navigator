import json

with open("data/schemes_extracted.json", encoding="utf-8") as f:
    data = json.load(f)

schemes = data["schemes"]
print(f"Total extracted: {len(schemes)}\n")

for i in [0, 5, 10, 20]:
    if i >= len(schemes):
        break
    s = schemes[i]
    print(f"--- Scheme {i+1}: {s['name']} ---")
    print(f"  Category:   {s['category']}")
    print(f"  Occupation: {s['eligibility']['occupation']}")
    print(f"  State:      {s['eligibility']['state']}")
    print(f"  Age min:    {s['eligibility']['age_min']}")
    print(f"  Residence:  {s['eligibility']['residence']}")
    print(f"  Income:     {s['eligibility']['income_category']}")
    print(f"  Benefit:    {s['benefit']}")
    print()