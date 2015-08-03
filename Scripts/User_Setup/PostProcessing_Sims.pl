#!/usr/bin/env perl
use warnings;
use strict;
my @temp=();

my $File = $ARGV[0];
exit(1) if !$File || !-f $File;

#Get Gene Aliases
my $Ftr_Dir=$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/Scripts/Feature_Aliases/";
opendir(my $dh, $Ftr_Dir);
my @Files = grep { $_ =~ /\.txt$/ } readdir($dh);
closedir($dh);

my %Genes=();
foreach my $file (@Files){
    my @Path = split(/\//,$file);
    my $Name = pop(@Path);
    $Name =~ s/\.txt$//;

    open(FH, "< ".$Ftr_Dir.$file);
    while(<FH>){
	chomp;
	my ($peg,$gene) = split(/\t/,$_,3);
	$Genes{$gene}=$peg;
    }
    close(FH);
}

#Get Families
open(FH, "< ../../DBs/Gramene_Family_Rows.txt");
my %Families_Genes=();
my %Genes_Families=();
my $Family=1;
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    shift @temp;

    foreach my $gene ( grep { exists($Genes{$_}) } map { $_ =~ s/^VIT_/Vv/; $_ } map { (split(/\|/,$_))[0] } @temp ){
        $Families_Genes{$Family}{$Genes{$gene}}=1;
        $Genes_Families{$Genes{$gene}}=$Family;
    }
    $Family++;
}
close(FH);

#Get Bacterial hits
open(FH, "< ../../DBs/Plant_Families_Microbes_BH.txt");
my %BactHits=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    next unless $temp[10] < 1e-5;
    $BactHits{$temp[0]}{$temp[1]}=join("\t",@temp[2..$#temp]);
}
close(FH);

my @Lines=();
open(FH, "< $File");
my %Pegs_Sims=();
my %BactCounts=();
my $Current_Peg="";
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    next if !exists($Genes_Families{$temp[1]});
    next unless $temp[10] < 1e-10;

    $Current_Peg = $temp[0];

    $Pegs_Sims{$Current_Peg}{$temp[1]}={bitscore=>$temp[11],line=>$_};

    if(exists($BactHits{$temp[1]})){
	foreach my $peg (keys %{$BactHits{$temp[1]}}){
	    last if scalar(keys %{$BactCounts{$Current_Peg}})>=30;

	    my $line = $Current_Peg."\t".$peg."\t".$BactHits{$temp[1]}{$peg};
	    my @parts = split(/\t/,$line,-1);
	    $Pegs_Sims{$Current_Peg}{$peg}={bitscore=>$parts[11],line=>$line};
	    $BactCounts{$Current_Peg}{$peg}=$parts[10];
	}
    }

    foreach my $peg (keys %{$Families_Genes{$Genes_Families{$temp[1]}}}){
	my $line = $Current_Peg."\t".$peg."\t".join("\t",@temp[2..$#temp]);
	my @parts = split(/\t/,$line,-1);

	if(!exists($Pegs_Sims{$Current_Peg}{$peg})){
	    $Pegs_Sims{$Current_Peg}{$peg}={bitscore=>$parts[11],line=>$line};
	}

	if(exists($BactHits{$peg})){
	    foreach my $Bpeg (keys %{$BactHits{$peg}}){
		last if scalar(keys %{$BactCounts{$Current_Peg}})>=30;
		my $line = $Current_Peg."\t".$Bpeg."\t".$BactHits{$peg}{$Bpeg};
		my @parts = split(/\t/,$line,-1);

		if(!exists($Pegs_Sims{$Current_Peg}{$Bpeg})){
		    $Pegs_Sims{$Current_Peg}{$Bpeg}={bitscore=>$parts[11],line=>$line};
		    $BactCounts{$Current_Peg}{$Bpeg}=$parts[10];
		}
	    }
	}
    }
#    last if scalar(keys %Pegs_Sims)==100;
}
close(FH);

my $out_file = $File."_expanded";
open(OUT, "> $out_file");
foreach my $query_peg (sort keys %Pegs_Sims){
    foreach my $result_peg (sort { $Pegs_Sims{$query_peg}{$b}{bitscore} <=> $Pegs_Sims{$query_peg}{$a}{bitscore} } keys %{$Pegs_Sims{$query_peg}}){
	print OUT $Pegs_Sims{$query_peg}{$result_peg}{line},"\n";
    }
}
close(OUT);
