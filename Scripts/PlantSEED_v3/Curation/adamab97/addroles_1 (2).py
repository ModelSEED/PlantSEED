import json

control_file = open("choline_biosynth_loc_2", "r")
control_dict = {}
for line in control_file:
	stripped_line = line. strip()
	#print(stripped_line)
	#(key, val) = stripped_line. split('\t')
	my_list = stripped_line. split('\t')
	#print(stripped_line)
	#(key, val) = mylist[0], mylist[1:]
	#control_dict[key] = {mylist[1] : mylist[2]}	
	#control_dict[key] = {'source': mylist[1], 'location': mylist[2]}
	control_dict[my_list[2]]={my_list[1]:[my_list[3]]}
#print(control_dict)
control_file. close()


f = open('Plantseed_Roles.json')
data = json.load(f)
for my_entry in data:
	for my_location in my_entry['localization']:
		#print(my_location)
		if(my_location in control_dict):
			#for my_feature in control_dict[my_location]:
				#print(my_feature)
			# Get the feature AND the publication from control_dict that matches the location
			for my_feature, my_publication in control_dict[my_location].items():
				#print(my_feature, '->', my_publication)	
				#print(my_entry['features'])
				#print(my_feature,'->',my_entry['features'])
				#if (my_feature in my_entry['features']):
					#This will never be true by problem definition

			#print(control_dict[my_location])
					#print(my_location,":",control_dict[my_location])
				#else:
					# Can't get this to work...
					#my_entry['localization'] = {my_location : {my_feature : {my_publication}}}
					#my_entry['localization'][my_location] = "my_feature"
					#my_entry['localization'][my_location] = {my_feature : {my_publication}}
				print(my_location, ': {',my_feature, control_dict[my_location] )
				my_entry['localization'][my_location] = control_dict[my_location]
				print(my_entry['localization'])
				#print(my_location, ': {',my_feature, ': {', my_publication, '}}' )

			#print(control_dict[my_location].value) 
				#my_entry['localization'] = control_dict[my_location]
				#print(my_entry['localization'])
				#print(entry['features'][feature])
				#print(control_dict[feature])
				#entry['features'][feature] = control_dict[feature]
				#print(entry['features'][feature])
				#print(entry)

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
				
				#for(my_feature in control_dict[my_location]):
					#if(my_feature in my_entry[‘features’]):
				##	#print(source)
				##	print(data_dict[source])
					##print(entry['features'][feature]['source'])
					#entry['features'][feature]['source']={data_dict[source]:1}
				##	print(entry)
				#entry['features'][feature][control_dict[feature]['source']]={control_dict[feature]['location']:1}
#save json file

#with open ('Plantseed_Roles.json','w') as out_file:
	#json.dump (data, out_file, indent=4)

#{'source':mylist[1], 'location': mylist[2]}
#data_dict=control_dict[feature]
