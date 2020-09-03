#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;

my $Ftr_Dir=$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/Scripts/Feature_Aliases/";
opendir(my $dh, $Ftr_Dir);
my @Files = grep { $_ =~ /\.txt$/ } readdir($dh);
closedir($dh);

my %Genome_Genes=();
foreach my $file (@Files){
    my @Path = split(/\//,$file);
    my $Name = pop(@Path);
    $Name =~ s/\.txt$//;

    open(FH, "< ".$Ftr_Dir.$file);
    my $count = 0;
    while(<FH>){
	chomp;
	my ($peg,$gene,$transcript) = split(/\t/,$_,3);
	$Genome_Genes{$gene}={'genome'=>$Name , 'seed'=>$peg, 'index' => $count};
	$Genome_Genes{$gene}{'transcript'}=$transcript if $transcript !~ /\.transcript$/;
	$count++;
    }
    close(FH);
}

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
opendir($dh, $GO_Root);
my @Dirs = grep { $_ =~ /_min\.json$/ } readdir($dh);
closedir($dh);

my $PS_Root = "/plantseed/Genomes/";
foreach my $file (@Dirs){
    my $Genome = $file;
    $Genome =~ s/_min\.json$//;

    my $Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$PS_Root."/.".$Genome."/minimal_genome"]})->[0][1];
    $Genome_obj = from_json($Genome_obj);

    foreach my $ftr (@{$Genome_obj->{features}}){
	if(defined($ftr->{function}) && $ftr->{function} ne ""){
	    my $Function = $ftr->{function};
	    $Function = (split(/\s+#/,$Function))[0];
	    $Genome_Genes{$ftr->{id}}{'function'}=$Function;

	    foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$Function)){
		$Genome_Genes{$ftr->{id}}{'roles'}{$role}=1;
		foreach my $ss (keys %{$Roles_Subsystems{$role}}){
		    $Genome_Genes{$ftr->{id}}{'subsystems'}{$ss}=1;
		}
	    }
	}
    }
}

$data = to_json(\%Genome_Genes);
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/feature_lookup',"unspecified",{},$data]], overwrite => 1 });
