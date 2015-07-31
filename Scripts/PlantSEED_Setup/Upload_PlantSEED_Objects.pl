#!/usr/bin/env perl
use warnings;
use strict;
my $output;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $file = $ARGV[0];
exit if !$ARGV[0] && !-f $ARGV[0];

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;

#Uploading Genome
$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"Genome",{},undef]], createUploadNodes => 1, overwrite => 1 });
my $SHOCK_URL = $output->[0][11];

use HTTP::Request::Common;
local $HTTP::Request::Common::DYNAMIC_FILE_UPLOAD = 1;
my $ua = LWP::UserAgent->new();
my $req = HTTP::Request::Common::POST($SHOCK_URL, 
				      Authorization => "OAuth " . Bio::P3::Workspace::ScriptHelpers::token(),
				      Content_Type => 'multipart/form-data',
				      Content => [upload => [$file]]);
$req->method('PUT');
my $sres = $ua->request($req);
print "Genome uploaded\n";

#Creating Folder
#If it already exists, nothing changes
#Permissions set in top-level folder
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name,"folder"]] });
print "/plantseed/Genomes/.".$name." folder created\n";

#Upload Minimal Genome
$file = join("/",@path[0..$#path-1])."/".$name."_min.json";

open(FH, "<", $file);
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

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
