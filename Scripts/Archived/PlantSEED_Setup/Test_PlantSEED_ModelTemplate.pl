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
rxn10200 rxn11923 rxn05029);

my %Rxns = map { $_ => 1} @Rxns;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use Bio::P3::Workspace::ScriptHelpers;

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
	     "PlantModelTemplate" => {dest => '', type => 'modeltemplate'});

my $WS_Root = '/chenry/public/modelsupport/';
my $Dest = $WS_Root.'templates/plant.modeltemplate';
my $Tmpl_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$Dest]})->[0][1];
$Tmpl_obj = from_json($Tmpl_obj);

print join("\n", map { $_->{type} } @{$Tmpl_obj->{templateReactions}}),"\n";

#print join("\n", grep { exists($Rxns{$_}) } map { $_->{reaction_ref} =~ /(rxn\d{5})$/; $1; } @{$Tmpl_obj->{templateReactions}}),"\n";
