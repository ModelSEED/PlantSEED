#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my $JSON=undef;
my @temp=undef;

open(FH, "< ../../Core_Plant_Metabolism/PlantSEED_Roles_v2_Curated.json");
while(<FH>){$JSON.=$_;}close(FH);
$JSON=from_json($JSON);

#Unlink_Roles.txt
open(FH, "< Unlink_Roles.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    foreach my $row (@$JSON){
	if($row->{role} eq $temp[0]){
	    foreach my $rxn (split(/\|/,$temp[1])){
		delete($row->{reactions}{$rxn});
	    }
	}
    }
}
close(FH);

#Overwrite_Reactions.txt
open(FH, "< Overwrite_Reactions.txt");
my %Reactions_Removed=();
my %Roles_Updated=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    foreach my $row (@$JSON){
	if($row->{role} eq $temp[0]){
	    my %Cpts=();
	    foreach my $rxn (keys %{$row->{reactions}}){
		foreach my $cpt (@{$row->{reactions}{$rxn}{"cmpts"}}){
		    $Cpts{$cpt}=1;
		}
	    }
	    foreach my $rxn (keys %{$row->{reactions}}){
		$Reactions_Removed{$rxn}{$row->{role}}={};
		$Roles_Updated{$row->{role}}{'remove'}{$rxn}={};
	    }
	    delete($row->{reactions});

	    foreach my $rxn (split(/\|/,$temp[1])){
		$row->{reactions}{$rxn}{"cmpts"}=[sort keys %Cpts];
		$Roles_Updated{$row->{role}}{'add'}{$rxn}={};
	    }
	}
    }
}
close(FH);

open(OUT, "> __Updated_Roles.json");
print OUT to_json(\%Roles_Updated,{pretty=>1}),"\n";
close(OUT);

#Check for removed reaction in other roles
foreach my $row (@$JSON){
    foreach my $rxn (keys %{$row->{reactions}}){
	if(exists($Reactions_Removed{$rxn})){
	    print "Keeping: ",$row->{role},"\t",$rxn,"\n";
	    delete($Reactions_Removed{$rxn});
	}
    }
}

open(OUT, "> __Removed_Reactions.txt");
print OUT join("\n",sort keys %Reactions_Removed),"\n";
close(OUT);

#Replace_Roles.txt
open(FH, "< Replace_Roles.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    foreach my $row (@$JSON){
	if($row->{role} eq $temp[0]){
	    $row->{role} = $temp[1];
	}
    }
}
close(FH);

#Add_Roles.txt
open(FH, "< Add_Roles.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    my %row = ("role"=>$temp[0],"reactions"=>{},"features"=>{});

    foreach my $rxn (split(/\|/,$temp[1])){
	$row{"reactions"}{$rxn}{"cmpts"}=[];
    }

    foreach my $ftr (split(/\|/,$temp[2])){
	my ($id,$source,$cpt) = split(/:/,$ftr);
	foreach my $sou (split(/;/,$source)){
	    $row{"features"}{$id}{$sou}{$cpt}=1;
	}
    }
    push(@$JSON,\%row);
}
close(FH);

#Add_Roles_to_Group.txt
open(FH, "< Add_Roles_to_Group.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    foreach my $row (@$JSON){
	if($row->{role} eq $temp[0]){
	    foreach my $group (split(/\|/,$temp[2])){
		$row->{$temp[1]}{$group}=1;
	    }
	}
    }
}
close(FH);

#Merge_Features.txt
my %Remove_Role=();
my %Update_Role=();
open(FH, "< Merge_Features.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    foreach my $row (@$JSON){
	if($row->{role} eq $temp[0]){
	    $Remove_Role{$row->{role}}=1;
	    $Update_Role{$temp[1]}=$row->{features};
	}
    }    
}
close(FH);

foreach my $role (keys %Update_Role){
    foreach my $row (@$JSON){
	if($row->{role} eq $role){
	    foreach my $ftr (keys %{$Update_Role{$role}}){
		if(!exists($row->{features}{$ftr})){
		    $row->{features}{$ftr}=$Update_Role{$role}{$ftr};
		}
	    }
	}
    }    
}

#Remove_Roles.txt
open(FH, "< Remove_Roles.txt");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_);

    $Remove_Role{$temp[0]}=1;
}
close(FH);

my @New_Roles=();
my %Found=();
foreach my $row (@$JSON){
    if(!exists($Remove_Role{$row->{role}})){
	push(@New_Roles,$row);
    }
}

#open(OUT, "> ../../Core_Plant_Metabolism/PlantSEED_Roles_v2.5.bak");
open(OUT, "> ../../Core_Plant_Metabolism/PlantSEED_Roles_v2.5.json");
print OUT to_json(\@New_Roles,{pretty=>1}),"\n";
close(OUT);
