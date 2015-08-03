#!/usr/bin/env perl
use warnings;
use strict;
my @temp=();
my $output=undef;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $Token_File = "/homes/seaver/Projects/PATRIC_Scripts/Workspace_Scripts/Login_Tokens.txt";
open(FH, "< $Token_File");
my %Tokens=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,3);
    $Tokens{$temp[0]}=[$temp[1],$temp[2]];
}

#Set user for this (seaver has admin power)
Bio::P3::Workspace::ScriptHelpers::login({ user_id => 'seaver', password => $Tokens{'seaver'}[0] });

my ($User,$Genome) = ($ARGV[0],$ARGV[1]);
exit if !$ARGV[0] || !$ARGV[1];

print $User,"\t",$Genome,"\n";

#Hard-coded set of files for genome includes
#1) Original Genome object (needs to be correctly identified and stored in $Genome)
#2) minimal_genome object, found in ~/.$Genome/minimal_genome
#3) Sims_n objects where n can be any number. These are found in ~/.$Genome/Sims_n

#A Check for existence of objects

my $PlantSEED_Root = '/plantseed/Genomes';
my @Dir_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$PlantSEED_Root] })->{$PlantSEED_Root}};
my ($HasGenome,$HasDir,$HasMin,$HasSims)=(0,0,0,0);
my @Sims=();
foreach my $entry (@Dir_Contents){
    if($entry->[0] eq $Genome && $entry->[1] eq 'genome'){
	$HasGenome=1;
    }
    if($entry->[0] eq ".".$Genome && $entry->[1] eq 'folder'){
	$HasDir=1;
	my @Gen_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$PlantSEED_Root."/.".$Genome] })->{$PlantSEED_Root."/.".$Genome}};
	foreach my $gentry (@Gen_Contents){
	    if($gentry->[0] eq "minimal_genome" && $gentry->[1] eq "unspecified"){
		$HasMin=1;
	    }
	    if($gentry->[0] =~ /^(Sims_\d+)$/ && $gentry->[1] eq "unspecified"){
		$HasSims=1;
		push(@Sims,$1);
	    }
	}
    }
}

exit if !$HasGenome || !$HasDir || !$HasMin || !$HasSims || scalar(@Sims)==0;

#B Check that user has PlantSEED directory
#Genomes will be stored in /<user>/plantseed/genomes/

my $User_Root = "/".$User;
$output = Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$User_Root], adminmode=>1 });
if(scalar(keys %$output)==0 || !exists($output->{$User_Root})){
    print STDERR "Cannot access $User directory\n";
    exit();
}

my $User_Genome_Root = $User_Root.lc($PlantSEED_Root);
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root."/plantseed",'folder']], adminmode=>1, setowner=>$User, overwrite=>1});
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Genome_Root,'folder']], adminmode=>1, setowner=>$User, overwrite=>1});

#C Copy Genome object
Bio::P3::Workspace::ScriptHelpers::wscall("copy",{ objects => [[$PlantSEED_Root."/".$Genome,$User_Genome_Root."/".$Genome]], adminmode=>1, overwrite=>1 });
Bio::P3::Workspace::ScriptHelpers::wscall("copy",{ objects => [[$PlantSEED_Root."/.".$Genome,$User_Genome_Root."/.".$Genome]], adminmode=>1, recursive=>1, overwrite=>1 });
