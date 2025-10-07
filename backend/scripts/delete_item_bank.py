import requests

# Delete the incomplete item bank
response = requests.delete('http://localhost:8000/api/item-banks/maths_complex_nos')
print(f"Delete: {response.status_code}")

