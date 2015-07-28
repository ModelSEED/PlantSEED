#!/usr/bin/env perl
use warnings;
use strict;
my @temp=();

my $Ftr_Dir=$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/Scripts/Feature_Aliases/";
opendir(my $dh, $Ftr_Dir);
my @Files = grep { $_ =~ /\.txt$/ } readdir($dh);
closedir($dh);

my %Peg_Aliases=();
foreach my $file (@Files){
    open(FH, "< ".$Ftr_Dir.$file);
    while(<FH>){
	chomp;
	my ($peg,$gene) = split(/\t/,$_,3);
	$Peg_Aliases{$peg}=$gene;
    }
    close(FH);
}

my $Sims_File = $ARGV[0];
exit(0) if !$Sims_File || !-f $Sims_File;
my @Lines = ();
open(FH, "< $Sims_File");
while(<FH>){
    chomp;
    my ($query,$hit,$line)=split(/\t/,$_,3);
    $query = $Peg_Aliases{$query} if exists($Peg_Aliases{$query});
    $hit = $Peg_Aliases{$hit} if exists($Peg_Aliases{$hit});
    push(@Lines, $query."\t".$hit."\t".$line);
}
close(FH);

open(OUT, "> $Sims_File");
print OUT join("\n",@Lines)."\n";
close(OUT);
