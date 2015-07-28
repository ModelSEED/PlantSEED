#Serves as a reminder of the order in which scripts should be run.
#Presumes that a fasta file has been downloaded

#0 Download PlantSEED Genomes
#  This only has to be done once
./Download_KBase_Genome_as_PATRIC_object.pl

#1 FASTA file has to be translated
#  No check implemented, assumes sequences are already nucleotide
#  Output files need to be re-named appropriately
./Translate_Nucleotide_Sequences.pl

#2 FASTA file has to be converted into genome object
./Convert_Fasta_to_PATRIC_object.pl

#3 Create appropriate directory in PATRIC workspace (if it doesn't exist)
./Create_PlantSEED_Genome_Dir.pl

#4 Upload Genome object
./Create_PlantSEED_Genome.pl

#5 Upload Minimal genome object
./Create_PlantSEED_Minimal_Genome.pl

#6 Blast fasta file against NR
#  NR found in /homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/DBs/
#  NR contains pegs identifiers
#  Script stores Qsub identifiers in Qsub_Genomes.txt
./Blast_Plant_Families.pl

#7 Plant PEG Identifiers are translated into the original identifiers for ease of use
./Translate_SEED_IDs_in_Blast_Results.pl

#7 Sims are expanded to include other plant/prokaryotic sims
#  The original NR used is a minimized version of important plant genes
#  And the original BLAST results are used to expand on these sims in a look-up table
<TBD>

#8 Sims are separated into multiple Sims files
#  The index of these objects are stored in the minimal genome
./Convert_Sims_into_JSONS.pl

#9 Sims are uploaded into the genome workspace directory
./Upload_Genome_Sims.pl <TBD>