#!/usr/bin/env perl
use warnings;
use strict;
my $output;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my ($User,$Genome) = ($ARGV[0],$ARGV[1]);
exit if !$ARGV[0] || !$ARGV[1];

print $User,"\t",$Genome,"\n";

#Hard-coded set of files for genome includes
#1) Original Genome object (needs to be correctly identified and stored in $Genome)
#2) minimal_genome object, found in ~/.$Genome/minimal_genome
#3) Sims_n objects where n can be any number. These are found in ~/.$Genome/Sims_n

#A Check for existence of objects

my $PlantSEED_Root = '/plantseed/Genomes';
my @Dir_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$PlantSEED_Root] })->{$PlantSEED_Root}};
my ($HasGenome,$HasDir,$HasMin,$HasSims)=(0,0,0,0);
my @Sims=();
foreach my $entry (@Dir_Contents){
    if($entry->[0] eq $Genome && $entry->[1] eq 'genome'){
	$HasGenome=1;
    }
    if($entry->[0] eq ".".$Genome && $entry->[1] eq 'folder'){
	$HasDir=1;
	my @Gen_Contents = @{Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$PlantSEED_Root."/.".$Genome] })->{$PlantSEED_Root."/.".$Genome}};
	foreach my $gentry (@Gen_Contents){
	    if($gentry->[0] eq "minimal_genome" && $gentry->[1] eq "unspecified"){
		$HasMin=1;
	    }
	    if($gentry->[0] =~ /^(Sims_\d+)$/ && $gentry->[1] eq "unspecified"){
		$HasSims=1;
		push(@Sims,$1);
	    }
	}
    }
}

exit if !$HasGenome || !$HasDir || !$HasMin || !$HasSims || scalar(@Sims)==0;

print join("|",($HasGenome,$HasDir,$HasMin,$HasSims,scalar(@Sims))),"\n";

#B Check that user has PlantSEED directory

my $User_Root = "/".$User."/";
$output = Bio::P3::Workspace::ScriptHelpers::wscall("ls",{ paths => [$User_Root], adminmode=>1 });
if(scalar(keys %$output)==0 || !exists($output->{$User_Root})){
    print STDERR "Cannot access $User's directory\n";
    exit();
}

@Dir_Contents = @{$output->{$User_Root}};
my $HasPS=0;
foreach my $entry (@Dir_Contents){
    if($entry->[0] eq 'plantseed' && $entry->[1] eq 'folder'){
	$HasPS=1;
    }
}
if(!$HasPS){
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [[$User_Root."plantseed",'folder']], adminmode=>1});
}

#C No Check that user has Genome, assuming overwrite all

if($HasPS){

}


__END__

my @path = split(/\//,$file);
my $name = $path[$#path];
$name =~ s/\.json$//;

#Uploading Genome
$output = Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/'.$name,"Genome",{},undef]], createUploadNodes => 1, overwrite => 1 });
my $SHOCK_URL = $output->[0][11];

use HTTP::Request::Common;
local $HTTP::Request::Common::DYNAMIC_FILE_UPLOAD = 1;
my $ua = LWP::UserAgent->new();
my $req = HTTP::Request::Common::POST($SHOCK_URL, 
				      Authorization => "OAuth " . Bio::P3::Workspace::ScriptHelpers::token(),
				      Content_Type => 'multipart/form-data',
				      Content => [upload => [$file]]);
$req->method('PUT');
my $sres = $ua->request($req);
print "Genome uploaded\n";

#Creating Folder
#If it already exists, nothing changes
#Permissions set in top-level folder
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name,"folder"]] });
print "/plantseed/Genomes/.".$name." folder created\n";

#Upload Minimal Genome
$file = join("/",@path[0..$#path-1])."/".$name."_min.json";

open(FH, "<", $file);
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name.'/minimal_genome',"unspecified",{},$data]], overwrite => 1 });
print "Uploaded minimal genome from $file into .$name\n";

#Upload Sims
my $Plants_Root="/homes/seaver/Projects/PATRIC_Scripts/Workshops/2015/";
my $Genomes = $Plants_Root."PlantSEED_Genomes/";
my $JSONs_Dir = $Genomes.$name."/JSONs/";
print STDERR "JSONS not found for $name\n" if !-d $JSONs_Dir;
exit if !-d $JSONs_Dir;

opendir(my $dh, $JSONs_Dir);
my @Sim_Files = grep { $_ =~ /\.json$/ } readdir($dh);
closedir($dh);

foreach my $sim (@Sim_Files){
    open(FH, "<", $JSONs_Dir."/".$sim);
    my $data="";
    while(<FH>){
	chomp;
	$data.=$_;
    }
    close(FH);

    $sim =~ s/\.json//;
    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Genomes/.'.$name.'/'.$sim,"unspecified",{},$data]], overwrite => 1 });
}
print "Uploaded ".scalar(@Sim_Files)." Sim objects into .$name\n";
