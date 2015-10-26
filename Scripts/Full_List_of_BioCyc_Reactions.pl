#!/usr/bin/env perl
use warnings;
use strict;
my @temp=();
my $header=1;

#######################################################
#Initialization
#######################################################

use Bio::KBase::fbaModelServices::ScriptHelpers qw( getToken );
my $AToken = getToken();

use Bio::KBase::fbaModelServices::Impl;
my $FBAImpl = Bio::KBase::fbaModelServices::Impl->new({'workspace-url' => "http://kbase.us/services/ws"});
$FBAImpl->_setContext(undef,{auth=>$AToken});

my $templateObj = $FBAImpl->_get_msobject("ModelTemplate","KBaseTemplateModels",'PlantModelTemplate');
my $bioObj = $FBAImpl->_get_msobject("Biochemistry",$templateObj->biochemistry_ref());

#my %Empty_Rxns = map { $_->id() => 1 } grep { scalar(@{$_->reagents()})==0 } @{$bioObj->reactions()};

#######################################################
#Collect All Reactions
#######################################################
my $aliasSet=$bioObj->reactionsByAlias();
my %Rxn_Aliases=();
foreach my $source (keys %$aliasSet){
    next unless $source =~ /Cyc/;
    my $Aliases = $aliasSet->{$source};
    foreach my $alias (keys %$Aliases){
	foreach my $rxn_id (keys %{$Aliases->{$alias}}){
#	    next if exists($Empty_Rxns{$rxn_id}); #IMPORTANT: IGNORE EMPTY REACTIONS
	    $Rxn_Aliases{$source}{$alias}{$rxn_id}=1;
	}
    }
}

########################
#Collect BioCyc Reactions
########################
open(OUT, "> ../DBs/Expanded_BioCyc_Aliases.txt");
foreach my $source (keys %Rxn_Aliases){
    my %Base_BioCyc_Aliases=();
    foreach my $alias (keys %{$Rxn_Aliases{$source}}){
	my $mcrxn=$alias;
	if($alias =~ /^(.*)\.([a-z]{1,2})(\.[a-z]+exp\..+)?$/){
	    $mcrxn=$1;
	}

	if($bioObj->getObjectByAlias("reactions",$alias,$source)){
	    foreach my $rxn (keys %{$Rxn_Aliases{$source}{$alias}}){
		$Base_BioCyc_Aliases{$mcrxn}{$rxn}=1;
	    }
	}
    }

    #Remove prior set of aliases
    delete($Rxn_Aliases{$source});

    my %Expanded_BioCyc_Aliases=();
    foreach my $rxn ( keys %Base_BioCyc_Aliases ){
	my $quoteRxn=quotemeta($rxn);
	
	my %Tmp_Expanded_Aliases=();
	foreach my $id (keys %{$Base_BioCyc_Aliases{$rxn}}){
	    my %Tmp_Aliases=();
	    foreach my $alias ( grep { $_ =~ /$quoteRxn/ } @{$bioObj->getObjectByAlias("reactions",$id,"ModelSEED")->getAliases($source)} ){
		$Tmp_Aliases{$alias}=1;
	    }
	    
	    foreach my $alias (keys %Tmp_Aliases){
		$Tmp_Expanded_Aliases{$alias}{$id}=1;
	    }
	}
    
	if(scalar( grep { $_ =~ /exp/ } keys %Tmp_Expanded_Aliases)>0){
	    my @BaseRxns = grep { $_ !~ /exp/ } keys %Tmp_Expanded_Aliases;
	
	    foreach my $base_rxn ( @BaseRxns ){
		delete($Tmp_Expanded_Aliases{$base_rxn});
	    }
	}

	foreach my $alias (keys %Tmp_Expanded_Aliases){
	    foreach my $id (keys %{$Tmp_Expanded_Aliases{$alias}}){
		$Expanded_BioCyc_Aliases{$rxn}{$alias}{$id}=1;
		$Rxn_Aliases{$source}{$alias}{$id}=1;
	    }
	}
    }

    foreach my $base_rxn (sort keys %Expanded_BioCyc_Aliases){
	print OUT $source,"\t",$base_rxn,"\t",join("\t", map { $_.":".join("|",sort keys %{$Expanded_BioCyc_Aliases{$base_rxn}{$_}}) } sort keys %{$Expanded_BioCyc_Aliases{$base_rxn}}),"\n";
    }
}
close(OUT);
