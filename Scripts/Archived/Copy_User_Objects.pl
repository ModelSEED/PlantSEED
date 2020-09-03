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
my $PS_User = 'seaver';
Bio::P3::Workspace::ScriptHelpers::login({ user_id => $PS_User, password => $Tokens{$PS_User}[0] });

my ($New_User,$Old_User) = ($ARGV[0],$ARGV[1]);
exit if !$ARGV[0] || !$ARGV[1];

print $New_User,"\t",$Old_User,"\n";

#Hard-coded set of files for genome includes
#1) Original Genome object (needs to be correctly identified and stored in $Genome)
#2) minimal_genome object, found in ~/.$Genome/minimal_genome
#3) Sims_n objects where n can be any number. These are found in ~/.$Genome/Sims_n

#A Check for existence of objects

my $Old_User_Root = "/".$Old_User."/plantseed/genomes";
my @Dir_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$Old_User_Root], adminmode=>1 })->{$Old_User_Root}};
my ($HasGenome,$HasDir,$HasMin,$HasSims)=(0,0,0,0);
my @Sims=();
foreach my $entry (@Dir_Contents){
    if($entry->[1] eq 'genome'){
	$HasGenome=$entry->[0];
    }
}

foreach my $entry (@Dir_Contents){
    if($entry->[0] eq ".".$HasGenome && $entry->[1] eq 'folder'){
	$HasDir=1;
	my @Gen_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$Old_User_Root."/.".$HasGenome], adminmode=>1 })->{$Old_User_Root."/.".$HasGenome}};
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

my $New_User_Root = "/".$New_User;
$output = Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$New_User_Root], adminmode=>1 });
if(scalar(keys %$output)==0 || !exists($output->{$New_User_Root})){
    print STDERR "Cannot access $New_User directory\n";
    exit();
}

my $New_User_Genome_Root = $New_User_Root."/plantseed/genomes";
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$New_User_Root."/plantseed",'folder']], adminmode=>1, setowner=>$New_User, overwrite=>1});
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$New_User_Genome_Root,'folder']], adminmode=>1, setowner=>$New_User, overwrite=>1});

#C Copy Genome object
print "Copying ".$New_User_Genome_Root."/".$HasGenome." from ".$Old_User_Root."/".$HasGenome."\n";
my $Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$Old_User_Root."/".$HasGenome], adminmode => 1})->[0][1];
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$New_User_Genome_Root."/".$HasGenome,"genome",{},$Genome_obj]], overwrite => 1, adminmode=>1 });

my $New_User_Genome_Folder = $New_User_Genome_Root."/.".$HasGenome;
my $Old_User_Genome_Folder = $Old_User_Root."/.".$HasGenome;


print "Copying ".$New_User_Genome_Folder."/minimal_genome from ".$Old_User_Genome_Folder."/minimal_genome\n";
my $Min_Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$Old_User_Genome_Folder."/minimal_genome"], adminmode => 1})->[0][1];
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$New_User_Genome_Folder."/minimal_genome","unspecified",{},$Min_Genome_obj]], overwrite => 1, adminmode=>1 });


foreach my $sim (@Sims){
    print "Copying ".$New_User_Genome_Folder."/".$sim," from ".$Old_User_Genome_Folder."/".$sim."\n";
    my $Sim_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$Old_User_Genome_Folder."/".$sim], adminmode => 1})->[0][1];
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$New_User_Genome_Folder."/".$sim,"unspecified",{},$Sim_obj]], overwrite => 1, adminmode=>1 });
}
