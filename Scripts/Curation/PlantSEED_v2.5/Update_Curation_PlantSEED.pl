#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $header=1;

my $DB_JSON = "../../Core_Plant_Metabolism/PlantSEED_Roles_v2.5.json";
open(FH, "< $DB_JSON");
my $DB="";
while(<FH>){
    $DB.=$_;
}
close(FH);
$DB = from_json($DB);

my $Cur_JSON = "./PlantSEED_Roles_Curation.curating";
my $Cur="";
open(FH, "< $Cur_JSON");
while(<FH>){
    $Cur.=$_;
}
close(FH);
$Cur = from_json($Cur);

my %Removed_Roles=();
#open(FH, "< ../Deleted_Roles.txt");
#while(<FH>){
#    chomp;
#    $Removed_Roles{$_}=1;
#}
#close(FH);

#Update quantities within $DB
my %New_Roles = ();
my %Updated_Roles = ();
my %Duplicate_Roles = ();
foreach my $row (@{$Cur}){
    $Duplicate_Roles{$row->{role}}++;
    next if exists($Removed_Roles{$row->{role}});

    my $Updated=0;
    for(my $i=0;$i<scalar(@$DB);$i++){
	if($row->{role} eq $DB->[$i]{role}){
	    $DB->[$i] = $row;
	    $Updated_Roles{$row->{role}}=1;
	    $Updated=1;
	    last;
	}
    }
    $New_Roles{$row->{role}}=1 if !$Updated;
}

print join("\n", map { "Warning! Duplicate role: ".$_ } grep { $Duplicate_Roles{$_} > 1 } sort keys %Duplicate_Roles),"\n";

#Add new roles to DB
foreach my $row  ( grep { exists($New_Roles{$_->{role}}) } @$Cur ){
    push(@$DB,$row);
}

#Remove unwanted roles from DB
$DB = [ grep { !exists($Removed_Roles{$_->{role}}) } @$DB ];

open(OUT, "> ../../Core_Plant_Metabolism/PlantSEED_Roles_v2.5_Curated.json");
print OUT to_json($DB, {pretty => 1, ascii => 1});
close(OUT);
