
#1/24/2025 Task Hlina Plan of Action
#open PlantSEED/Data and check all folders
#create a list of all E.C number values, search for each E.C and print out the reaction that is associated with that
#
#if not found, print E.C value __ not found

import os
from pathlib import Path

dataBase = "/home/tesse044/Bio_Research/PlantSEED/Data"
print(dataBase)
#directory to be opened and searched for enzyme with matching EC number

ec_values = ec_values = {
    "Step1": ["1.14.14.42", "1.14.14.40", "1.14.14.156", "1.14.13.237"],
    "Step2": ["1.14.14.43", "1.14.14.45"],
    "Step4": ["3.4.19.16"],
    "Step5": ["4.4.1.13", "2.4.1.195"],
    "Step6": ["EC 2.4.1.195"],
    "Step7": ["2.8.2.38", "2.8.2.24"]
}

#This is a dictionary of step keys with the ec nums as values of each key
#Additional comments about the ec values:
#EC 1.14.14.45 should be Phenolic and Indolic

def find_reaction(ec_num, dB):
#function that will find the reaction associated with an ec number and then return it
    for root, dirs, files, in os.walk(dB):
    #loop through dataBase
        for directory in dirs:
            find_reaction(ec_num, os.path.join(root, directory))
            for file in files:
                with open(os.path.join(root, dB)) as f:
                    content = f.read()
                    if (ec_num in content) and ("reactions" in content) and ("role" in content):
                    #if ec_num is found, search for its reaction and return it
                        start_index = content.find("role")
                        end_index = content.find("pathways")
                        reaction_info = content[start_index:end_index]
                        return reaction_info
                #sub string with role of enzyme info and reaction info is returned
                
    return "ec reaction not found"
    #if code gets to this point, it means that ec reaction was not found in dataBase

for stepKey in ec_values:
    print(stepKey + " result: ")
    for value in stepKey:
        print(find_reaction(value, dataBase) + "\n")
#for loop goes through ec values and prints results determined by find_reaction function


#updated TO-DO:
#find_reaction function is doing too much work, must split into smaller tasks
#need one function to go thru dataBase to open and check for directores
#said function needs to return a list of files with their paths
#second additional function needs to go through the list of file paths to find the wanted ec number




            




    
