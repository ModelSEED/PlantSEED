#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();

use FIG;
use gjoseqlib;

my $PlantBLAST_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $PlantBLAST_Root."User_Genomes/";

my $RAST_User=$ARGV[0];
#$RAST_User="plantseed";
exit(0) if !$RAST_User;

my $GenomeDir = $Genomes.$RAST_User."/Files/";
my $JSONDir = $Genomes.$RAST_User."/JSONs/";
mkdir $JSONDir if !-d $JSONDir;
exit(1) if !-d $GenomeDir;
exit(1) if !-d $JSONDir;

#Find user's fasta file
opendir(my $DIR, $GenomeDir);
my $Fasta = ( grep { $_ =~ /\.fa$/ } readdir($DIR))[0];
closedir($DIR);
exit(0) if !$Fasta || !-f $GenomeDir.$Fasta;

my @path = split(/\//,$Fasta);
my $Name = pop @path;
$Name =~ s/\.fa$//;

my $full_genome = {};
$full_genome->{id}=$Name;
$full_genome->{source}="PlantSEED";
$full_genome->{scientific_name} = undef;
$full_genome->{taxonomy} = undef;

my $minimal_genome = $full_genome;

my @seqs = gjoseqlib::read_fasta($GenomeDir.$Fasta);

foreach my $seq (@seqs){
    my $ftr = { id => $seq->[0] };
    my $minimal_ftr = $ftr;

    $ftr->{function} = undef;
    $ftr->{protein_translation} = $seq->[2];
    $ftr->{protein_translation_length} = length($ftr->{protein_translation});
    $ftr->{dna_sequence_length} = 3*$ftr->{protein_translation_length};
    $ftr->{md5} = Digest::MD5::md5_hex($ftr->{protein_translation});
    $ftr->{publications} = [];
    $ftr->{subsystems} = [];
    $ftr->{protein_families} = [];
    $ftr->{subsystem_data} = [];
    $ftr->{regulon_data} = [];
    $ftr->{atomic_regulons} = [];
    $ftr->{coexpressed_fids} = [];
    $ftr->{co_occurring_fids} = [];
    push(@{$full_genome->{features}},$ftr);

    $minimal_ftr->{function} = undef;
    $minimal_ftr->{subsystems} = [];
    push(@{$minimal_genome->{features}},$minimal_ftr);
}

open(JSON, "> ".$JSONDir.$Name.".json");
print JSON to_json($full_genome, {pretty => 1});
close(JSON);

open(JSON, "> ".$JSONDir.$Name."_min.json");
print JSON to_json($minimal_genome, {pretty =>1});
close(JSON);
