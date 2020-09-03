#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;

my %Roles_Subsystems=();
open(FH, "< ".$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/DBs/PlantSEED_Roles.json");
my $data = undef;
while(<FH>){
    $data.=$_;
}
close(FH);

my @Roles = @{from_json($data)};
foreach my $row (@Roles){
    foreach my $ss (keys %{$row->{subsystems}}){
	$Roles_Subsystems{$row->{role}}{$ss}=1;
    }
}

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

my $GO_Root = "/homes/seaver/Projects/PlantSEED_GitHub/Genome_Objects/";
opendir(my $dh, $GO_Root);
my @Dirs = grep { $_ =~ /_min\.json$/ } readdir($dh);
closedir($dh);

my $PS_Root = "/plantseed/Genomes/";
foreach my $file (@Dirs){
    my $Genome = $file;
    $Genome =~ s/_min\.json$//;

    my $Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$PS_Root."/.".$Genome."/minimal_genome"]})->[0][1];
    $Genome_obj = from_json($Genome_obj);

    my @Ftrs = @{$Genome_obj->{features}};
    for(my $i=0;$i<scalar(@Ftrs);$i++){
	$Ftrs[$i]->{'subsystems'}={};
	if(defined($Ftrs[$i]->{function}) && $Ftrs[$i]->{function} ne ""){
	    my $Function = $Ftrs[$i]->{function};
	    $Function = (split(/\s#/,$Function))[0];
	    foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$Function)){
		foreach my $ss (keys %{$Roles_Subsystems{$role}}){
		    $Ftrs[$i]->{'subsystems'}{$ss}=1;
		}
	    }
	    $Ftrs[$i]->{function}=$Function;
	}
	$Ftrs[$i]->{'subsystems'}=[keys %{$Ftrs[$i]->{'subsystems'}}];
    }
    $Genome_obj->{features}=\@Ftrs;
    $data = to_json($Genome_obj);

    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$PS_Root."/.".$Genome."/minimal_genome","unspecified",{},$data]], overwrite => 1 });
}
