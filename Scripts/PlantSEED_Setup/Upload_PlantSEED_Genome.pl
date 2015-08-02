#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my $output;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $file = $ARGV[0];
exit if !-f $ARGV[0];

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;
print "Uploading $file as $name\n";

#Possibly delete old nodes because over-writing will create a new node and ignore old ones
#$output = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => ['/plantseed/Genomes/'.$name] });
#my $SHOCK_URL = $output->[0][1];
#print $SHOCK_URL,"\n";

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

$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"Genome",$Genome_Meta,undef]], 
							       createUploadNodes => 1, overwrite => 1 });
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
print "File created\n";
