
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


def data_files(dB, all_files):
    for entry in os.listdir(dB):
        full_path = os.path.join(dB, entry)
        #print(full_path)
        if os.path.isdir(full_path):
            data_files(full_path, all_files)
        else:
            all_files.append(full_path)
           # data_files(full_path, all_files)
    return all_files

#data_files returns Data directory as a list of files


def find_reaction(ec_num, fileList):
#function that will find the reaction associated with an ec number and then return it
    for files in fileList:
        f = open(files, "r")
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

data = []
data_files(dataBase, data)
for stepKey, ec_nums in ec_values.items():
    print(stepKey + " result: ")
    for value in ec_nums:
        print(find_reaction(value,data ) + "\n")

#for loop goes through ec values and prints results determined by find_reaction function






            




    
