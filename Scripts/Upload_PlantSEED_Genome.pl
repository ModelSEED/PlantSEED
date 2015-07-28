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
exit if !-f $ARGV[0];

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;
print "Uploading $file as $name\n";

$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"Genome",{},undef]], createUploadNodes => 1, overwrite => 1 });
my $SHOCK_URL = $output->[0][11];
#$SHOCK_URL = "https://p3.theseed.org/services/shock_api/node/11fff6ac-b933-4646-bbeb-6e2924b500bb";

use HTTP::Request::Common;
local $HTTP::Request::Common::DYNAMIC_FILE_UPLOAD = 1;
my $ua = LWP::UserAgent->new();
my $req = HTTP::Request::Common::POST($SHOCK_URL, 
				      Authorization => "OAuth " . Bio::P3::Workspace::ScriptHelpers::token(),
				      Content_Type => 'multipart/form-data',
				      Content => [upload => [$file]]);
$req->method('PUT');
my $sres = $ua->request($req);

use Data::Dumper;
print Dumper($sres),"\n";

print "File created:\n";
