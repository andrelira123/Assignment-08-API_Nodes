import requests

from google.oauth2 import service_account
from google.auth.transport.requests import Request

url = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"

my_data = {
    'q': "Roses"
}

response = requests.get(url, data=my_data)
data = response.json()
object_id = data['objectIDs'][0]  

object_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"
response = requests.get(object_url)
art_data = response.json()
title = art_data['title']
artist = art_data['artistDisplayName']

meme_url = "https://api.imgflip.com/get_memes"
response = requests.get(meme_url)
meme = response.json()['data']['memes'][0]['name']

creds = service_account.Credentials.from_service_account_file(
    "keys/service.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

# Fetch an access token (this is what gcloud auth print-access-token returns)
creds.refresh(Request())
token = creds.token

my_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

project_id = creds.project_id          # read from service.json
location = "global"
model = "gemini-3.8-flash"             # copy the exact ID from Model Garden

gemini_url = (f"https://aiplatform.googleapis.com/v1/projects/{project_id}"
              f"/locations/{location}/publishers/google/models/{model}:generateContent")

body = {"contents": [{"role": "user", "parts": [{"text": f"You're an ad agency creative director. Write a one-line campaign brief that reimagines {title} by {artist} as a modern ad for a product of your choosing, then write a plan for meme using the {meme} template."}]}]}
r = requests.post(gemini_url, headers=my_headers, json=body)
text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
print(text)


