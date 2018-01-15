#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my $JSON;
my $header=1;
my @temp=();
my $output;

my $GenomeDir="/Users/seaver/Projects/PlantSEED_v2/Reference_Data_Scripts/Reference_Genomes/";
my %Ath_Genome_IDs=();
open(FH, "< ".$GenomeDir."Phytozome_11_Athaliana.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);
my $Genome = from_json($JSON);
foreach my $ftr (@{$Genome->{features}}){
    my $protein_id = $ftr->{id};
    my $gene_id = $protein_id;
    $gene_id =~ s/\.\d$//;
    $Ath_Genome_IDs{$gene_id}{$protein_id}=$ftr->{protein_translation_length};
}

open(FH, "< PlantSEED_Roles.json");
undef($JSON);
while(<FH>){
    chomp;
    $JSON.=$_;
}
close(FH);
my $Annotation = from_json($JSON);
foreach my $role (@{$Annotation}){
    my %Old_Ftrs = %{$role->{features}};
    my %New_Ftrs = ();
    foreach my $ftr (keys %Old_Ftrs){
	my $old_ftr=$ftr;
	my $longest_protein_id=$ftr;
	my $longest_protein_length=0;

	foreach my $protein (sort keys %{$Ath_Genome_IDs{$ftr}}){
	    if($Ath_Genome_IDs{$ftr}{$protein} > $longest_protein_length){
		$longest_protein_id=$protein;
		$longest_protein_length = $Ath_Genome_IDs{$ftr}{$protein};
	    }
	}
	my $new_ftr=$longest_protein_id;
	$New_Ftrs{$new_ftr}=$Old_Ftrs{$old_ftr};
    }
    $role->{features}=\%New_Ftrs;
}

open(OUT, "> PlantSEED_Roles_UpdatedFtrs.json");
print OUT to_json($Annotation, { pretty=>1, ascii=>1});
close(OUT);
