#!/bin/bash
for i in $(ws-listobj Phytozome_Genomes -t KBaseGenomes.Genome | grep Genome | awk '{print $2}')
do
    echo $i
    ws-copy $i $i -s Phytozome_Genomes -n PlantSEED_v3
done
