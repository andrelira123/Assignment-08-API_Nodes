import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

met_url = "https://collectionapi.metmuseum.org/public/collection/v1.1/search"

met_data = {
    "q":"George Washington",
    "medium":"Paintings"
}

response = requests.get(met_url, data=met_data)
if response.status_code == 200:
    data = response.json()
    pretty_json = json.dumps(data, indent=4, sort_keys=True)
    print(pretty_json)
    object_id = data['objectIDs'][0]
else:
    print("broken!")


#this will give me info about a painting using the object id
met_url2 = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}"

response2 = requests.get(met_url2)

if response2.status_code == 200:
    data = response2.json()
    title = data['title']
    artist = data['artistDisplayName']

else:
    print("broken!!!!")

print(title)
print(artist)

meme_url = "https://api.imgflip.com/get_memes"
meme_response = requests.get(meme_url)
if meme_response.status_code == 200:
    meme_data = meme_response.json()
    meme_name = meme_data['data']['memes'][0]['name']
    print(meme_name)
else:
    print("meme error")

#### GEMINI STUFF


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


gemini_url = (f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:generateContent")

body = {
    "contents": [
        {"role": "user", 
         "parts": [
             {"text": f"You're an ad agency creative director. Write a one-line campaign brief that reimagines {title} by {artist} as a modern ad for a product of your choosing, then write a plan for meme using the {meme_name} template."}
             ]
        }
    ]
}
response_ad = requests.post(gemini_url, headers=my_headers, json=body)
text = response_ad.json()["candidates"][0]["content"]["parts"][0]["text"]
print(text)