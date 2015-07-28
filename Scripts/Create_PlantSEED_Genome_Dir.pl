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
$name = $name;
print "Creating directory .".$name."\n";

$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name,"folder"]] });
Bio::P3::Workspace::ScriptHelpers::print_wsmeta_table($output);

#$output = Bio::P3::Workspace::ScriptHelpers::wscall("set_permissions", { path => '/plantseed/Genomes/.'.$name , new_global_permission => 'r'});
#Bio::P3::Workspace::ScriptHelpers::print_wsmeta_table([$output]);
