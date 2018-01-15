#!/usr/bin/env perl
use warnings;
use strict;
use JSON;
my @temp=();
my $header=1;

use fba_tools::fba_toolsImpl;
my $FBAImpl = fba_tools::fba_toolsImpl->new();
my $modelTemplate = $FBAImpl->_get_msobject("ModelTemplate","NewKBaseModelTemplates","PlantModelTemplate");
foreach my $tmplRxn (@{$modelTemplate->templateReactions()}){
    print $tmplRxn->id(),"\t",$tmplRxn->reaction()->id(),"\t",$tmplRxn->type(),"\t",$tmplRxn->reaction()->definition(),"\n";
}

