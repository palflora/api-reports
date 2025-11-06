import json
import datetime
import requests

# Prompt the user for their API key
api_key = input("Please enter your Calflora-API-Key: ")
 
# Get all Calflora observation data for group
url = 'https://api.calflora.org/observations'
params = {
    'maxResults': 0, # leave off for default (2000) or set to 0 for unlimited
    'groupIds': '140', # 140 = OC Parks
    'formatResults': 'true'
}
headers = {
    'accept': 'application/geo+json',
    'X-API-Key': api_key
}
print(url) 
print(params)
print(headers)
response = requests.get(url, params=params, headers=headers)
 
# Check if the request was successful
if response.status_code == 200:
    data = response.json()
data2=data
print('Searching for duplicate records')

# initialize duplicate counter
ct=0

# loop through each observation and find any observations with same lat/long,date,observer but different unique ID
for f in data['features']:
	fID=f['properties'].get('ID')
	fLat=f['properties'].get('Latitude')
	fLong=f['properties'].get('Longitude')
	fDate=f['properties'].get('Date')
	fObs=f['properties'].get('Observer')
	for d in data2['features']:
		dID=d['properties'].get('ID')
		dLat=d['properties'].get('Latitude')
		dLong=d['properties'].get('Longitude')
		dDate=d['properties'].get('Date')
		dObs=d['properties'].get('Observer')
		if(fID!=dID and fLat==dLat and fLong==dLong and fDate==dDate):
			print(fID + ' is dup of ' + dID)
			print(fID+'|'+str(fLat)+'|'+str(fLong)+'|'+fDate+'|'+fObs+'|'+dID+'|'+str(dLat)+'|'+str(dLong)+'|'+dDate+'|'+dObs)
			ct=ct+1

# print total duplicates found
print('total='+str(ct))
