#!/usr/bin/env perl
use strict;
use warnings;
use JSON;
my @temp=();
my @Headers=();

my $Biochemistry_Root = $ENV{SEAVER_PROJECT}."ModelSEEDDatabase/Biochemistry/";
open(FH, "< ".$Biochemistry_Root."reactions.master.tsv");
undef(@Headers);
my %Biochem_Rxns=();
while(<FH>){
    chomp;
    if(scalar(@Headers)==0){
	@Headers = split(/\t/,$_);
	next;
    }
    my %RowObject=();
    my @array = split(/\t/,$_,-1);
    for(my $i=0;$i<scalar(@array);$i++){
	$RowObject{$Headers[$i]}=$array[$i];
    }
    $Biochem_Rxns{$RowObject{id}}=\%RowObject;
}
close(FH);

open(FH, "< ".$Biochemistry_Root."compounds.master.tsv");
undef(@Headers);
my %Biochem_Cpds=();
while(<FH>){
    chomp;
    if(scalar(@Headers)==0){
	@Headers = split(/\t/,$_);
	next;
    }
    my %RowObject=();
    my @array = split(/\t/,$_,-1);
    for(my $i=0;$i<scalar(@array);$i++){
	$RowObject{$Headers[$i]}=$array[$i];
    }
    $Biochem_Cpds{$RowObject{id}}=\%RowObject;
}
close(FH);

open(FH, "< Plastidial_SandBox_Media.txt");
my %Media_Transporters=();
my $New_Rxn_ID="rxn5000";
my $Rxn_Count=0;
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    next if $temp[0] eq "id";
    my $mediacpd = $temp[0];

    my $Found_Transporter = "";
    foreach my $rxn ( sort grep { defined($Biochem_Rxns{$_}{is_transport}) && $Biochem_Rxns{$_}{is_transport}==1 } keys %Biochem_Rxns ){
	if($Biochem_Rxns{$rxn}{stoichiometry} =~ /${temp[0]}/){
	    @temp=split(/;/,$Biochem_Rxns{$rxn}{stoichiometry});
	    my %Cpds = ();
	    foreach my $item (@temp){
		my ($coeff,$cpd,$cpt,$idx,$name)=split(/:/,$item);
		$Cpds{$cpd}=1;
	    }
	    if(scalar(keys %Cpds != 0) && scalar( grep { $_ ne $mediacpd } keys %Cpds )==0){
		$Found_Transporter=$rxn;
		last;
	    }
	}
    }
    if($Found_Transporter){
	$Media_Transporters{$mediacpd}=$Found_Transporter;
    }else{
	$Media_Transporters{$mediacpd}=$New_Rxn_ID.$Rxn_Count;
	$Rxn_Count++;
    }
}
close(FH);

#Load /homes/seaver/Projects/
open(FH, "< ".$ENV{SEAVER_PROJECT}."PlantSEED_v2_WorkRepo/Core_Plant_Metabolism/ProbModelSEED/PlantSEED_Subsystems.json");
my $JSON="";
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);

#Energy  Photosystem_I   PWY-101
#Energy  Photosystem_II  PWY-101
#Energy  F0F1-type_ATP_synthase_in_plants_(plastidial)   PWY-6126
#Central Carbon  Pentose_phosphate_pathway_in_plants     OXIDATIVEPENT-PWY
#Central Carbon  Pentose_phosphate_pathway_in_plants     NONOXIPENT-PWY
#Central Carbon  Calvin-Benson-Bassham_cycle_in_plants   CALVIN-PWY
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   GLYSYN-ALA-PWY
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   GLYSYN2-PWY
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   PWY0-1021
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   ALANINE-SYN2-PWY
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   SERSYN-PWY
#Amino acids     Alanine,_serine,_glycine_metabolism_in_plants   PWY-6196
#6 subsystems and 11 pathways

my %SandBox_Subsystems=(#"Amino acids: Alanine,_serine,_glycine_metabolism_in_plants"=>["GLYSYN-ALA-PWY","GLYSYN2-PWY","PWY0-1021","ALANINE-SYN2-PWY","SERSYN-PWY","PWY-6196"],
			"Central Carbon: Calvin-Benson-Bassham_cycle_in_plants"=>["CALVIN-PWY"],
#			"Central Carbon: Pentose_phosphate_pathway_in_plants"=>["OXIDATIVEPENT-PWY","NONOXIPENT-PWY"],
#			"Energy: F0F1-type_ATP_synthase_in_plants_(plastidial)"=>["PWY-6126"],
#			"Energy: Photosystem_I"=>["PWY-101"],
#			"Energy: Photosystem_II"=>["PWY-101"]);
    );
my %PlantSEED_Subsystems = %{from_json($JSON)};
my %Plastidial_Reactions = ();
foreach my $ss (sort keys %{$PlantSEED_Subsystems{subsystems}}){
    next unless exists($SandBox_Subsystems{$ss});
    foreach my $ss_rxn (@{$PlantSEED_Subsystems{subsystems}{$ss}}){
	$Plastidial_Reactions{$ss_rxn->[0]}{$ss}=1;
    }
}

open(FH, "< Athaliana_FBAModel.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);

my $PlantSEED_Model = from_json($JSON);

my %SdBx_Rxns = ();
my %CytRxns = ();
foreach my $mdlrxn (@{$PlantSEED_Model->{modelreactions}}){
    my %RgtCpts=();
    foreach my $rgt (@{$mdlrxn->{modelReactionReagents}}){
	$rgt->{modelcompound_ref} =~ /_(\w)0$/;
	$RgtCpts{$1}=1;
    }
#    next unless exists($RgtCpts{d});
    
    my $Base_ID = $mdlrxn->{id};
    $Base_ID =~ s/_\w\d$//;
    next unless exists($Plastidial_Reactions{$Base_ID});

    if(!exists($RgtCpts{d})){
	$CytRxns{$Base_ID}{join("",sort keys %RgtCpts)}=1;
    }else{
	$SdBx_Rxns{$mdlrxn->{id}}=1;
    }
#    print $mdlrxn->{modelcompartment_ref},"\t",join("",sort keys %RgtCpts),"\n";
}

my $Bio_Ref = "kbase/plantdefault_obs";
my $Genome_Ref="/plantseed/plantseed/Athaliana-TAIR10/genome||";
my $Template_Ref="/chenry/public/modelsupport/templates/plant.modeltemplate||";
my %ModelObject = ("id"=>"Plastidial_SandBox_Model",
		   "source"=>"PlantSEED",
		   "source_id"=>"PlantSEED",
		   "name"=>"Plastidial_SandBox_Model",
		   "type"=>"GenomeScale",
		   "genome_ref"=>$Genome_Ref,
		   "template_ref"=>$Template_Ref,
		   "gapfillings"=>[],
		   "gapgens"=>[],
		   "biomasses"=>[],
		   "modelcompartments"=>[],
		   "modelcompounds"=>[],
		   "modelreactions"=>[]);

foreach my $cpt (['e','extracellular'],['d','plastid']){
    my %CptObject = ( id => $cpt->[0]."0", label => $cpt->[1]."_0",
		       compartment_ref => $Template_Ref."/compartments/id/".$cpt->[0],
		       compartmentIndex => 0, pH => 7, potential => 0 );
    push(@{$ModelObject{modelcompartments}},\%CptObject);
}
close(FH);

my %SdBx_Cpts=();
my %SdBx_Cpds=();
foreach my $mdlrxn ( grep { exists($SdBx_Rxns{$_->{id}}) } @{$PlantSEED_Model->{modelreactions}} ){

    foreach my $rgt (@{$mdlrxn->{modelReactionReagents}}){
	@temp=split(/\//,$rgt->{modelcompound_ref});
	my $mdlcpd = $temp[$#temp];
	$SdBx_Cpds{$mdlcpd}=1;
	@temp=split(/_/,$mdlcpd);
	my $mdlcpt = $temp[$#temp];
	$SdBx_Cpts{$mdlcpt}=1;
    }

    foreach my $prot (@{$mdlrxn->{modelReactionProteins}}){
	#Need to fix feature_ref
	my $subunit = $prot->{modelReactionProteinSubunits}[0];
#	print join("\n",@{$subunit->{feature_refs}}),"\n";
    }

    $mdlrxn->{reaction_ref} = $Template_Ref."/reactions/id/".$mdlrxn->{id};
    $mdlrxn->{reaction_ref} =~ s/\d$//;
    push(@{$ModelObject{modelreactions}},$mdlrxn);
}

foreach my $mdlcpd ( grep { exists($SdBx_Cpds{$_->{id}}) } @{$PlantSEED_Model->{modelcompounds}} ){
    $mdlcpd->{compound_ref} = $Template_Ref."/compounds/id/".$mdlcpd->{id};
    $mdlcpd->{compound_ref} =~ s/_\w\d$//;
    push(@{$ModelObject{modelcompounds}},$mdlcpd);
}

#Need to add biomass
my $SdBx_Biomass = { "id" => "bio1", "name" => "Plastidial biomass", "removedcompounds" => [],
		     "lipid" => 0, "protein" => 0, "cellwall" => 0, "other" => 0, "energy" => 0, "rna" => 0, "cofactor" => 0, "dna" => 0,
		     "biomasscompounds" => [{"modelcompound_ref" => "~/modelcompounds/id/cpd00102_d0",
					     "gapfill_data" => {},
					     "coefficient" => -1.0}
#					    {"modelcompound_ref" => "~/modelcompounds/id/cpd11416_d0",
#					     "gapfill_data" => {},
#					     "coefficient" => 1.0}
			 ] };
push(@{$ModelObject{biomasses}},$SdBx_Biomass);

open(SS, "> Plastidial_SandBox_Subsystems.txt");
print SS "Subsystem\tAraCyc Pathways\tReactions\n";
foreach my $ss (sort keys %SandBox_Subsystems){
    print SS $ss,"\t",join(", ",sort @{$SandBox_Subsystems{$ss}}),"\t";
    print SS join(", ", grep { exists($Plastidial_Reactions{$_}{$ss}) } keys %Plastidial_Reactions),"\n";
}
close(SS);

open(RXN, "> Plastidial_SandBox_Reactions.txt");
print RXN "Reaction\tEquation\tProteins\n";
my %Global_Ftrs=();
foreach my $sdbx_rxn ( grep { exists($SdBx_Rxns{$_->{id}}) } @{$PlantSEED_Model->{modelreactions}} ){
    my $Base_ID = $sdbx_rxn->{id}; $Base_ID =~ s/_\w\d$//;

    my %Ftrs=();
    foreach my $prot (@{$sdbx_rxn->{modelReactionProteins}}){
	#Need to fix feature_ref
	my $subunit = $prot->{modelReactionProteinSubunits}[0];
	my @New_FtrRefs=();
	foreach my $ftr_ref (@{$subunit->{feature_refs}}){
	    @temp = split(/\//,$ftr_ref);
	    my $ftr = $temp[$#temp];
	    $Ftrs{$ftr}=1;
	    $Global_Ftrs{$ftr}=1;
	    my $new_ftr_ref = "~/genome/features/id/".$ftr;
	    push(@New_FtrRefs,$new_ftr_ref);
	}
	$subunit->{feature_refs}=\@New_FtrRefs;
    }
    my $Eq = $Biochem_Rxns{$Base_ID}{definition};
    $Eq =~ s/\[0\]//g;
    print RXN $Base_ID,"\t",$Biochem_Rxns{$Base_ID}{definition},"\t",join(", ",sort keys %Ftrs),"\n";
}
close(RXN);

open(TRN, "> Plastidial_SandBox_Transporters.txt");
print TRN "Reaction\tEquation\n";
foreach my $mediacpd (sort keys %Media_Transporters){

    if(!exists($SdBx_Cpds{$mediacpd."_d0"})){
	print $mediacpd."_d0\n";
	next;
    }

    #Add e0 cpds and check for d0 cpds
    my $mediacpdObject = { "id" => $mediacpd."_e0",
			   "name" => $Biochem_Cpds{$mediacpd}{name},
			   "charge" => $Biochem_Cpds{$mediacpd}{charge}+0,
			   "compound_ref" => $Template_Ref."/compounds/id/".$mediacpd,
			   "formula" => $Biochem_Cpds{$mediacpd}{formula},
			   "modelcompartment_ref" => "~/modelcompartments/id/e0",
			   "aliases" => []};
    push(@{$ModelObject{modelcompounds}},$mediacpdObject);

    my $modeltransporter = {"reaction_ref" => $Template_Ref."/reactions/id/".$Media_Transporters{$mediacpd}."_d",
			    "id" => $Media_Transporters{$mediacpd}."_d0", "name"=> $Biochem_Cpds{$mediacpd}{name}." transport",
			    "modelReactionProteins" => [],"probability" => 0,"aliases" => [],"gapfill_data" => {},"protons" => 0,
			    "direction" => "=","modelcompartment_ref" => "~/modelcompartments/id/d0",
			    "modelReactionReagents" => [{"coefficient" => -1,
							 "modelcompound_ref" => "~/modelcompounds/id/".$mediacpd."_d0"},
							{"coefficient" => 1,
							 "modelcompound_ref" => "~/modelcompounds/id/".$mediacpd."_e0"}]};

    if($Media_Transporters{$mediacpd} =~ /rxn5/){
	$modeltransporter->{reaction_ref}=$Template_Ref."/reactions/id/rxn00000_c";
    }
			    
    push(@{$ModelObject{modelreactions}},$modeltransporter);
}

open(OUT, "> PMS_Plastidial_SandBox_Model.json");
print OUT to_json(\%ModelObject, {pretty=>1,ascii=>1});
close(OUT);

open(FH, "< Athaliana_Genome.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);
my $Ath_Genome = from_json($JSON);
my %Ath_Ftrs = map { $_->{id} => $_ } @{$Ath_Genome->{features}};

open(FH, "< SandBox_Skeleton_Genome.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);
my $Genome = from_json($JSON);

open(FH, "< /Users/seaver/Projects/PlantSEED_Repo/DBs/PlantSEED_Roles_UpdatedFtrs.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);
my $Annotation = from_json($JSON);
my %Roles_Subsystems=();
foreach my $role (@{$Annotation}){
    foreach my $ss (keys %{$role->{subsystems}}){
	$Roles_Subsystems{$role->{role}}{$ss}=1;
    }
}

my $minimal_genome = {};
$minimal_genome->{id}=$Genome->{id};
$minimal_genome->{source}=$Genome->{source};
$minimal_genome->{scientific_name} = $Genome->{scientific_name};
$minimal_genome->{taxonomy} = $Genome->{taxonomy};
$minimal_genome->{domain}="Plant";
$minimal_genome->{features}=[];

foreach my $ftr (sort keys %Global_Ftrs){
    my $ftrObj = $Ath_Ftrs{$ftr};

    my $minimal_ftr = {id => $ftr,
		       function => $ftrObj->{function},
		       subsystems => []};
    push(@{$minimal_genome->{features}},$minimal_ftr);
    push(@{$Genome->{features}},$ftrObj);
}

foreach my $ftr (@{$minimal_genome->{features}}){
    my %SSs = ();
    foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$ftr->{function})){
	foreach my $ss (keys %{$Roles_Subsystems{$role}}){
	    $SSs{$ss}=1;
	}
    }
    $ftr->{subsystems}=[sort keys %SSs];
}

open(OUT, "> SandBox_Full_Genome.json");
print OUT to_json($Genome,{pretty=>2,ascii=>1});
close(OUT);

open(OUT, "> SandBox_Minimal_Genome.json");
print OUT to_json($minimal_genome,{pretty=>2,ascii=>1});
close(OUT);
