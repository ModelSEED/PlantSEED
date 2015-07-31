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
my $folder = $path[$#path];
$folder =~ s/_min\.json$//;
my $name = "minimal_genome";
print "Uploading $file as $name into $folder\n";

open(FH, "<", $file);
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$folder.'/'.$name,"unspecified",{},$data]], overwrite => 1 });
Bio::P3::Workspace::ScriptHelpers::print_wsmeta_table($output);
