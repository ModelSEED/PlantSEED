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

my $P3_User = 'seaver';
#Set user for this
Bio::P3::Workspace::ScriptHelpers::login({ user_id => $P3_User, password => $Tokens{$P3_User}[0] });

my $Plants_Root = "/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/User_Genomes/";
my $User = $ARGV[0];
my $PS_Genome = $ARGV[1];
exit if !$User || !-d $Plants_Root.$User;
exit if !$PS_Genome;

#A Get PlantSEED minimal genome object
my $PS_Root = '/plantseed/Genomes/';
my $PS_Minimal_Genome = $PS_Root.".".$PS_Genome."/minimal_genome";
my $PS_Min_Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$PS_Minimal_Genome], adminmode => 1})->[0][1];
$PS_Min_Genome_obj = from_json($PS_Min_Genome_obj);

#B Check for Genome object
my $User_Root = "/".$User."/plantseed/genomes";
my $Genome = Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$User_Root], adminmode=>1, excludeDirectories => 1 })->{$User_Root}[0][0];
my $Minimal_Genome = ".".$Genome."/minimal_genome";

#C Get Genome objects
my $Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$User_Root."/".$Genome], adminmode => 1})->[0][1];
$Genome_obj = from_json($Genome_obj);

my $Min_Genome_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$User_Root."/".$Minimal_Genome], adminmode => 1})->[0][1];
$Min_Genome_obj = from_json($Min_Genome_obj);

foreach my $ftr (@{$PS_Min_Genome_obj->{features}}){
    my @Ftrs = @{$Genome_obj->{features}};
    for(my $i=0;$i<scalar(@Ftrs);$i++){
	
    }

    for(my $i=0;$i<scalar(@Ftrs);$i++){
	if($Ftrs[$i]->{id} eq $ftr->{id}){
	    $Ftrs[$i]->{function}=$ftr->{function};
	    last;
	}
    }
    $Genome_obj->{features}=\@Ftrs;

    @Ftrs = @{$Min_Genome_obj->{features}};
    for(my $i=0;$i<scalar(@Ftrs);$i++){
	if($Ftrs[$i]->{id} eq $ftr->{id}){
	    $Ftrs[$i]->{function}=$ftr->{function};
	    last;
	}
    }
    $Min_Genome_obj->{features}=\@Ftrs;
}

$Genome_obj=to_json($Genome_obj);
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/'.$Genome,"genome",{},$Genome_obj]],
						     overwrite => 1, adminmode => 1, setowner=>$User });
print "Genome uploaded\n";

$Min_Genome_obj=to_json($Min_Genome_obj);
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/'.$Minimal_Genome,"unspecified",{},$Min_Genome_obj]],
						     overwrite => 1, adminmode => 1, setowner=>$User });
print "Minimal Genome uploaded\n";
