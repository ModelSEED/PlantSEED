#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my $output;
my @temp=();

my @Rxns = qw(rxn07301 rxn25468 rxn31542 rxn31420 rxn04468 rxn15786 rxn10095 
rxn31005 rxn24334 rxn24256 rxn25469 rxn22880 rxn25980 rxn25981
rxn30838 rxn31505 rxn01659 rxn11572 rxn07298 rxn24256 rxn04219
rxn17241 rxn19302 rxn25468 rxn23165 rxn25469 rxn23171 rxn23067
rxn30830 rxn30910 rxn31440 rxn01659 rxn13782 rxn13783 rxn13784
rxn05294 rxn05295 rxn05296 rxn10002 rxn10088 rxn11921 rxn11922
rxn10200 rxn11923 rxn05029 rxn05017 rxn03190 rxn26353 rxn31649 rxn31650);

my %Rxns = map { $_ => 1} @Rxns;

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
my $User = 'seaver';
Bio::P3::Workspace::ScriptHelpers::login({ user_id => $User, password => $Tokens{$User}[0] });

my %Files = ("PlantMapping" => {dest => 'biochemistry/plantdefault.mapping', type => 'mapping'},
	     "PlantBiochemistry" => {dest => 'biochemistry/plantdefault.biochem', type => 'biochemistry'},
	     "PlantModelTemplate" => {dest => 'templates/plant.modeltemplate', type => 'modeltemplate'});

my $File_Root = "../../DBs/";

#Read in prior models to find list of acceptable reactions
my %ModelReactions = ();
foreach my $file ("Evidenced-Arabidopsis-Model","PlantSEED-Ath-Model-GF"){
    my $data = "";
    open(FH, "< ".$File_Root.$file.".json");
    while(<FH>){
	chomp;
	$data.=$_;
    }
    close(FH);
    $data = from_json($data);

    foreach my $mdlrxn (@{$data->{modelreactions}}){
	my @path = split(/\//,$mdlrxn->{reaction_ref});
	my $rxn = $path[$#path];
	$ModelReactions{$rxn}=1;
    }
}

#foreach my $rxn (keys %Rxns){
#    $ModelReactions{$rxn}=1;
#}

my $WS_Root = '/chenry/public/modelsupport/';
foreach my $file (keys %Files){
    my $Dest = $WS_Root.$Files{$file}{dest};

    my $data = "";
    open(FH, "< ".$File_Root.$file.".json");
    while(<FH>){
	chomp;
	if( $file eq "PlantModelTemplate" ){
	    my $Old_Biochem_Root = "489\/13\/8";
	    my $Old_Mapping_Root = "598\/3\/17";
	    my $Biochem_Root = $WS_Root.$Files{'PlantBiochemistry'}{dest}."||";
    	    my $Mapping_Root = $WS_Root.$Files{'PlantMapping'}{dest}."||";

	    if( $_ =~ /${Old_Biochem_Root}/ ){
		$_ =~ s/${Old_Biochem_Root}/${Biochem_Root}/;
	    }elsif( $_ =~ /${Old_Mapping_Root}/ ){
		$_ =~ s/${Old_Mapping_Root}/${Mapping_Root}/;
	    }
	}

	$data .= $_;
    }
    close(FH);

    if( $file eq "PlantModelTemplate" ){
	$data = from_json($data);

	my %Remove_TmplRxns = ();
	foreach my $tmplrxn ( grep { $_->{type} eq "gapfilling" } @{$data->{templateReactions}}){
	    my @path = split(/\//,$tmplrxn->{reaction_ref});
	    my $rxn = $path[$#path];
	    $Remove_TmplRxns{$tmplrxn->{id}}=1 if !exists($ModelReactions{$rxn});
	}

	my @New_TmplRxns = grep { $_->{type} ne "gapfilling" || !exists($Remove_TmplRxns{$_->{id}}) } @{$data->{templateReactions}};
	$data->{templateReactions}=\@New_TmplRxns;
	$data = to_json($data);
    }

    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$Dest,$Files{$file}{type},{},$data]], overwrite => 1, adminmode => 1 });
    print "Uploaded $file to $Dest\n";
    
}
