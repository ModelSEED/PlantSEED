#!/usr/bin/env perl
use strict;
use warnings;
use DateTime;
use JSON;
my @temp=();
my $Token = $ENV{'KB_AUTH_TOKEN'};

# Should read this directly from template files
my %Template_Compartment_Mapping=('c' => 'cytosol', 'g' => 'golgi', 'w' => 'cellwall',
                                  'n' => 'nucleus', 'r' => 'endoplasm',
                                  'v' => 'vacuole', 'cv' => 'vacuole',
                                  'd' => 'plastid', 'cd' => 'plastid',
                                  'm' => 'mitochondria','cm' => 'mitochondria',
                                  'mj' => 'mitointer',
                                  'x' => 'peroxisome');

#KBase Environment
my $Workspace_URL = "https://appdev.kbase.us/services/ws";

#PlantSEED commit
my $PS_git_url = "https://raw.githubusercontent.com/ModelSEED/PlantSEED/";
my $PS_tag = "v3.0.0";
#$PS_tag = "07e5f81e4d7c892e02daf6642ece114e73b83e0c"; # Integrating Tristan's Linalool
#$PS_tag = "ea80e9943a49506cb02466e29b97c93508181f08"; # Integrating Ashley's 1,8-cineole
#$PS_tag = "a5d09a110b175f525275a52419367a6919f1ca21"; # Integrating Leah's Work

#User's Workspace
my $WS="PlantSEED";
$WS="tcontant:narrative_1626281518370";
$WS="ashanderson:narrative_1627079050992";
$WS="seaver:narrative_1625174835851";
$WS="seaver:narrative_1629867179241";
$WS="ldunlap7:narrative_1632495329033";

#User's Genome
my $Genome="Athaliana_TAIR10";
$Genome="Arabidopsis_thaliana";

#my $remote_file = $PS_git_url.$PS_tag."/Data/PlantSEED_v3/PlantSEED_Roles.json";
#print($remote_file,"\n");
#use LWP::Simple;
# Need LWP::Protocol::https
#use LWP::UserAgent;

#my $agent = LWP::UserAgent->new;
#my $response = $agent->get($remote_file);

#$response->is_success or die $response->status_line;

#my $json_file = get $remote_file;
#print($json_file,"\n");
#my $Curation = from_json($json_file);

my $local_file = "../../../Data/PlantSEED_v3/PlantSEED_Roles.json";
my $json_file="";
open(FH, "< $local_file");
while(<FH>){
    $json_file.=$_;
}
close(FH);
my $Curation = from_json($json_file);

#Load Ath Annotation
my %Ftrs=();
foreach my $row (@$Curation){
    foreach my $spp_ftr (@{$row->{'features'}}){
        $Ftrs{$spp_ftr}{'roles'}{$row->{role}}=1;
    }

    foreach my $cpt (keys %{$row->{'localization'}}){
        foreach my $entry (keys %{$row->{'localization'}{$cpt}}){
            if(exists($Ftrs{$entry})){
                $Ftrs{$entry}{'cpts'}{$cpt}=1;
            }
        }
    }
}

my %Ftr_Funcs=();
foreach my $ftr (sort keys %Ftrs){
    my $func = join(" / ", sort keys %{$Ftrs{$ftr}{'roles'}});
    my $cpts = join(" # ", map { $Template_Compartment_Mapping{$_} } sort keys %{$Ftrs{$ftr}{'cpts'}});
    $func.=" # ".$cpts if $cpts ne "";

    $Ftr_Funcs{$ftr}=$func;
}

use Bio::KBase::workspace::Client;
my $WS_Client=Bio::KBase::workspace::Client->new($Workspace_URL,token => $Token);

my $data = $WS_Client->get_objects2({objects=>[{ref=>$WS."/".$Genome}]})->{data}[0];

my @Ftrs = @{$data->{data}{features}};
my %Ftr_Index=();
for(my $i=0;$i<scalar(@Ftrs);$i++){
    $Ftr_Index{$Ftrs[$i]{'id'}}=$i;
    if(exists($Ftrs[$i]{'function'})){
	delete($Ftrs[$i]{'function'});
    }
    $Ftrs[$i]{'functions'}=[];
}

my @mRNAs = @{$data->{data}{mrnas}};
for(my $i=0;$i<scalar(@mRNAs);$i++){
    my $Obj_ID = $mRNAs[$i]{id};
    my $Ftr_ID = $mRNAs[$i]{'parent_gene'};
    my $Spp_Protein = "Athaliana_TAIR10||".$Ftr_ID;

    if(exists($Ftr_Funcs{$Spp_Protein})){
	my $Function=$Ftr_Funcs{$Spp_Protein};
	$mRNAs[$i]{'functions'}=[$Function];
	$Ftrs[$Ftr_Index{$Ftr_ID}]{'functions'}=[$Function];
	print($Function,"\n");
    }else{
	$mRNAs[$i]{'functions'}=[];
    }
}

$WS_Client->save_object({id=>$Genome."_PS2",type=>"KBaseGenomes.Genome",data=>$data->{data},metadata=>$data->{info}[10],workspace=>$WS});
