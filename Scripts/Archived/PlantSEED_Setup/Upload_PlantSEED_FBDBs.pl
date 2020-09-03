#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $output=undef;
my $ua = LWP::UserAgent->new();
my $res = undef;

use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/Workspace/lib/';
use lib '/homes/seaver/Projects/PATRIC_Deploy/dev_container/modules/auth/lib/';
use lib '/homes/seaver/Projects/ModelDeploy/kbapi_common/lib/';
use Bio::P3::Workspace::ScriptHelpers;
use Bio::P3::Workspace::WorkspaceClient;

my $Token_File = "/homes/seaver/Projects/PATRIC_Scripts/Workspace_Scripts/Login_Tokens.txt";
open(FH, "< $Token_File");
my %Tokens=();
while(<FH>){
    chomp;
    @temp=split(/\t/,$_,3);
    $Tokens{$temp[0]}=[$temp[1],$temp[2]];
}

#Set user for this
Bio::P3::Workspace::ScriptHelpers::login({ user_id => 'plantseed', password => $Tokens{'plantseed'}[0] });

my $DBs = "../../DBs/Functional_BLAST_DBs";

my $file = $DBs.".json";
exit if !-f $file;

open(FH, "<", $file);
my $data="";
while(<FH>){
    chomp;
    $data.=$_;
}
close(FH);

Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Functional_Blast_DBs/',"folder"]], overwrite => 1 });
Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Functional_Blast_DBs/lookup',"unspecified",{},$data]], overwrite => 1 });
print "Uploaded $file as functional blast lookup\n";

opendir(my $dh, $DBs);
my @Files = grep { $_ =~ /\.tar\.gz$/ } readdir($dh);
closedir($dh);

foreach my $file (@Files){
    print $DBs."/".$file,"\n" if -f $DBs."/".$file;


    open(FH, "< ".$DBs."/".$file);
    binmode(FH);
 
    $data = undef;
    my $read = undef;
    my $nbytes;
    while ($nbytes = read FH, $read, 128) { $data.=$read }
    close(FH);

    Bio::P3::Workspace::ScriptHelpers::wscall("create",{ objects => [['/plantseed/Functional_Blast_DBs/'.$file,"unspecified",{},$data]], overwrite => 1 });
}
