
import os,sys,json
import glob
import itertools

def process_fasta(fasta_file):
    sequences=dict()

    file_handle = open(fasta_file,'r')
    # alternate header and sequence
    fasta_iter = (x[1] for x in itertools.groupby(file_handle, lambda line: line[0] == ">"))
    for header in fasta_iter:
        # drop the ">"
        header = next(header)[1:].strip()

        # join all sequence lines to one.
        seq = "".join(s.strip() for s in next(fasta_iter))

        fasta_header=""
        try:
            fasta_header, fasta_description = header.split(' ', 1)
        except:
            fasta_header = header
            fasta_description = None

        seq = seq.upper()
        sequences[fasta_header]=seq

    return sequences

if(len(sys.argv)<2 or os.path.isdir(sys.argv[1]) is False):
    print("Takes one argument, the path to and including the curation folder")
    sys.exit()

cur_folder = sys.argv[1]
print("Parsing folder: "+cur_folder)

with open("../../../../Data/PlantSEED_v3/PlantSEED_Roles.json") as subsystem_file:
    roles_list = json.load(subsystem_file)

roles_dict=dict()
spontaneous_reactions=list()
for entry in roles_list:
    roles_dict[entry['role']]=entry
    if(entry['role'] == 'Spontaneous Reaction'):
        for reaction in entry['reactions']:
            if(reaction not in spontaneous_reactions):
                spontaneous_reactions.append(reaction)

############################################################
# As it stands, the data is now curated in multiple files:
# 1) The main pathway file: *-enzymes
# 2) Pathway flow, linking enzymes in succession: *-pathway-flow
# 3) Predicted genes as derived from protein families: *-predicted-genes
# 4) Fasta file containing protein sequences: *-fasta-files
# NB: At time of writing we will integrate pathway-flow at another date

############################################################
# Here we collect the predicted gene identifiers
predicted_genes_dict=dict()
search_path = os.path.join(cur_folder,"*-predicted-genes")
for predgenes_file in glob.glob(search_path):
    with open(predgenes_file) as predgenes_file_handle:
        for line in predgenes_file_handle.readlines():
            line=line.strip('\r\n')
            (gene,prediction,psi)=line.split('\t')
            gene = "Uniprot||"+gene
            #print(gene)
            if(gene not in predicted_genes_dict):
                predicted_genes_dict[gene]=dict()
            predicted_genes_dict[gene][prediction]=psi

############################################################
# Here we collect the protein sequences
protein_sequences_dict=dict()
search_path = os.path.join(cur_folder,"*-fasta-files")
for protseq_file in glob.glob(search_path):
    protein_sequences_dict = process_fasta(protseq_file) #protseq_dict
    print(protein_sequences_dict)
    updated_protein_sequences_dict = dict()
    for fasta_ID in protein_sequences_dict:
        uniprot_ID = fasta_ID.split('|')[1]
        uniprot_ID = "Uniprot||"+uniprot_ID
        print(fasta_ID,fasta_ID.split('|'),fasta_ID.split('|')[1],uniprot_ID)
        updated_protein_sequences_dict[uniprot_ID]=protein_sequences_dict[fasta_ID]
    print(updated_protein_sequences_dict)
        #del(protein_sequences_dict[fasta_ID])
############################################################
# Here we process the main pathway file
search_path = os.path.join(cur_folder,"*-enzymes")
for pwy_file in glob.glob(search_path):
    with open(pwy_file) as pwy_file_handle:
        for line in pwy_file_handle.readlines():
            line=line.strip('\r\n')
            (rxn,role,ftr,pub,ss,cls,pwy,loc)=line.split('\t')

            new_role = False
            if(role not in roles_dict):
                new_role = True
            elif(role == 'Spontaneous Reaction'):
                if(rxn not in spontaneous_reactions):
                    new_role = True

            if(new_role is True):
                new_role = {'role':'',
                            'include':True,
                            'subsystems':[],
                            'classes':{},
                            'features':[],
                            'reactions':[],
                            'localization':{},
                            'publications':[],
                            'predictions':{},
                            'sequences':{}}

                ####################################
                # Add function
                new_role['role']=role

                ####################################
                # Add subsystem and class
                class_dict=dict()
                for entry in ss.split('||'):
                    new_role['subsystems'].append(entry)
                    class_dict[entry]=[]

                    # If MetaCyc Pathway defined
                    if(pwy != ""):
                        class_dict[entry].append(pwy)

                new_role['classes'][cls]=class_dict

                ####################################
                # Add reaction
                new_role['reactions'].append(rxn)

                ####################################
                # Add genes
                if(ftr != ""):
                    for entry in ftr.split(';'):
                        new_role['features'].append(entry)

                ####################################
                # Add publications
                if(pub != ""):
                    for entry in pub.split(','):
                        new_role['publications'].append(entry)

                ####################################
                # Add localization
                for entry in loc.split(';'):
                    loc_dict=dict()
                    cpt=entry
                    #if protein localization data used
                    if(':' in entry):
                        pass
                        #(cpt,gene,sources)=entry.split(':')
                        #loc_dict[gene]=sources.split('|')
                    #assumed reaction compartment
                    else:
                        loc_dict[rxn]=[]

                    new_role['localization'][cpt]=loc_dict

                ####################################
                # Add predictions
                for ftr in new_role['features']:
                    print(ftr)
                    if(ftr in predicted_genes_dict):
                        print(ftr)
                    # you need to add the predicted genes and their PSI to
                    # the new_role['predictions'] dict
                    # there's a hint on how to do it in the 'Add sequences' below
                    # But you need to add "Uniprot||" to the ftr to make a match
                        new_role['predictions'][ftr]=predicted_genes_dict[ftr]
                        #pass

                ####################################
                # Add sequences
                for ftr in new_role['features']:
                    print(ftr)
                    if(ftr in updated_protein_sequences_dict):
                        print("match")
                        print(ftr)
                        # NB: in it's current state, this won't happen
                        # can you figure out why?
                        new_role['sequences'][ftr]= updated_protein_sequences_dict[ftr] #protseq_dict[ftr]

                roles_list.append(new_role)

with open('../../../../Data/PlantSEED_v3/PlantSEED_Roles.json','w') as new_subsystem_file:
    json.dump(roles_list,new_subsystem_file,indent=4)
# print(json.dumps(roles_list,indent=4))
