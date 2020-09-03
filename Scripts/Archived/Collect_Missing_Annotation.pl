#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp = ();
my $header = 1;

my %Map_Files=();
foreach my $dir ("Subsystem","Table1"){
    opendir(my $dh, $ENV{SEAVER_PROJECT}."UF_Subsystems/Initial_".$dir."_Mappings/");
    foreach my $file ( grep { /\.txt$/ }  readdir($dh) ){
	$Map_Files{$file}=$dir;
    }
    closedir($dh);
}

open(FH, "< ../DBs/Expanded_BioCyc_Aliases.txt");
my %Aliases=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    my $rxn = shift(@temp);
    foreach my $tmp (@temp){
	my ($cyc_rxn,$ms_rxn)=split(/:/,$tmp);
	$Aliases{$rxn}{$ms_rxn}=1;
    }
}
close(FH);

my %Empty_Roles=();
my %Spontaneous_Reactions=();
foreach my $file(keys %Map_Files){
    $file =~ /^(.*)\.txt$/;

    open(FH, "< ".$ENV{SEAVER_PROJECT}."UF_Subsystems/Initial_".$Map_Files{$file}."_Mappings/".$file);
    while(<FH>){
	chomp;
	@temp=split(/\t/,$_,-1);

	if($temp[0] eq "Spont"){
	    foreach my $rxn (split(/\|/,$temp[1])){
		foreach my $ms_rxn(keys %{$Aliases{$rxn}}){
		    $Spontaneous_Reactions{$rxn}{ms}{$ms_rxn}=1;
		}
		$Spontaneous_Reactions{$rxn}{source}{$Map_Files{$file}}=1;
		$Spontaneous_Reactions{$rxn}{pathway}{$file}=1;
	    }
	}

	if($temp[0] eq "No Genes Found"){
	    foreach my $role (split(/\|;\|/,$temp[1])){
		next if $role eq "None";
		$Empty_Roles{$role}{$Map_Files{$file}}=1;
	    }
	}
    }
}

open(OUT, "> ../DBs/Spontaneous_Reactions.txt");
print OUT join("\n", map { $_."\t".join("|",sort keys %{$Spontaneous_Reactions{$_}{ms}})."\t".join("|",sort keys %{$Spontaneous_Reactions{$_}{source}})."\t".join("|",sort keys %{$Spontaneous_Reactions{$_}{pathway}}) } sort keys %Spontaneous_Reactions),"\n";
close(OUT);

open(OUT, "> ../DBs/Empty_Roles.txt");
print OUT join("\n", map { $_."\t".join("|",sort keys %{$Empty_Roles{$_}}) } sort keys %Empty_Roles),"\n";
close(OUT);
