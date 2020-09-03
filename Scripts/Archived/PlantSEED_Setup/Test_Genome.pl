#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my $output;
my @temp=();

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

my $WS_Root = '/chenry/public/modelsupport/';
#my $Dest = '/plantseed/Genomes/Zmays-AGPv2';
my $Dest = '/athamm/plantseed/genomes/.Athaliana_TAIR10/minimal_genome';
#my $Dest = '/reviewer/plantseed/genomes/..Mesculenta_v6.1/minimal_genome';
my $Tmpl_obj = Bio::P3::Workspace::ScriptHelpers::wscall("get",{ objects => [$Dest], adminmode=>1 })->[0][1];
$Tmpl_obj = from_json($Tmpl_obj);

print $Tmpl_obj->{exemplars},"\n";
print join("\n", keys %{$Tmpl_obj->{exemplars}}),"\n";
#print $Tmpl_obj->{domain},"\n";

#print join("\n", grep { exists($Rxns{$_}) } map { $_->{reaction_ref} =~ /(rxn\d{5})$/; $1; } @{$Tmpl_obj->{templateReactions}}),"\n";
