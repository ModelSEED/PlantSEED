import json

control_file = open("choline_biosynth_loc_2", "r")
control_dict = {}
for line in control_file:
	stripped_line = line. strip()
	my_list = stripped_line. split('\t')
	control_dict[my_list[1]]={'role':my_list[0],'localization':my_list[2],'source':my_list[3]}

control_file. close()

f = open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json')
data = json.load(f)
for my_entry in data:
	for my_feature in my_entry['features']:
		if(my_feature in control_dict and control_dict[my_feature]['role'] == my_entry['role']):
			my_location = control_dict[my_feature]['localization']
			if(my_location in my_entry['localization']):
				print("Location already there: "+my_location)
			else:
				print("Location not there: "+my_location)
				my_entry['localization'][my_location] = {my_feature: [ control_dict[my_feature]['source'] ]}
			for entry_location in my_entry['localization']:
				print(my_entry['localization'][entry_location], entry_location, my_entry['role'])
	
with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json', 'w') as out_file:
	json.dump (data, out_file, indent=4)
