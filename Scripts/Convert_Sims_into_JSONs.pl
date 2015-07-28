#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();

my $Ftr_Dir=$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/Scripts/Feature_Aliases/";
opendir(my $dh, $Ftr_Dir);
my @Files = grep { $_ =~ /\.txt$/ } readdir($dh);
closedir($dh);

my %Genome_Genes=();
foreach my $file (@Files){
    my @Path = split(/\//,$file);
    my $Name = pop(@Path);
    $Name =~ s/\.txt$//;

    open(FH, "< ".$Ftr_Dir.$file);
    while(<FH>){
	chomp;
	my ($peg,$gene) = split(/\t/,$_,3);
	$Genome_Genes{$gene}=$Name;
    }
    close(FH);
}

my $Plants_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $Plants_Root."PlantSEED_Genomes/";
my $Genome = $ARGV[0];
$Genome = "Athaliana-TAIR10";

my $File = $Genomes.$Genome."/Files/".$Genome.".sims";
exit(0) if !$Genome || !-f $File;

my $JSONs_Dir = $Genomes.$Genome."/JSONs/";
mkdir $JSONs_Dir if !-d $JSONs_Dir;

open(FH, "< $File");
my $Sims = {};
my $Sims_Index = 0;
my $Ftr_Index = {};

while(<FH>){
    chomp;

    @temp=split(/\t/,$_,-1);
    my ($query,$hit,$percent,$evalue,$bitscore) = @temp[0,1,2,10,11];

    next if exists($Genome_Genes{$hit}) && $Genome_Genes{$hit} eq $Genome;

    if(scalar(keys %$Sims)>=1000 && !exists($Sims->{$query})){
	open(JSON, "> ".$JSONs_Dir."Sims_".$Sims_Index.".json");
	print JSON to_json($Sims, {pretty => 1});
	close(JSON);

	undef($Sims);
	$Sims_Index++;
    }

    my $ftr_json = { hit_id => $hit, percent_id => $percent, e_value => $evalue, bit_score => $bitscore };

    $Sims->{$query} = [] if !exists($Sims->{$query});
    push(@{$Sims->{$query}},$ftr_json);

    if(exists($Ftr_Index->{$query}) && $Ftr_Index->{$query} != $Sims_Index){
	print "Warning";
    }
    $Ftr_Index->{$query}=$Sims_Index;
}

my $GitHub_Root="/homes/seaver/Projects/PlantSEED_GitHub/";
my $GenomeObjects = $GitHub_Root."Genome_Objects/";

open(FH, "< ".$GenomeObjects.$Genome."_min.json");
my $json_text = "";
while(<FH>){
    $json_text.=$_;
}
close(FH);

my $minimal_genome = from_json($json_text);
$minimal_genome->{similarities_index}=$Ftr_Index;

open(JSON, "> ".$GenomeObjects.$Genome."_min.json");
print JSON to_json($minimal_genome, {pretty => 1});
close(JSON);
