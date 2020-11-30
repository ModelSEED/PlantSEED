#!/usr/bin/env python
import sys,json,re,os

Root_Class="Central_Carbon"
Subsystems=["AcetylCoA","Calvin","Glycolysis",
            "Pentose","RubiscoShunt","Photores","TCA"]

gene_publications=dict()
for ss in Subsystems:
    for dir_tuple in os.walk(Root_Class+"/"+ss):
        if('Done' in dir_tuple[0]):
            for gene_file in dir_tuple[2]:
                with open(dir_tuple[0]+'/'+gene_file) as gfh:
                    for line in gfh.readlines():
                        line=line.strip()
                        if(line == ""):
                            continue
                        array=line.split('\t')
                        if(array[0] not in gene_publications):
                            gene_publications[array[0]]=list()
                        gene_publications[array[0]].append(array[1])
