
#Program takes in string input, searches PlantSEED_Roles.json which is located in PlantSEED/Data/PlantSEED_v3
# for example Aliphatic desulfoglucosinolate sulfotransferase (EC 2.8.2.38) 
#print out the list of reactions associated with the role

import os
import json
from pathlib import Path

dataBase = "/Users/pelle283/Documents/PlantSEED/Data/PlantSEED_v3/PlantSEED_Roles.json"
#path to PlantSEED_Roles.json file


def find_reaction(ec_num, plant_json):
#function that will find the reactions associated with an enzyme and then return it
    reaction_info = []
    found = False
    inDB = False
    fullName = ""
    with open(plant_json, 'r') as openfile:
        content = json.load(openfile)
        for info in content: 
            for item in info:
                if item == ("role"):
                    if ec_num in info[item]:
                       # print(ec_num + " this ec is in the info!")
                        fullName += info[item]
                        found = True
                        inDB = True
                if item == ("reactions") and found == True :
                    start_index = item.find("reactions")
                    for i in range (len(info[item])):
                        reaction_info.append(info[item][start_index])
                        start_index += 1
                    found = False
                    
    if (len(reaction_info)) > 0:
        print("Results for: " + ec_num)
        print(reaction_info) 
        print("NAME OF ENZYME AS IN DATA BASE: " + fullName +"\n")
            #list of enzyme reactions if present in plantseed json file
    else:
        if (inDB == False):
            print("The following ec " + ec_num + " is not in PlantSEED_Roles.json")
        else:
            print("The following ec " + ec_num + " is present in PlantSEED_Roles.json but no reactions are listed")
    #if code gets to this point, it means that ec reaction was not found in dataBase             

if __name__ == "__main__": 
    search_target = input("Enter the name or ec number of enzyme: ")
    find_reaction(search_target, dataBase)


    # print("Testing with all enzymes:\n")
    # ec_List = ["EC 1.14.14.42", "EC 1.14.14.40", "EC 1.14.14.156", "EC 1.14.14.43","EC 1.14.14.45",
    #  "EC 1.14.14.45","EC 3.4.19.16", "EC 4.4.1.13", "EC 2.4.1.195", "EC 1.14.13.237", "EC 2.8.2.24"]
    # for i in range (len(ec_List)):
    #     target = ec_List[i]
    #     print(find_reaction(target, dataBase))
    #result: EC 2.8.2.24 and EC 1.14.13.237 not found
    #true negative for EC 1.14.13.237, it is not in plantSEED_Roles.json
    #EC 2.8.2.24 is in plantSEED_Roles.json but no reactions listed for it




            




    
