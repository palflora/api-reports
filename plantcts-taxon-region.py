import json
import requests
import datetime
import re
import os
 
# report purpose
print('Summary of plants treated by year for each population in a region of a single taxon')
# Prompt the user for their API key
api_key = input("Please enter your Calflora-API-Key: ")
# OCP group ID =140
grpID=140

# create folder to save output files
if not os.path.exists('data'):
    os.mkdir('data')
downloadpath='data'

headers = {
    'accept': 'application/geo+json',
    'X-API-Key': api_key
}

# Get list of all regions
response = requests.get('https://api.calflora.org/searchPolygons', {}, headers=headers)
# Check if the request was successful
if response.status_code == 200:
    regionstouse={}
    polyID=""
    allregions=response.json()
    for p in allregions:
        if p["ugroup"]==grpID:
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

# Get taxon
url = 'https://api.calflora.org/plants'
taxonname=''
taxonmatches={}
while( not taxonname):
    if(len(taxonmatches)>0):
        print('POSSIBLE MATCHES:')
        for p in taxonmatches:
            print(taxonmatches[p])
    taxonstr=input("Please enter taxon name: ")
    params = {
        'orderBy': 'taxon',
        'county': 'ORA',
        'taxon': taxonstr
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        taxonmatches={}
        possiblematches = response.json()
        for p in possiblematches:
            if(p["taxon"]==taxonstr):
                taxonname=taxonstr
            else:
                taxonmatches[p["id"]]=p["taxon"]
    else:
        print(f"Error: {response.status_code}")

# fuction to address ranges and other text in number of plants field, convert to integer
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

# set parameters to get Calflora observation data
url = 'https://api.calflora.org/observations'
params = {
    'taxon': taxonname,    # filter either taxon or plantlistID 
    #'georef': 'a',                     # Access by others (a = published, c = obscured, r = private, z = unpublished)
    'maxResults': 0,                   # leave off for default (2000) or set to 0 for unlimited
    #'dateAfter': '2025-01-01',
    #'dateBefore': '2025-05-31',
    'csetId': '379', #define Column Set 136=OC Form 
    #'plantlistId': 'px3845',          # NROC 2023-27 Treatment Priority 1 & 2; filter either taxon or plantlistID 
    #'observer': '',
    #'myrec': 'true',                # Only My Records: only return records owned by the current user     
    'shapeId': polyID,           # 'shapeId' in Shape Editor or 'rid' in Calflora link
    'groupIds': grpID,
    #'projectIds': 'pr305,pr306,pr523,pr695,pr994,pr237,pr335,pr336,pr244,pr294,pr420,pr238,pr230,pr815,pr814,pr307,pr270,pr269,pr308',
    #'projectIds': prjID,
    #'includeGeometry': 'true',
    'formatResults': 'true'
}
# Querry observation data
response = requests.get(url, params=params, headers=headers)
# Check if the request was successful
if response.status_code == 200:
    data = response.json()
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
        #TODO: These column names don't match col set we're using
        features[item["id"]] = {
                "ID": item['id'],
                "Observer": item['properties'].get('Observer', None),                
                "Taxon": item['properties'].get('Taxon', None),
                "Common Name": item['properties'].get('Common Name', None),
                "Date_Time": item['properties'].get('Date / Time', None),
                "Infested Area Count": item['properties'].get('Infested Area Count', None),
                "Infested Area Units": item['properties'].get('Infested Area Units', None),
                "Distribution": item['properties'].get('Distribution', None),
                "Gross Area Count": item['properties'].get('Gross Area Count', None),
                "Gross Area Units": item['properties'].get('Gross Area Units', None),
                "Number of Plants": number_of_plants,
                "Percent Cover": item['properties'].get('Percent Cover', None),                
                "Manual Treatment": item['properties'].get('Manual Treatment?', None),
                "Mechanical Method": item['properties'].get('Mechanical Method', None),
                "Chemical Method": item['properties'].get('Chemical Method', None),
                "Treatment Notes": treatment_notes,  # Updated Treatment Notes
                "Percent Treated": item['properties'].get('Percent of Population Treated', None),
                "Project": item['properties'].get('Project', None),
                "Region": item['properties'].get('Region', None),
                "Root": item['properties'].get('Root', item['id']),
                "Reference Polygon": item['properties'].get('Reference Polygon', item['id']),
                "Latitude": item['geometry']['coordinates'][0][1] if item['geometry']['type'] == 'Polygon' else item['geometry']['coordinates'][1],
                "Longitude": item['geometry']['coordinates'][0][0] if item['geometry']['type'] == 'Polygon' else item['geometry']['coordinates'][0]            
        }
    # class to build a nested dictionary
    class AutoDict(dict):
        def __missing__(self, k):
            self[k] = AutoDict()
            return self[k]
    # create set of unique years
    years=set()
    # nested dictionary of years where a population was mapped
    yearswdata= AutoDict()
    # nested dictionary of plant counts by root ID and year
    ## Treated counts summed up
    popct_treat=AutoDict()
    ## non-treated counts (largest in a year)
    popct_nt=AutoDict()
    ## all population IDs
    pops_all=set()
    for i,f in features.items():
            if len(f["Date_Time"])==10:
                yr=datetime.datetime.strptime(f["Date_Time"], '%Y-%m-%d').year
            else:
                yr=datetime.datetime.strptime(f["Date_Time"], '%Y-%m-%d %H:%M:%S').year
            rootid=f["Root"] or f["ID"]
            years.add(yr)
            pops_all.add(rootid)
            if(f['Chemical Method'] or f['Manual Treatment']):
                treatment=True
            else:
                treatment=False
            # print(str(treatment)+' '+str(f["ID"])+' '+str(rootid) + ' ' +str(yr) + ': ' +str(f["Number of Plants"]))
            # for treatment records add them all for the year
            if(treatment):
                yearswdata[rootid][yr]['trt']=True
                if rootid in popct_treat and yr in popct_treat[rootid]:
                    print('...summing')
                    if f["Number of Plants"]:
                        popct_treat[rootid][yr]=popct_treat[rootid][yr]+f["Number of Plants"]
                elif f["Number of Plants"] or f["Number of Plants"]==0:
                    popct_treat[rootid][yr]=f["Number of Plants"]
            else:
                yearswdata[rootid][yr]['nt']=True
                if rootid in popct_nt and yr in popct_nt[rootid]:
                    if f["Number of Plants"] and f["Number of Plants"] > popct_nt[rootid][yr]:
                        popct_nt[rootid][yr]=f["Number of Plants"]
                elif f["Number of Plants"] or f["Number of Plants"]==0:
                    popct_nt[rootid][yr]=f["Number of Plants"]
            # if no treatment report the largest plant count
            
    # start html file
    html_content='<HTML><HEAD></HEAD><BODY><H3>Total Plants Found by Population and Year for '+taxonname+' in '+polygonname +' ('+polyID+')</H3><BR>- = no data<BR>x = no plant count recorded<BR>treat = total of all plant counts for all treatment records that year<BR>nt = the max plant count recorded that year in an observation without treatment<BR><SPAN STYLE="background-color:lightgreen">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</SPAN> = year with no plants observed<TABLE PADDING="3" BORDER="1"><TR><TH>Root</TH><TH>Ref Poly</TH>'
    # sort years in order
    oyears=sorted(years)
    pops_todate=pops_treated=pops_monitored={}
    for y in oyears:
        html_content+='<TH COLSPAN="2">'+str(y)+'</TH>'
        pops_todate[y]=0
        pops_monitored[y]=0
        pops_treated[y]=0
    html_content+='</TR><TR><TH COLSPAN="2"></TH>';
    for y in oyears:
        html_content+='<TH>treat</TH><TH>nt</TH>'
    html_content+='</TR>'
    curryr=0
    # loop through totals to create data in a table with links to calflora.org 
    for i in pops_all:
        if(features.get(i, {}).get('Reference Polygon')):
            refpolygon='Y'
        else:
            refpolygon='<SPAN STYLE="color:red">N</SPAN>'
        html_content+='<TR><TD><A HREF="https://www.calflora.org/entry/poe.html#vrid='+str(i)+'">'+str(i)+'</A></TD><TD>'+refpolygon+'</TD>'
        for y in oyears:
            # start pops_todate with sum from last year as year changes
            if(y==curryr):
                pops_todate[y]+=pops_todate[curryr]
            elif curryr in pops_todate: 
                pops_todate[y]=pops_todate[curryr]
                curryr=y

            if(popct_treat[i].get(y)==0):
                if(str(popct_nt[i].get(y))=='None' or popct_nt[i].get(y)==0):
                    grncell='STYLE="background-color:lightgreen"'
            elif(popct_nt[i].get(y)==0):
                if(str(popct_treat[i].get(y))=='None' or popct_treat[i].get(y)==0):
                    grncell=' STYLE="background-color:lightgreen"'
            else:
                grncell=''
            html_content+='<TD'+grncell+'>'
            if(str(popct_treat[i].get(y))!='None'):
                html_content+=str(popct_treat[i].get(y))
                pops_treated[y]+=1
            elif yearswdata[i][y]['trt']:
                html_content+='x'
            else:
                html_content+='-'
            html_content+='</TD><TD'+grncell+'>'
            if(str(popct_nt[i].get(y))!='None'):
                html_content+=str(popct_nt[i].get(y))
            elif yearswdata[i][y]['nt']:
                html_content+='x'
            else:
                html_content+='-'
        html_content+='</TD></TR>'
    # show totals by year
    html_content+='<TR><TH COLSPAN="2">Total Pops</TH>'
    for y in oyears:
        html_content+='<TH COLSPAN="2">'+str(y)+' Treated Pops</TH>'
    html_content+='</TR><TR><TH COLSPAN="2">'+str(len(pops_all))+'</TH>'
    for y in oyears:
        html_content+='<TH COLSPAN="2">'+str(pops_treated[y])+'</TH>' 
    # close html tags
    html_content+='</TABLE></BODY></HTML>'

    # create file name based on criteria
    file_name_components = [
    'plantctsyr',
    f"{params['taxon'].replace(' ', '')}" if 'taxon' in params else None,
    f"plantlistId_{params['plantlistId']}" if 'plantlistId' in params else None,
    f"{params['observer']}" if 'observer' in params else None,
    f"After{params['dateAfter'].replace('-', '')}" if 'dateAfter' in params else None,
    f"Before{params['dateBefore'].replace('-', '')}" if 'dateBefore' in params else None,
    f"{params['projectIds'].replace(',', '')}" if 'projectIds' in params else None,
    f"{params['shapeId']}" if 'shapeId' in params else None,
    f"poly" if 'includeGeometry' in params else None    
]
    # Filter out None values, join the components and limit length for file name
    file_name = "_".join(component for component in file_name_components if component is not None)[:200]  # Truncate to avoid long file names
    savefile = f'{downloadpath}/{file_name}.html'
 
    # Save the data to the specified JSON file
    with open(savefile, 'w', encoding='utf-8') as html_file:
        html_file.write(html_content)
 
    print(f"Data saved to {savefile}")   
else:
    print(f"Error: {response.status_code}")