import json

control_file = open("central_carbon_publications", "r")
control_dict = {}
for line in control_file:
	stripped_line = line. strip()
	my_list = stripped_line. split('\t')
	control_dict[my_list[0]] = {'publication':my_list[1]}

control_file. close()

f = open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json')
data = json.load(f)
for my_entry in data:
	for my_feature in my_entry['features']:
		if(my_feature in control_dict): 
			my_jsonpub = my_entry['publications']
			my_addedpub = control_dict[my_feature]['publication']
			if my_addedpub not in my_jsonpub:
				my_jsonpub.append(my_addedpub)
			print(my_jsonpub)

with open ('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as out_file:
	json.dump (data, out_file, indent=4)
