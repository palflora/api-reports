import json
import requests
import datetime
import os
import re

print('Running QA/QC tests...')
# Prompt the user for their API key
api_key = input("Please enter your Calflora-API-Key: ")
#api_key = 'key'
 

# Specify the file path and name
#savejsonfile = input("Enter the file path (e.g., /path/to/observations.json): ")
 
grpID=140
headers = {
    'accept': 'application/geo+json',
    'X-API-Key': api_key
}

reportview=polyID=prjID=observerstr=None
projectname=polygonname=''
while(reportview!='user' and reportview!='project' and reportview!='preserve'):
    reportview = input("How would you like reports organized (user, project, preserve): ")

if(reportview=='user'):
    observerstr = input("If you want to limit by observer name, you can enter a partial name here (hit return for all): ")
elif(reportview=='project'):
    # Get list of Projects 
    response = requests.get('https://api.calflora.org/projects', {}, headers=headers)
    # Check if the request was successful
    prjmatches=False
    if response.status_code == 200:
        prj_partial = ""
        prjID=""
        while(not prj_partial):
            prj_partial = input("Please enter project name (partial OK):")
            if(prj_partial):
                projects=response.json()
                for p in projects:
                    if prj_partial in p["name"]:
                        print(p["id"]+ ': '+p["name"])
                        prjmatches=True
                if prjmatches==False:
                    prj_partial=None
                else:
                    while( not prjID):
                        validprjID = False
                        prjID = input("Please enter project ID: ")
                        for p in projects:
                            if p["id"]==prjID:
                                validprjID = True
                                projectname=p["name"]
                        if not validprjID:
                            prjID=""
                    print("You selected "+prjID+": "+projectname)
    else:
        print("error getting list of projects")
elif(reportview=='preserve'):
    # Get list of all regions
    response = requests.get('https://api.calflora.org/searchPolygons', {}, headers=headers)
    # Check if the request was successful
    if response.status_code == 200:
        regionstouse={}
        polyID=""
        #while( not prj_partial):
        #    prj_partial = input("Please enter project name (partial OK): ")    
        allregions=response.json()
        #print(allregions)
        for p in allregions:
            if p["ugroup"]==grpID:
                #if 'buffered' in p["name"]:
                print(p["id"] + ' => ' + p["name"])
        while( not polyID):
            validpolyID = False
            polyID = input("Please enter polygon ID: ") 
            for p in allregions:
                if p["id"] == polyID:
                    validpolyID = True
                    polygonname = p["name"]
            if not validpolyID:
                polyID=""
    else:
        print(f"Error: {response.status_code}")
    print("You selected "+polyID+": "+polygonname)

# function to ensure date is valid and in ISO format
#def validate(date_text):
#    try:
#        datetime.date.fromisoformat(date_text)
#    except ValueError:
#       raise ValueError("Incorrect data format, should be YYYY-MM-DD")
# couldn't figure out error handling on this

# class to build a nested dictionary
class AutoDict(dict):
    def __missing__(self, k):
        self[k] = AutoDict()
        return self[k]

# Get taxon
url = 'https://api.calflora.org/plantlists/px2896'
params = {
    'includePlants': 'true',
}
response = requests.get(url, params=params, headers=headers)
if response.status_code == 200:
    weeds=response.json()
    ocweednames=set()
    for w in weeds['plants']:
        ocweednames.add(w['taxon'])
else:
    print(f"Error: {response.status_code}")

#keep prompting for date until you get input
dateafter=''
while(not dateafter):
	dateafter = input("Start date for finding errors (YYYY-MM-DD): ")

if not os.path.exists('output'):
    os.mkdir('output')
if not os.path.exists('output/'+dateafter):
    os.mkdir('output/'+dateafter)
downloadpath='output/'+dateafter


# Get Calflora data
url = 'https://api.calflora.org/observations'
params = {
    #'taxon': 'Cynara cardunculus',    # filter either taxon or plantlistID 
    #'georef': 'a',                     # Access by others (a = published, c = obscured, r = private, z = unpublished)
    'maxResults': 0,                   # leave off for default (2000) or set to 0 for unlimited
    'dateAfter': dateafter,
    #'dateBefore': '2025-05-31',
    'csetId': '379', #define Column Set 136=OC Form, 379=OC API columns
    #'plantlistId': 'px3845',          # NROC 2023-27 Treatment Priority 1 & 2; filter either taxon or plantlistID 
    'observer': observerstr,
    #'myrec': 'true',                # Only My Records: only return records owned by the current user     
    'shapeId': polyID,          # 'shapeId' in Shape Editor or 'rid' in Calflora link
    'groupIds': grpID, #140 = OCP Plantopia, 250 = OC CG Group
    'projectIds': prjID,
    'includeGeometry': 'true',
    'formatResults': 'true'
}

response = requests.get(url, params=params, headers=headers)
 
def process_number_of_plants(value):
    # If the value is a range (e.g., "5-10"), calculate the mid number
    if isinstance(value, str) and '-' in value:
        try:
            start, end = value.split('-')
            mid = (float(start) + float(end)) / 2
            return round(mid), value  # Return both the mid value and the original range
        except ValueError:
            return None, value  # If there is an error in parsing, return None and the original value
    # If the value contains a '>' symbol (greater than), increment it by 1
    elif isinstance(value, str) and '>' in value:
        try:
            # Extract the number after the '>'
            number = float(value[1:])
            new_value = number + 1
            return str(new_value), value  # Return the new value and the original value
        except ValueError:
            return None, value  # If there is an error in parsing, return None and the original value
    # If the value contains special character, remove the special character
    elif isinstance(value, str):
        return re.sub(r'^\D+', '', value), value  # Return the cleaned value and original value
    else:
        return value, None  # Return the value and None if it's not a range or special format
 
print(params)
# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    # Convert the response into the desired GeoJSON format
    geojson_data = {
        "type": "FeatureCollection",
        "features": []
    }

    features = {}
    for item in data['features']:
        # Process the number of plants and get both processed value and original text
        number_of_plants, original_range = process_number_of_plants(item['properties'].get('Number of Plants', None))
        # Ensure treatment_notes is always a string
        treatment_notes = item['properties'].get('Treatment Notes', "")
        if treatment_notes is None:
            treatment_notes = ""  # Explicitly set to empty string if it's None
        # Append the original range (if any) to the Treatment Notes
        if original_range:
            treatment_notes += f" Original Number of Plants: {original_range}"
 
        features[item["id"]] = {
                "ID": item['id'],
                "Polygon": item['geometry'].get('type', None),
                "Observer": item['properties'].get('Observer', None),
                "ProjectID": item['properties'].get('Project #', None),
                "Project": item['properties'].get('Project', None),
                "Taxon": item['properties'].get('Taxon', None),
                "Common Name": item['properties'].get('Common Name', None),
                "Date_Time": item['properties'].get('Date / Time', None),
                "Infested Area Count": item['properties'].get('Infested Area Count', None),
                "Infested Area Units": item['properties'].get('Infested Area Units', None),
                "Distribution": item['properties'].get('Distribution', None),
                "Gross Area": item['properties'].get('Gross Area', None),
                "Number of Plants": number_of_plants,
                "Percent Cover": item['properties'].get('Percent Cover', None),                
                "Habitat": item['properties'].get('Habitat', None),
                "Phenology": item['properties'].get('Phenology', None),
                "Manual Treatment?": item['properties'].get('Manual Treatment 1?', None),
                "Mechanical Method": item['properties'].get('Mechanical Method', None),
                "Chemical Method": item['properties'].get('Chemical Method', None),
                "Treatment Notes": treatment_notes,  # Updated Treatment Notes
                "Percent Treated": item['properties'].get('Percent of Population Treated', None),
                "Region": item['properties'].get('Region', None),
                "Root": item['properties'].get('Root', None),
                "Seeds Removed num of 55 gallon bags": item['properties'].get('Seeds Removed (# of 55 gallon bags)', None),
                "Latitude": item['geometry']['coordinates'][0][1] if item['geometry']['type'] == 'Polygon' else item['geometry']['coordinates'][1],
                "Longitude": item['geometry']['coordinates'][0][0] if item['geometry']['type'] == 'Polygon' else item['geometry']['coordinates'][0]            
        }
        #print(features)
    errors=AutoDict() #records missing info
    verifies=AutoDict() #records that might need fixes
    observers=set()
    for i,f in features.items():
        if not f["Root"]:
            found=False
            for p,d in features.items():
                if d["Root"]==i:
                    found=True
            if not found:
                verifies[i]['unstacked']=True
        observers.add(f["Observer"])

    for i,f in features.items():
        if f["Polygon"] != 'Polygon':
            errors[i]['polygon']=True
        if not f["Gross Area"]:
            errors[i]['gross']=True
        if not f["Number of Plants"] and f["Number of Plants"]!=0:
            errors[i]['plantct']=True
        if not f["Percent Cover"] and not f["Infested Area Count"]:
            errors[i]['infested']=True
        if f["Manual Treatment?"] and not f["Mechanical Method"]:
            errors[i]['Mechanical']=True
        if (f["Mechanical Method"] or f["Chemical Method"]) and not f["Percent Treated"]:
            errors[i]['PercTrt']=True
        if f["ProjectID"]=='pr785':
            errors[i]['project']=True
        if f["Taxon"] not in ocweednames:
            verifies[i]['weedname']=True
        observers.add(f["Observer"])


    def buildreport(sortcriteria):
        # start html file
        html_content='<HTML><HEAD><TITLE>'+sortcriteria+' QA/QC since '+dateafter+'</TITLE></HEAD><BODY><H1>ERRORS for '+sortcriteria+' QA/QC since '+dateafter+'</H1>Please fix all errors listed below. This report is running the following tests:<UL><LI>polygon was created<LI>observation is not in TEMPORARY project<LI>gross area is calculated<LI>either net area or percent cover recorded<LI>plant count recorded<LI>mechanical method set if manually treated<LI>percent treated recorded if mechanical or chemical method set</UL>'
        html_content+='<TABLE PADDING="3" BORDER="1"><TR><TH>ID</TH><TH>Date</TH><TH>Observer</TH><TH>Taxon</TH><TH>Project</TH><TH>Polygon</TH><TH>Area</TH><TH>Plant Ct</TH><TH>Treatment Info</TH></TR>'   
        # loop through errors to create data in a table with links to calflora.org 
        for i,f in errors.items():
            # projects and polygons create 1 report, default option produces 1 report for each observer name so need to test match if other vars empty
            if prjID or polyID or obs==features[i].get('Observer'):
                html_content+='<TR><TD><A HREF="https://www.calflora.org/entry/poe.html#vrid='+i+'">'+i+'</A></TD><TD>'+features[i].get('Date_Time','-')+'</TD><TD>'+features[i].get('Observer','-')+'</TD><TD>'+features[i].get('Taxon','-')
                if i in verifies:
                    if verifies[i]['weedname']==True:
                        html_content+='<DIV STYLE="color:red">(taxon not in priority weed list)</DIV>'
                html_content+='</TD><TD>'+features[i].get('Project','-')
                if(errors[i]['project']):
                    html_content+='<DIV STYLE="color:red">Needs to be moved to different Project</DIV>'
                html_content+='</TD><TD>'
                if(errors[i]['polygon']):
                    html_content+='<DIV STYLE="color:red">Missing Polygon</DIV>'
                html_content+='</TD><TD>'
                if(errors[i]['gross']):
                    html_content+='<DIV STYLE="color:red">Missing Gross Area</DIV>'
                if(errors[i]['infested']):
                    html_content+='<DIV STYLE="color:red">Missing Net Area or % Cover</DIV>'
                html_content+='</TD><TD>'
                if(errors[i]['plantct']):
                    html_content+='<DIV STYLE="color:red">Missing Plant Count</DIV>'
                html_content+='</TD><TD>'
                if(errors[i]['Mechanical']):
                    html_content+='<DIV STYLE="color:red">Missing Mechanical Method</DIV>'
                if(errors[i]['PercTrt']):
                    html_content+='<DIV STYLE="color:red">Missing % Treated</DIV>'
                html_content+='</TD></TR>'
        # close html tags
        html_content+='</TABLE><H1>WARNINGS for '+sortcriteria+' QA/QC since '+dateafter+'</H1>These warnings may or may not need fixing. This report is running the following tests:<UL><LI>checking to see if record is in a history stack, if it is a new population than that is okay<LI>checking to see if taxon is on OC priority weed list - please ensure that weed names match version on the plant list. Warnings for plants not on the OC priority weed list can be ignored.</UL>'
        html_content+='<TABLE PADDING="3" BORDER="1"><TR><TH>ID</TH><TH>Date</TH><TH>Observer</TH><TH>Taxon</TH></TR>' 
        for i,f in verifies.items():
            if prjID or polyID or obs==features[i].get('Observer'):
                html_content+='<TR><TD><A HREF="https://www.calflora.org/entry/poe.html#vrid='+i+'">'+i+'</A>'
                if verifies[i]['unstacked']==True:
                    html_content+='<DIV STYLE="color:red">(not stacked)</DIV>'
                html_content+='</TD><TD>'+features[i].get('Date_Time','-')+'</TD><TD>'+features[i].get('Observer','-')+'</TD><TD>'+features[i].get('Taxon','-')
                if verifies[i]['weedname']==True:
                    html_content+='<DIV STYLE="color:red">(taxon not in priority weed list)</DIV>'
                html_content+='</TD></TR>' 
        html_content+='</TABLE></BODY></HTML>'

        # create file name based on criteria
        file_name_components = [
        'qaqc',
        f"plantlistId_{params['plantlistId']}" if 'plantlistId' in params else None,
        sortcriteria.replace(' ','-'),
        f"After{params['dateAfter'].replace('-', '')}" if 'dateAfter' in params else None,
        f"Before{params['dateBefore'].replace('-', '')}" if 'dateBefore' in params else None,
        f"{projectname.replace(' ', '-')}" if 'projectIds' in params else None,
        f"{polygonname.replace(' ', '-')}" if 'shapeID' in params else None   
        ]

        # Filter out None values, join the components and limit length for file name
        file_name = "_".join(component for component in file_name_components if component is not None)[:200]  # Truncate to avoid long file names
        savefile = f'{downloadpath}/{file_name}.html'
     
        # Save the data to the specified JSON file
        with open(savefile, 'w', encoding='utf-8') as html_file:
            html_file.write(html_content) 
        print(f"Data saved to {savefile}")

    if(prjID):
        buildreport(prjID)
    elif(polyID):
        buildreport(polyID)
    else:
        for obs in observers:
            buildreport(obs)

else:
    print(f"Error: {response.status_code}")

