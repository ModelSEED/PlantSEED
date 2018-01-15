#!/usr/bin/env perl
use strict;
use warnings;
use JSON;
my @temp=();
my @Headers=();

open(OUT, "> Plastidial_SandBox_Media.txt2");
print OUT "id\tname\tconcentration\tminflux\tmaxflux\n";
open(FH, "< Plastidial_SandBox_Media.txt");
undef(@Headers);
while(<FH>){
    chomp;
    if(scalar(@Headers)==0){@Headers=split(/\t/,$_,-1);next;}
    @temp=split(/\t/,$_,-1);
    print OUT $temp[0],"\t",$temp[0],"\t0.01\t-1000\t1000\n";
}
close(OUT);
