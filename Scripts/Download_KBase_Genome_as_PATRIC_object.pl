#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();

#######################################################
#Initialization
#######################################################

use Bio::KBase::Auth;
my $AToken = Bio::KBase::Auth::GetConfigs()->{token};

use Bio::KBase::workspace::Client;
my $WSClient = Bio::KBase::workspace::Client->new('https://kbase.us/services/ws');
$WSClient->{token} = $AToken;
$WSClient->{client}->{token} = $AToken;

#######################################################
#List Genomes
#######################################################
my $Workspace = "PlantSEED";

open(SUM, "> PlantSEED_Summary.txt");
print SUM "PATRIC ID\tScientific name\t# Features\n";
foreach my $genome_info (@{$WSClient->list_objects({workspaces=>[$Workspace],type=>"KBaseGenomes.Genome"})}){
    my $kbase_genome = $WSClient->get_object({workspace=>$Workspace,id=>$genome_info->[1],type=>"KBaseGenomes.Genome"});
    next if $genome_info->[1] !~ /PlantSEED/;

    #Generate PATRIC Genome ID from original PlantSEED files
    #Retrieve species name
    open(FH, "< /vol/public-pseed/FIGdisk/FIG/Data/Organisms/".$kbase_genome->{data}{source_id}."/GENOME");
    my $Full_name = <FH>;
    chomp($Full_name);
    @temp=split(/\s+/, $Full_name);
    close(FH);

    my $Species_name = substr($temp[0],0,1).$temp[1];

    #Retrieve species version
    open(FH, "< /vol/public-pseed/FIGdisk/FIG/Data/Organisms/".$kbase_genome->{data}{source_id}."/PROJECT");
    my $Project_String = <FH>;
    $Project_String =~ /assembly version ([\w\.]+),/;
    my $Species_version = $1;
    close(FH);

    #Retrieve taxonomy
    open(FH, "< /vol/public-pseed/FIGdisk/FIG/Data/Organisms/".$kbase_genome->{data}{source_id}."/TAXONOMY");
    my $Taxonomy = <FH>;
    chomp $Taxonomy;
    close(FH);

    my $PATRIC_ID = $Species_name."-".$Species_version;

    #Initial copy of object
    my $patric_genome = $kbase_genome->{data};
    $patric_genome->{id}=$PATRIC_ID;
    $patric_genome->{source}="PlantSEED";
    $patric_genome->{scientific_name} = $Full_name;
    $patric_genome->{taxonomy} = $Taxonomy;
    print SUM $PATRIC_ID."\t".$patric_genome->{scientific_name}."\t".scalar(@{$patric_genome->{features}}),"\n";

    open(OUT, "> Feature_Aliases/".$PATRIC_ID.".txt");
    foreach my $ftr (@{$patric_genome->{features}}){
	delete $ftr->{feature_creation_event};

	my $PubSEED_ID = $ftr->{id};

	#Attempting to retrieve original gene id, there was no inherent order in how these were stored in PubSEED
	my $Gene_ID = ( grep { $_ !~ /(CDS\.?\d*$)|(_transcript$|\.transcript$|\.\d$|\.t\d+$|_T\d+$)/ } @{$ftr->{aliases}})[0];

	#Some A. lyrata gene ids need fixing
	if(!$Gene_ID && $PATRIC_ID eq "Alyrata-v.1.0"){
	    $Gene_ID = ( grep { $_ !~ /(CDS\.?\d*$)|(_transcript$|\.transcript$|\.t\d+$|_T\d+$)/ } @{$ftr->{aliases}})[0];
	}

	my $Transcript_ID = ( grep { $_ =~ /${Gene_ID}/ && $_ ne $Gene_ID && $_ !~ /CDS/ } @{$ftr->{aliases}} )[0];

	#Some chlamy, rice, maize, A. lyrata transcripts are slightly different
	if(!$Transcript_ID && ($PATRIC_ID =~ /^(Creinhardtii-v3\.0|Alyrata-v\.1\.0|Osativa-MSU6|Zmays-AGPv2)$/)){
	    $Transcript_ID = ( grep { $_ ne $Gene_ID && $_ !~ /CDS/ } @{$ftr->{aliases}} )[0];
	}
	
	#Grape gene/transcript identifiers need to be modified slightly to fit public sources
	if($PATRIC_ID eq "Vvinifera-IGGP_12x.txt"){
	    $Gene_ID =~ s/^Vv/VIT_/;
	    $Transcript_ID =~ s/^Vv/VIT_/;
	}

	#Fixing ids and aliases
	$ftr->{id} = $Gene_ID;
	$ftr->{aliases} = [$Gene_ID,$Transcript_ID,$PubSEED_ID];

	print OUT $PubSEED_ID,"\t",$Gene_ID,"\t",$Transcript_ID,"\n";

	if (defined($ftr->{protein_translation})) {
	    $ftr->{protein_translation_length} = length($ftr->{protein_translation});
	    $ftr->{dna_sequence_length} = 3*$ftr->{protein_translation_length};
	    $ftr->{md5} = Digest::MD5::md5_hex($ftr->{protein_translation}),
	    $ftr->{publications} = [],
	    $ftr->{subsystems} = [],
	    $ftr->{protein_families} = [],
	    $ftr->{subsystem_data} = [],
	    $ftr->{regulon_data} = [],
	    $ftr->{atomic_regulons} = [],
	    $ftr->{coexpressed_fids} = [],
	    $ftr->{co_occurring_fids} = [],
	}
    }
    close(OUT);

    open(JSON, "> ../Genome_Objects/".$PATRIC_ID.".json");
    print JSON to_json($patric_genome, {pretty => 1});
    close(JSON);

    #Print limited Athaliana JSON for testing
    if($PATRIC_ID eq "Athaliana-TAIR10"){
	$patric_genome->{features} = [(@{$patric_genome->{features}})[0..100]];
	open(JSON, "> ../Genome_Objects/Test.json");
	print JSON to_json($patric_genome, {pretty => 1});
	close(JSON);
    }
}
close(SUM);
