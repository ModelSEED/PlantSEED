# Methanesulfonate efflux — unblocking the AOP side-chain modifications

Methanesulfonate (`cpd08023`) is released by every AOP-family side-chain
modification of an aliphatic glucosinolate:

    rxn23785   glucoiberin   -> sinigrin              + methanesulfonate
    rxn27066   glucoraphanin -> gluconapin            + methanesulfonate
    rxn44212   glucoiberin   -> 3-hydroxypropyl-GSL   + methanesulfonate

Nothing in the reconstruction consumes it, so at steady state none of those
reactions can carry flux. One dead-end byproduct gates the whole family.

Its metabolic fate in Arabidopsis is not known, so no degradation route can be
curated honestly. Instead this gives it an efflux: `rxn08960` is a plain
cytosol<->extracellular transport of methanesulfonate, status OK. Once it can
leave the cell the standard exchange machinery provides the sink, and the AOP
reactions are free to carry flux.

This follows the existing PlantSEED pattern for exactly this situation — see
`Ammonia transport`, `Carbon dioxide transport`, `Carbon monoxide transport`:
gene-less, `type: universal`, `is_transporter: true`, filed under
`Media_transport`. The transporter is unidentified, which is why the role has no
features; that is the same position as those three.

NOTE this does not by itself make sinigrin appear, and should not. Sinigrin is
2-propenyl glucosinolate, made from glucoiberin by AOP2 (`AT4G03060`) — which
UniProt annotates for Col-0 as "Probable INACTIVE 2-oxoglutarate-dependent
dioxygenase AOP2". Col-0 does not accumulate alkenyl glucosinolates, and
sinigrin is absent from the 21 measured Col-0 compounds. See the gap notes.
