#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;
my $ua = LWP::UserAgent->new();
my $res = undef;

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

#Set user for this
Bio::P3::Workspace::ScriptHelpers::login({ user_id => 'plantseed', password => $Tokens{'plantseed'}[0] });

my $file = $ARGV[0];
exit if !-f $ARGV[0];

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;
print "Uploading $file as $name\n";

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

open(FH, "<", $file);
$data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"genome",$Genome_Meta,$data]], overwrite => 1 });
