#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp = ();
my $header = 1;

#Collect Subsystems
open(FH, "< ../DBs/Subsystems_Classes_Pathways.txt");
my %Subsystems=();
my %Pathways=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    $Subsystems{$temp[1]}{class}{$temp[0]}=1;
    $Subsystems{$temp[1]}{path}{$temp[2]}=1;
    $Pathways{$temp[2]}{class}{$temp[0]}=1;
    $Pathways{$temp[2]}{ss}{$temp[1]}=1;
}
close(FH);

my %Expanded_Rxns=();
open(FH, "< ../DBs/Expanded_BioCyc_Aliases.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    my $source = shift(@temp);
    my $base_rxn = shift(@temp);

    next unless $source eq "AraCyc" || $source eq "MetaCyc";

    foreach my $rxns (@temp){
        my ($exp_rxn,$ms_rxn)=split(/:/,$rxns);
        $Expanded_Rxns{$source}{$base_rxn}{$exp_rxn}=$ms_rxn;
    }
}
close(FH);

my %Map_Files=();
foreach my $dir ("Subsystem","Table1"){
    opendir(my $dh, $ENV{SEAVER_PROJECT}."UF_Subsystems/Initial_".$dir."_Mappings/");
    foreach my $file ( grep { /\.txt$/ }  readdir($dh) ){
	$Map_Files{$file}=$dir;
    }
    closedir($dh);
}

my %RolesSSs=();
my %RolesRxns=();
foreach my $file(keys %Map_Files){
    $file =~ /^(.*)\.txt$/;
    my $Pwy = $1;

    my %Subsystem=();
    foreach my $ss (keys %Subsystems){
	foreach my $pwy (keys %{$Subsystems{$ss}{path}}){
	    if($Pwy eq $pwy){
		$Subsystem{$ss}=1;
	    }
	}
    }

    open(FH, "< ".$ENV{SEAVER_PROJECT}."UF_Subsystems/Initial_".$Map_Files{$file}."_Mappings/".$file);
    while(<FH>){
	chomp;
	@temp=split(/\t/,$_,-1);

	next if $temp[0] eq "Spont" || $temp[0] eq "None";

	foreach my $SS (keys %Subsystem){
	    if($temp[0] eq "No Genes Found"){
		foreach my $role (split(/\|;\|/,$temp[1])){
		    next if $role eq "None";
		    $Subsystems{$SS}{roles}{$role}=1;
		    $RolesSSs{$role}{$SS}=1;
		}
	    }else{
		$Subsystems{$SS}{roles}{$temp[0]}=1;
		$RolesSSs{$temp[0]}{$SS}=1;

		foreach my $rxn (split(/\|/,$temp[1])){
		    if(exists($Expanded_Rxns{AraCyc}{$rxn})){
			foreach my $exprxn (keys %{$Expanded_Rxns{AraCyc}{$rxn}}){
			    $RolesRxns{$temp[0]}{$Expanded_Rxns{AraCyc}{$rxn}{$exprxn}}=1;
			}
		    }elsif(exists($Expanded_Rxns{MetaCyc}{$rxn})){
			foreach my $exprxn (keys %{$Expanded_Rxns{MetaCyc}{$rxn}}){
			    $RolesRxns{$temp[0]}{$Expanded_Rxns{MetaCyc}{$rxn}{$exprxn}}=1;
			}
		    }else{
#			print $_,"\n";
		    }
		}
	    }
	}
    }
}

my %Evidence = ();
open(FH, "< ".$ENV{SEAVER_PROJECT}."Cyc/Ara/Output/Ara_EnzRxn_EXP_Evidence.txt");
while(<FH>){
    chomp;
    my ($enzrxn, $cpx, $classes, $evd_codes, $rxn, $genes) = split(/\t/,$_,6);

    my %Gene_Rxn_Codes=();
    my %Codes=();
    foreach my $class (split(/\|/,$classes)){
	foreach my $code (split(/\|/,$evd_codes) ){
	    $Codes{$code}=1;
	    $Gene_Rxn_Codes{$class}{$code}=1 if $code =~ /$class/;
	}
    }

    #Discard association if zero evidence
    next if scalar(keys %Gene_Rxn_Codes)==0;

    #Consider discarding association if only evidence is "COMP" or "AS" or both
    if(scalar( grep { $_ ne "COMP" && $_ ne "AS" } keys %Gene_Rxn_Codes)==0){

	#Discard association if doesn't contains human inference
	if(!exists($Gene_Rxn_Codes{COMP}) || scalar( grep { $_ =~ /HINF/ } keys %{$Gene_Rxn_Codes{COMP}})==0){
	    next;
	}
    }

    foreach my $gene ( grep { $_ !~ /peg/ } split(/\|/, $genes )){
	$gene =~ s/\.\d+$//;
	$Evidence{$gene}=1;
    }
}
close(FH);

open(FH, "< ../DBs/PlantSEED_Kmers.out");
my %Kmer_Roles = ();
my $Ftr = undef;
my $Function = undef;
while(<FH>){
    chomp;

    if($_ =~ /^#/){
	#Parse Kmers
#	next if !$Function;
#	my ($hash,$score1,$kmer,$function,$species,$score2,$score3) = split(/\t/,$_,7);
#	next unless $function eq $Function;
#	$Functions{$Function}{'kmers'}{$kmer}=1;
    }else{
#	last if $Ftr;
	
	$Ftr = undef;
	$Function = undef;

	#Parse functions
	my ($ftr,$function,$score,$no_hits,$o_hits,$figfam) = split(/\t/,$_,6);
	$figfam =~ s/\s+$//;

	foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$function)){
	    $Kmer_Roles{$role}{'features'}{$ftr}=1;
	    $Kmer_Roles{$role}{'figfams'}{$figfam}=1 if $figfam;
	}

	$Ftr = $ftr;
	$Function = $function;
    }
}
close(FH);

my %PlantSEED_Roles = ();
open(FH, "< ../DBs/Primary_PlantSEED_Annotation.txt");
$header = 1;
while(<FH>){
    chomp;
    if($header){$header--;next}
    my @temp=split(/\t/,$_,-1);
    my $role = $temp[0];

    $PlantSEED_Roles{$role} = {'role' => $role, 'features' => {}, 
			       'subsystems' => {}, 'classes' => {},
			       'pathways' => {}, 'reactions' => {}} if !exists($PlantSEED_Roles{$role});

    foreach my $ftr (split(/\|/,$temp[2])){
	$PlantSEED_Roles{$role}{'features'}{$ftr}=1;
    }
    
    if(exists($RolesSSs{$role})){
	foreach my $ss (keys %{$RolesSSs{$role}}){
	    $PlantSEED_Roles{$role}{'subsystems'}{$ss}=1;
	    foreach my $path (keys %{$Subsystems{$ss}{path}}){
		$PlantSEED_Roles{$role}{'pathways'}{$path}=1;
	    }
	    foreach my $class (keys %{$Subsystems{$ss}{class}}){
		$PlantSEED_Roles{$role}{'classes'}{$class}=1;
	    }
	}
    }
   
    if(exists($RolesRxns{$role})){
	foreach my $rxn (keys %{$RolesRxns{$role}}){
	    $PlantSEED_Roles{$role}{'reactions'}{$rxn}=1;
	}
    }else{
#	print $role,"\n";
    }
}
close(FH);

open(FH, "< ../DBs/Empty_Roles.txt");
while(<FH>){
    chomp;
    my @temp=split(/\t/,$_,-1);
    my $role = $temp[0];
    $PlantSEED_Roles{$role} = {'role' => $role, 'features' => {}, 
			       'subsystems' => {}, 'classes' => {},
			       'pathways' => {}, 'reactions' => {}} if !exists($PlantSEED_Roles{$role});
    
    if(exists($RolesSSs{$role})){
	foreach my $ss (keys %{$RolesSSs{$role}}){
	    $PlantSEED_Roles{$role}{'subsystems'}{$ss}=1;
	    foreach my $path (keys %{$Subsystems{$ss}{path}}){
		$PlantSEED_Roles{$role}{'pathways'}{$path}=1;
	    }
	    foreach my $class (keys %{$Subsystems{$ss}{class}}){
		$PlantSEED_Roles{$role}{'classes'}{$class}=1;
	    }
	}
    }
   
    if(exists($RolesRxns{$role})){
	foreach my $rxn (keys %{$RolesRxns{$role}}){
	    $PlantSEED_Roles{$role}{'reactions'}{$rxn}=1;
	}
    }else{
#	print $role,"\n";
    }
}
close(FH);

open(FH, "< ../DBs/Secondary_PlantSEED_Annotation.txt");
$header = 1;
while(<FH>){
    chomp;
    if($header){$header--;next}
    my @temp=split(/\t/,$_,-1);
    my $role = $temp[0];
    next if !exists($Kmer_Roles{$role});
    
    my $isEvidenced = [];
    foreach my $gene (split(/\|/,$temp[2])){
	if(exists($Evidence{$gene})){
	    push(@$isEvidenced,$gene)
	}
    }
    next if scalar(@$isEvidenced)==0;

    next if !exists($RolesRxns{$role});

    foreach my $rxn (keys %{$RolesRxns{$role}}){
	$PlantSEED_Roles{$role}{'reactions'}{$rxn}=1;
    }
}

#open(OUT, "> Missing_Reactions.txt");
#print OUT join("\n",sort grep { scalar(keys %{$PlantSEED_Roles{$_}{'reactions'}})==0 } keys %PlantSEED_Roles),"\n";
#close(OUT);
 
my @PlantSEED_Roles = map { $PlantSEED_Roles{$_} } sort keys %PlantSEED_Roles;

my %Spont_SSs=();
open(FH, "< ../DBs/Spontaneous_Reactions.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    next unless $temp[2] eq "Subsystem";

    foreach my $rxn (split(/\|/,$temp[1])){
	foreach my $path (split(/\|/,$temp[3])){
	    $path =~ s/\.txt//;
	    foreach my $ss (keys %{$Pathways{$path}{ss}}){
		$Spont_SSs{$ss}{$rxn}=1;
	    }
	}
    }
}

my $role = "Spontaneous Reaction";
foreach my $ss (keys %Spont_SSs){
    my $hash = {'role' => $role, 'features' => {}, 
		'subsystems' => { $ss=>1 }, 'classes' => {},
		'pathways' => {}, 'reactions' => {}};
    
    foreach my $rxn (keys %{$Spont_SSs{$ss}}){
	$hash->{reactions}{$rxn}=1;
    }

    foreach my $path (keys %{$Subsystems{$ss}{path}}){
	$hash->{pathways}{$path}=1;
    }

    foreach my $path (keys %{$Subsystems{$ss}{class}}){
	$hash->{classes}{$path}=1;
    }
    push(@PlantSEED_Roles,$hash);
}

open(OUT, "> ../DBs/PlantSEED_Roles.json");
print OUT to_json(\@PlantSEED_Roles, {pretty=>1, ascii =>1});
close(OUT);
