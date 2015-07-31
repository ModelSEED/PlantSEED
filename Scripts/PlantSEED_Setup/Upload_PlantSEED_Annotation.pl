#!/usr/bin/env perl
use warnings;
use strict;
my $output;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $file = "../../DBs/PlantSEED_Roles.json";
exit if !-f $file;

open(FH, "<", $file);
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/annotation_overview',"unspecified",{},$data]], overwrite => 1 });
print "Uploaded $file as annotation_overview\n";
