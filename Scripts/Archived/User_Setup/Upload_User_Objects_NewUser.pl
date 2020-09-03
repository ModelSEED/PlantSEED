#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;

my %Roles_Subsystems=();
open(FH, "< ".$ENV{SEAVER_PROJECT}."PlantSEED_GitHub/DBs/PlantSEED_Roles.json");
my $data = undef;
while(<FH>){
    $data.=$_;
}
close(FH);

my @Roles = @{from_json($data)};
foreach my $row (@Roles){
    foreach my $ss (keys %{$row->{subsystems}}){
	$Roles_Subsystems{$row->{role}}{$ss}=1;
    }
}

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use Bio::P3::Workspace::ScriptHelpers;

my $Token_File = "/homes/seaver/Projects/PATRIC_Scripts/Workspace_Scripts/Login_Tokens.txt";
open(FH, "< $Token_File");
my %Tokens=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,3);
    $Tokens{$temp[0]}=[$temp[1],$temp[2]];
}

my $P3_User = 'seaver';
#Set user for this
Bio::P3::Workspace::ScriptHelpers::login({ user_id => $P3_User, password => $Tokens{$P3_User}[0] });

my $Plants_Root = "/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/User_Genomes/";
my $User = $ARGV[0];
exit if !$User || !-d $Plants_Root.$User;

my $NewUser = $ARGV[1];
exit if !$NewUser;

#A Gather json files
opendir(my $dh, $Plants_Root.$User."/JSONs/");
my %Files = map { $_ => 1 } grep { $_ =~ /\.json$/ } readdir($dh);
closedir($dh);

my $Genome = ( grep { $_ !~ /Sim|min/ } keys %Files)[0];
$Genome =~ s/\.json$//;

my @Sims = sort { substr($a,index($a,'_')+1,index($a,'.')-index($a,'_')) <=> substr($b,index($b,'_')+1,index($b,'.')-index($b,'_')) } grep { $_ =~ /Sims_/ } keys %Files;

#A Check for existence of objects

my $User_Root = "/".$NewUser."/plantseed/genomes";
my @Dir_Contents = Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => ["/".$NewUser], adminmode=>1 })->{"/".$User};
my $MakePS = 0;
if(scalar(@Dir_Contents)==0 || !defined($Dir_Contents[0])){
    $MakePS=1;
}else{
    foreach my $entry (@Dir_Contents){
	my $HasPS=0;
	if($entry->[0][0] eq "plantseed"){
	    $HasPS=1;
	    last;
	}
	$MakePS=1 if !$HasPS;
    }
}

if($MakePS){
    print "Making plantseed directories for $User\n";
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [["/".$NewUser."/plantseed",'folder']], adminmode=>1, setowner=>$NewUser, overwrite=>1});
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root,'folder']], adminmode=>1, setowner=>$NewUser, overwrite=>1});
}

#Add Genome object
my $File = $Plants_Root.$User."/JSONs/".$Genome.".json";
open(FH, "<", $File);
$data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

my $Kmer_File = $Plants_Root.$User."/Files/".$Genome.".fa_Release70_Kmer8";
my %Annotations=();
open(FH, "< $Kmer_File");
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,-1);
    my ($GeneId,$Function) = ($temp[1],$temp[2]);
    next if !defined($Function) || $Function eq "";
    $Annotations{$GeneId}=$Function;
}
close(FH);

my $Genome_obj = from_json($data);
my @Ftrs = @{$Genome_obj->{features}};
for(my $i=0;$i<scalar(@Ftrs);$i++){
    if(!defined($Ftrs[$i]->{function})){
	$Ftrs[$i]->{function}="";
    }

    if(exists($Annotations{$Ftrs[$i]->{id}})){
	$Ftrs[$i]->{function}=$Annotations{$Ftrs[$i]->{id}};
    }

    $Ftrs[$i]->{'subsystems'}={};
    if(defined($Ftrs[$i]->{function}) && $Ftrs[$i]->{function} ne ""){
	my $Function = $Ftrs[$i]->{function};
	$Function = (split(/\s#/,$Function))[0];

	foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$Function)){
	    foreach my $ss (keys %{$Roles_Subsystems{$role}}){
		    $Ftrs[$i]->{'subsystems'}{$ss}=1;
	    }
	}

	$Ftrs[$i]->{function}=$Function;
    }
    $Ftrs[$i]->{'subsystems'}=[keys %{$Ftrs[$i]->{'subsystems'}}];
}
$Genome_obj->{features}=\@Ftrs;
$Genome_obj->{scientific_name}=$Genome;
$Genome_obj->{taxonomy}=$Genome;
$Genome_obj->{domain}="Plant";
$data = to_json($Genome_obj);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/'.$Genome,"genome",{},$data]], overwrite => 1, adminmode => 1, setowner=>$NewUser });
print "Genome uploaded\n";

#Creating Genome folder
#If it already exists, nothing changes
#Permissions set in top-level folder
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/.'.$Genome,"folder"]], adminmode=>1, setowner=>$NewUser });
print "Genome folder created\n";

#Add Minimal Genome object
$File = $Plants_Root.$User."/JSONs/".$Genome."_min.json";
open(FH, "<", $File);
$data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

my $Min_Genome_obj = from_json($data);
@Ftrs = @{$Min_Genome_obj->{features}};
for(my $i=0;$i<scalar(@Ftrs);$i++){
    if(!defined($Ftrs[$i]->{function})){
	$Ftrs[$i]->{function}="";
    }

    if(exists($Annotations{$Ftrs[$i]->{id}})){
	$Ftrs[$i]->{function}=$Annotations{$Ftrs[$i]->{id}};
    }

    $Ftrs[$i]->{'subsystems'}={};
    if(defined($Ftrs[$i]->{function}) && $Ftrs[$i]->{function} ne ""){
	my $Function = $Ftrs[$i]->{function};
	$Function = (split(/\s#/,$Function))[0];

	foreach my $role (split(/\s*;\s+|\s+[\@\/]\s+/,$Function)){
	    foreach my $ss (keys %{$Roles_Subsystems{$role}}){
		    $Ftrs[$i]->{'subsystems'}{$ss}=1;
	    }
	}

	$Ftrs[$i]->{function}=$Function;
    }
    $Ftrs[$i]->{'subsystems'}=[keys %{$Ftrs[$i]->{'subsystems'}}];
}
$Min_Genome_obj->{features}=\@Ftrs;
$data = to_json($Min_Genome_obj);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/.'.$Genome."/minimal_genome","unspecified",{},$data]],
						     overwrite => 1, adminmode => 1, setowner=>$NewUser });
print "Minimal Genome uploaded\n";

#Upload Sims
foreach my $sim (@Sims){
    $File = $Plants_Root.$User."/JSONs/".$sim;
    open(FH, "< $File");
    $data="";
    while(<FH>){
	chomp;
	$data.=$_;
    }
    close(FH);

    $sim =~ s/\.json//;
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root.'/.'.$Genome."/".$sim,"unspecified",{},$data]], 
							 overwrite=>1, adminmode=>1, setowner=>$NewUser });
}
print "Uploaded ".scalar(@Sims)." Sim objects\n";
