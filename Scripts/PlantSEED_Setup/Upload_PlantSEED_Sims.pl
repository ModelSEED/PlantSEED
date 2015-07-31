#!/usr/bin/env perl
use warnings;
use strict;
my $output;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $Plants_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $Plants_Root."PlantSEED_Genomes/";
my $Genome = $ARGV[0];
$Genome = "Athaliana-TAIR10";
my $JSONs_Dir = $Genomes.$Genome."/JSONs/";
exit if !-d $JSONs_Dir;

opendir(my $dh, $JSONs_Dir);
my @Sim_Files = grep { $_ =~ /\.json$/ } readdir($dh);
closedir($dh);

foreach my $sim (@Sim_Files){
    my $name = $sim;
    $name =~ s/\.json$//;
    my $folder = "/plantseed/Genomes/.".$Genome;
    print "Uploading $sim as $name into $folder\n";

    open(FH, "<", $JSONs_Dir."/".$sim);
    my $data="";
    while(<FH>){
	chomp;
	$data.=$_;
    }
    close(FH);
    $output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$folder.'/'.$name,"unspecified",{},$data]], overwrite => 1 });
}

