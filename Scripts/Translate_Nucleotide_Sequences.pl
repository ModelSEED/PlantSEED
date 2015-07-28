#!/usr/bin/env perl
use warnings;
use strict;

use FIG;
use gjoseqlib;

my $file = $ARGV[0];
exit if !$file || !-f $file;

my @seqs = gjoseqlib::read_fasta($file);
foreach my $seq (@seqs){
    $seq->[2]=gjoseqlib::translate_seq($seq->[2]);
}

gjoseqlib::write_fasta($file.".protSeq",@seqs);
