#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use Bio::P3::Workspace::ScriptHelpers;

my $Token_File = "/homes/seaver/Projects/PATRIC_Scripts/Workspace_Scripts/Login_Tokens.txt";
open(FH, "< $Token_File");
my %Tokens=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,3);
    $Tokens{$temp[0]}=[$temp[1],$temp[2]];
}

#Set user for this
Bio::P3::Workspace::ScriptHelpers::login({ user_id => 'plantseed', password => $Tokens{'plantseed'}[0] });

#Retrieve meta data
my $MetaFile = "../../DBs/PlantSEED_Meta.json";
open(FH, "< $MetaFile");
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);
my $Meta = from_json($data);

my $GO_Root = "/homes/seaver/Projects/PlantSEED_GitHub/Genome_Objects/";
opendir(my $dh, $GO_Root);
my @Dirs = grep { $_ =~ /_min\.json$/ } readdir($dh);
closedir($dh);

my $PS_Root = "/plantseed/Genomes/";
foreach my $file (@Dirs){
    my $Genome = $file;
    $Genome =~ s/_min\.json$//;

    my $Genome_Meta = {};
    foreach my $meta (@$Meta){
	$Genome_Meta = $meta->{$Genome} if exists($meta->{$Genome});
    }

    my $Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$PS_Root."/".$Genome]})->[0][1];
    $Genome_obj = from_json($Genome_obj);

    my @Ftrs = @{$Genome_obj->{features}};
    for(my $i=0;$i<scalar(@Ftrs);$i++){
	if(defined($Ftrs[$i]->{function}) && $Ftrs[$i]->{function} ne ""){
	    my $Function = $Ftrs[$i]->{function};
	    $Function = (split(/\s#/,$Function))[0];
	    $Ftrs[$i]->{function}=$Function;
	}
    }
    $Genome_obj->{features}=\@Ftrs;
    my $data = to_json($Genome_obj);

    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$PS_Root."/".$Genome,"genome",$Genome_Meta,$data]], overwrite => 1 });
}
