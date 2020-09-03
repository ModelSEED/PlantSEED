#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();

my $DBs = "/homes/seaver/Projects/PlantSEED_GitHub/DBs/Functional_BLAST_DBs";

opendir(my $dh, $DBs);
my @Files = grep { $_ =~ /\.tar\.gz$/ } readdir($dh);
closedir($dh);

foreach my $file (@Files){
    print $DBs."/".$file,"\n" if -f $DBs."/".$file;
    my $number = $file;
    $number =~ s/\.tar\.gz$//;
    
    my $local_dir = $DBs."/".$number."/";
    print "Running mkdir $number\n";
    mkdir $number;
    
    print "Running tar -xzf ".$file." -C ".$number." ".$number.".fasta\n";
    system("tar -xzf ".$file." -C ".$number." ".$number.".fasta");

    chdir $number;
    print "Running /vol/kbase/runtime/bin/makeblastdb -in ".$number.".fasta -dbtype prot -input_type fasta -out ".$number."\n";
    system("/vol/kbase/runtime/bin/makeblastdb -in ".$number.".fasta -dbtype prot -input_type fasta -out ".$number);
    print "Running tar -czf ../".$file." *\n";
    system("tar -czf ../".$file." *");

    chdir "../";
    system("rm -rf ".$number);
}
