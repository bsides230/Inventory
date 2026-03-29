import requests

print("Updating item...")
res = requests.post("http://localhost:8030/api/inventory/produce/update", json={
    "id": "produce_0",
    "qty": 5,
    "unit": "case"
})
print(res.json())

print("Submitting order...")
res2 = requests.post("http://localhost:8030/api/submit_order", json={
    "date": "2024-03-12",
    "is_rush": False
})
print(res2.json())
