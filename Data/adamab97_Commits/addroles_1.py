import json

control_file = open("choline_biosynth_loc", "r")
control_dict = {}
for line in control_file:
	stripped_line = line. strip()
	#print(stripped_line)
	#(key, val) = stripped_line. split('\t')
	mylist = stripped_line. split('\t')
	#print(stripped_line)
	#(key, val) = mylist[0], mylist[1:]
	key = mylist[0]
	#control_dict[key] = {mylist[1] : mylist[2]}	
	#control_dict[key] = {'source': mylist[1], 'location': mylist[2]}
	control_dict[key]= {mylist[1] : {mylist[2] :1}}

control_file. close()

#print(control_dict)

with open ('PlantSEED_Roles.json') as f:
	data = json.load(f)
	for entry in data:
		#print(entry)
		for feature in entry['features']:
			if(feature in control_dict):
				#print(entry['features'][feature])
				#print(control_dict[feature])
				entry['features'][feature] = control_dict[feature]
				#print(entry['features'][feature])
				print(entry)

				#print ('features')
				#print(feature)
				#print(entry)
				#print(entry['features'])
				#print(entry['features'][control_dict[feature]])
				#print(entry['features'][control_dict[feature]['source']])
				#print(entry['features'][feature])
				#print(control_dict[feature])
				##data_dict = control_dict[feature]
				#print(data_dict)
				##for source in data_dict:
				
				##	#print(source)
				##	print(data_dict[source])
					##print(entry['features'][feature]['source'])
					#entry['features'][feature]['source']={data_dict[source]:1}
				##	print(entry)
				#entry['features'][feature][control_dict[feature]['source']]={control_dict[feature]['location']:1}
#save json file

with open ('Plantseed_Roles.json','w') as out_file:
	json.dump (data, out_file, indent=4)

#{'source':mylist[1], 'location': mylist[2]}
#data_dict=control_dict[feature]
