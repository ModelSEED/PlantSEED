#!/usr/bin/env perl
use warnings;
use strict;

my $PlantBLAST_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $PlantBLAST_Root."User_Genomes/";

my $RAST_User=$ARGV[0];
#$RAST_User="plantseed";
exit(0) if !$RAST_User;

my $GenomeDir = $Genomes.$RAST_User."/";
mkdir $GenomeDir if !-d $GenomeDir;
exit(0) if !-d $GenomeDir;

#Find user's fasta file
opendir(my $DIR, $GenomeDir."Files/");
my $Fasta = ( grep { $_ =~ /\.fa$/ } readdir($DIR))[0];
closedir($DIR);
exit(0) if !$Fasta;

my $QsubOutputDir=$GenomeDir."QsubOutput/";
mkdir $QsubOutputDir;

#Prepare Qsub command/optionss
my @Command = ("qsub","-l","arch=lx26-amd64","-b","yes","-N","PlantSEED_".$RAST_User,"-e",$QsubOutputDir."QsubError","-o",$QsubOutputDir."QsubOutput");

#prepare Blast command/options
push(@Command,"/vol/rast-bcr/2010-1124/linux-rhel5-x86_64/bin/blastall");
push(@Command,"-p");push(@Command,"blastp");
push(@Command,"-FF");
push(@Command,"-e");push(@Command,"1.0e-5");
push(@Command,"-m");push(@Command,"8");

#prepare Blast files
push(@Command,"-d");push(@Command,$PlantBLAST_Root."DBs/PubSEED_Plants_Families_Shortened");
push(@Command,"-i");push(@Command,$GenomeDir."Files/".$Fasta);
push(@Command,"-o");push(@Command,$GenomeDir."Files/".$Fasta."_pfs");

my $cmd=join(" ",@Command);

my $QsubIDFile=$GenomeDir."QSUB_SIMS_ID";
my $QsubID=0;

if (!open(Q, "$cmd |")){
    die("Qsub failed for genome $Fasta: $!");
}
while(<Q>){
    if (/Your\s+job\s+(\d+)/){
	$QsubID = $1;
    }
}

if (!close(Q)){
    warn("Qsub close failed: $!");
}

if (!$QsubID){
    warn("did not get job id from qsub");
}

print "Submitted, job id is $QsubID\n";

my %Qsub_Genomes=();
open(FH, "< Qsub_Genomes.txt");
while(<FH>){
    chomp;
    my @temp=split(/\t/);
    $Qsub_Genomes{$temp[1]}=$temp[0];
}
close(FH);

$Qsub_Genomes{$RAST_User}=$QsubID;

open(FH, "> Qsub_Genomes.txt");
foreach my $RU (keys %Qsub_Genomes){
    print FH $Qsub_Genomes{$RU},"\t",$RU,"\n";
}
close(FH);
