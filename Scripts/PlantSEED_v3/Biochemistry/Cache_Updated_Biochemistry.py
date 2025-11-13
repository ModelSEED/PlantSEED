#!/usr/bin/env python
import datetime
import httpx
import time
import pickle
import copy
import os
import re
import json

def fetch_biochemistry_data(url: str, pattern: str, branch: str):
	
	# Set the branch via the 'ref' query parameter
	params = { "ref": branch }

	# Set up headers, including the token for authentication
	headers = { "Accept": "application/vnd.github.v3+json" }

	# Make the API request
	with httpx.Client() as client:
		try:
			response = client.get(url, headers=headers, params=params)
			response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
			directory_contents = response.json()
		except httpx.HTTPStatusError as e:
			print(f"Error fetching directory contents: {e}")
		except httpx.RequestError as e:
			print(f"An error occurred during the request: {e}")

	compiled_pattern = re.compile(pattern)
	data_dict=dict()
	with httpx.Client(headers=headers, follow_redirects=True) as client:
		for item in directory_contents:
			# Check if the item is a file AND its name matches the regex pattern
			if item.get("type") == "file" and compiled_pattern.match(item.get("name", "")):
				download_url = item["download_url"]
		
				try:
					# The download_url points to the raw file, so no special GitHub headers are needed, 
					# but the Authorization header might be.
					response = client.get(download_url)
					response.raise_for_status()
				
					# The content is a raw string (the JSON text)
					raw_content = response.text
				
					# Parse the JSON string into a Python object (dictionary or list)
					file_data = json.loads(raw_content)
					for entry in file_data:
						data_dict[entry['id']]=entry

				except httpx.HTTPStatusError as e:
					print(f"   - ❌ Failed to download {file_name} (HTTP Error: {e.response.status_code})")
				except json.JSONDecodeError:
					print(f"   - ❌ Failed to parse {file_name} as JSON.")
				except Exception as e:
					print(f"   - ❌ An unexpected error occurred with {file_name}: {e}")
				
	return data_dict

time_string = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh %Mm %Ss'))
print("Fetching biochemistry "+time_string)
############################
## Load Biochemistry
############################
FOLDER = "Biochemistry"
COMMITS_URL = f"https://api.github.com/repos/ModelSEED/ModelSEEDDatabase/commits"
CONTENTS_URL = f"https://api.github.com/repos/ModelSEED/ModelSEEDDatabase/contents/{FOLDER}"
MSD_BRANCH = "dev" # could be commit?
CACHE = "Cache"
if(os.path.isdir(CACHE) is False):
	os.mkdir(CACHE)

# --- Step 1: Check the /commits endpoint FIRST ---
# We set default headers for all requests in this client
headers = {
	'Accept': 'application/vnd.github+json',
	'User-Agent': 'My-ModelSEED-Downloader'
	# 'Authorization': 'Bearer YOUR_GITHUB_TOKEN' # See "Best Practices"
}

with httpx.Client(headers=headers) as client:
	print(f"Checking for new commits for Biochemistry...")
	try:
		# Query the commits, filtering by path
		params = {'path': FOLDER, 'per_page': 1, 'branch': MSD_BRANCH}
		r = client.get(COMMITS_URL, params=params)
		r.raise_for_status()  # Raise an exception for 4xx/5xx errors

		commit_list = r.json()
		if not commit_list:
			print(f"Error: No commits found for path '{PATH_IN_REPO}'.")

		else:
			# Get the *newest* commit (it's the first in the list)
			latest_commit = commit_list[0]
			new_sha = latest_commit['sha']
			new_timestamp_str = latest_commit['commit']['committer']['date']
			new_dt = datetime.datetime.fromisoformat(new_timestamp_str)
			
			print(f"Latest commit is {new_sha[:7]} from {new_dt.date()}")

	except httpx.HTTPStatusError as e:
		print(f"HTTP error occurred: {e.request.url} - {e.response.status_code}")
	except Exception as e:
		print(f"An error occurred: {e}")

	with open(CACHE+"/repo-state.json", 'w') as f:
		json.dump({'sha': new_sha, 'timestamp': new_timestamp_str}, f, indent=2)
    	
# reaction_pattern = r"^reaction_.*\.json$"
# reactions_dict = fetch_biochemistry_data(msd_base_url,reaction_pattern,msd_branch)

# Its important to use binary mode
# with open(CACHE+'/MS_Rxns.pickle', 'wb') as rfh:
# 	pickle.dump(reactions_dict,rfh)

# compound_pattern = r"^compound_.*\.json$"
# compounds_dict = fetch_biochemistry_data(msd_base_url,compound_pattern,msd_branch)
compounds_dict = dict()
for compound in compounds_dict:
	cpd_obj = compounds_dict[compound]

	# fix default values
	for key in ["charge","mass","deltag","deltagerr"]:
		if(cpd_obj[key] is None):
			cpd_obj[key] = 0.0

	if(cpd_obj['formula'] is None):
		cpd_obj['formula'] = 'R'

	template_compound_hash = { 'id':compound, 'name':cpd_obj["name"],
								'abbreviation':cpd_obj["abbreviation"], 'aliases':[],
								'formula':cpd_obj["formula"], 'isCofactor':0,
								'defaultCharge':float(cpd_obj["charge"]), 'mass':float(cpd_obj["mass"]),
								'deltaG':float(cpd_obj["deltag"]), 'deltaGErr':float(cpd_obj["deltagerr"]),
								'compound_ref':biochem_ref+"/compounds/id/"+cpd_obj['id'] }
	compounds_dict[compound]=template_compound_hash

# Its important to use binary mode
# with open(CACHE+'/MS_Cpds.pickle', 'wb') as cfh:
# 	pickle.dump(compounds_dict,cfh)

time_string = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh %Mm %Ss'))
print("Biochemistry cacheed "+time_string)