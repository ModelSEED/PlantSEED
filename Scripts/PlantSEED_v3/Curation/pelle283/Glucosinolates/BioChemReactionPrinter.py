
#Program takes in string input, searches PlantSEED_Roles.json which is located in PlantSEED/Data/PlantSEED_v3
# for example Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38) 
#print out the list of reactions associated with the role

import os
import json
from pathlib import Path

dataBase = "/home/tesse044/Bio_Research/PlantSEED/Data/PlantSEED_v3/PlantSEED_Roles.json"
#path to PlantSEED_Roles.json file


def find_reaction(ec_num, plant_json):
#function that will find the reactions associated with an enzyme and then return it
    reaction_info = []
    found = False
    with open(plant_json, 'r') as openfile:
        content = json.load(openfile)
        for info in content: 
            for item in info:
                if item == ("role"):
                    if ec_num in info[item]:
                        print(ec_num)
                        found = True
                if item == ("reactions") and found == True :
                    start_index = item.find("reactions")
                    size = len(item)
                    #while (curr != "localization"):
                    for i in range (size-1):
                        reaction_info.append(info[item][start_index])
                        start_index += 1
                    found = False
                    
    if reaction_info:
        return reaction_info
            #list of enzyme reactions if present in plantseed json file
    else:
        return "ec reaction not found"
    #if code gets to this point, it means that ec reaction was not found in dataBase             

if __name__ == "__main__": 
    search_target = input("Enter the name or ec number of enzyme: ")
    print(find_reaction(search_target, dataBase))



            




    
