#!/usr/bin/env perl
use strict;
use warnings;
use JSON;
my @temp=();
my @Headers=();

my $Media = {"id" => "Plastidial_Media","source_id" => "PlantSEED", "name" => "Plastidial_Media","type" => "unspecified",
	     "isMinimal" => 0,"isDefined" => 1,
	     "mediacompounds" => []};

open(FH, "< Plastidial_SandBox_Media.txt");
my %Media = ();
undef(@Headers);
while(<FH>){
    chomp;
    if(scalar(@Headers)==0){@Headers=split(/\t/,$_,-1);next;}
    @temp=split(/\t/,$_,-1);
    my $mediacpd = { compound_ref => "kbase/plantdefault_obs/compounds/id/".$temp[0],
		     concentration=>0.01,minFlux=>-1000,maxFlux=>1000 };
    push(@{$Media->{mediacompounds}},$mediacpd);
}
close(FH);

open(OUT, "> Plastidial_SandBox_Media.json");
print OUT to_json($Media,{pretty=>1,ascii=>1});
close(OUT);
