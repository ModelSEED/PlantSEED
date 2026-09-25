# AOP3 side-chain hydroxylation — balancing the two reactions

AOP3 (`AT4G03050`) hydroxylates methylsulfinylalkyl glucosinolates, cleaving off
methanesulfonate. Both reactions on this role were written as bare skeletons —
substrate in, product out, with the leaving group omitted — so both carried the
imbalance `MI:C:-1/H:-2/S:-1`, which is exactly one CH3SO3- group, and both were
excluded from the template by the balance check.

## 3-hydroxypropyl: swap the reaction

`rxn23786` and `rxn44212` are the same MetaCyc reaction, RXN-2223. `rxn44212`
is the correctly written form and is already balanced (status OK), so the fix is
to assign it and drop the skeleton.

    rxn23786  Glucoiberin -> 3-hydroxypropyl-GSL                        MI:C:-1/H:-2/S:-1
    rxn44212  H2O + O2 + Glucoiberin -> H+ + methanesulfonate
              + 3-hydroxypropyl-GSL                                     OK

## 4-hydroxybutyl: fix the reaction in place

`rxn27065` has the identical defect but is MetaCyc RXNQT-4340, with no correctly
written twin to swap in. It is therefore repaired with the same four reagents
that `rxn44212` carries:

    H2O -1,  O2 -1,  H+ +1,  methanesulfonate +1

Verified: as deposited the reaction is off by {C:-1, H:-2, S:-1}; with these four
added it balances exactly, atoms {} and charge 0, matching `rxn44212`.

Scoped to `rxn27065` so the override cannot touch `rxn44212`, which already
carries those reagents.

This should be reported upstream — RXNQT-4340 wants the same treatment RXN-2223
already received in ModelSEED, at which point these four rows become redundant.

## Dependency

Neither reaction can carry flux without a methanesulfonate sink; see
`Curators/samseaver/methanesulfonate_sink_260917/`.

## Note on addressing

The two `ADD reactions` rows use the ROLE name, which carries the `(no EC)`
suffix. The four `CPX_ADD` rows use the complex's `abstract_enzyme`, which does
NOT — complexes are keyed on abstract_enzyme, not role name. Getting this wrong
produces a skipped-with-warning, not an error.
