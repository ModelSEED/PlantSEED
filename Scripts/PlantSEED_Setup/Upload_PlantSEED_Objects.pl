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
my $User = 'plantseed';
Bio::P3::Workspace::ScriptHelpers::login({ user_id => $User, password => $Tokens{$User}[0] });

my $file = $ARGV[0];
exit if !$ARGV[0] || !-f $ARGV[0];

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;

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
my $Genome_Meta = undef;
foreach my $meta (@$Meta){
    $Genome_Meta = $meta->{$name} if exists($meta->{$name});
}

#Uploading Genome
open(FH, "<", $file);
$data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);
my $Genome_obj = from_json($data);

my @Ftrs = @{$Genome_obj->{features}};
for(my $i=0;$i<scalar(@Ftrs);$i++){
    if(!defined($Ftrs[$i]->{function})){
	$Ftrs[$i]->{function}="";
    }

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

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"genome",$Genome_Meta,$data]], overwrite => 1 });
print "Genome uploaded\n";

#Creating Folder
#If it already exists, nothing changes
#Permissions set in top-level folder
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name,"folder"]] });
print "/plantseed/Genomes/.".$name." folder created\n";

#Upload Minimal Genome
$file = join("/",@path[0..$#path-1])."/".$name."_min.json";

open(FH, "<", $file);
$data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);
my $Min_Genome_obj = from_json($data);

my @Ftrs = @{$Min_Genome_obj->{features}};
for(my $i=0;$i<scalar(@Ftrs);$i++){
    if(!defined($Ftrs[$i]->{function})){
	$Ftrs[$i]->{function}="";
    }

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
$Min_Genome_obj->{features}=\@Ftrs;
$data = to_json($Min_Genome_obj);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name.'/minimal_genome',"unspecified",{},$data]], overwrite => 1 });
print "Uploaded minimal genome from $file into .$name\n";

#Upload Sims
my $Plants_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $Plants_Root."PlantSEED_Genomes/";
my $JSONs_Dir = $Genomes.$name."/JSONs/";
print STDERR "JSONS not found for $name\n" if !-d $JSONs_Dir;
exit if !-d $JSONs_Dir;

opendir(my $dh, $JSONs_Dir);
my @Sim_Files = grep { $_ =~ /\.json$/ } readdir($dh);
closedir($dh);

foreach my $sim (@Sim_Files){
    open(FH, "<", $JSONs_Dir."/".$sim);
    my $data="";
    while(<FH>){
	chomp;
	$data.=$_;
    }
    close(FH);

    $sim =~ s/\.json//;
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name.'/'.$sim,"unspecified",{},$data]], overwrite => 1 });
}
print "Uploaded ".scalar(@Sim_Files)." Sim objects into .$name\n";
