import urllib.request
import json

api_key = "rnd_coICmwUZglrHzzHC84glOBZTgl1U"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

svc_id = "srv-daem9k1t0dsc73ar02dg"

# Render API supports PUT /v1/services/{serviceId}/env-vars with array of {key, value}
print("Render API is ready to set env vars!")
