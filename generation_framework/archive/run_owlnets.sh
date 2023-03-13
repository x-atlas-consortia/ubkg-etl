#!/bin/bash

OWLNETS_SCRIPT=./owlnets_script/__main__.py

$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/uberon.owl
$OWLNETS_SCRIPT -c -v http://www.ebi.ac.uk/sbo/exports/Main/SBO_OWL.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/pato.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/obi.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/mp.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/mi.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/hsapdv.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/mi.owl
$OWLNETS_SCRIPT -c -v http://edamontology.org/EDAM.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/doid.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/cl/cl-base.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/cl.owl
$OWLNETS_SCRIPT -c -v http://brg.ai.sri.com/CCO/downloads/cco.owl
$OWLNETS_SCRIPT -c -v https://ccf-ontology.hubmapconsortium.org/ccf.owl
$OWLNETS_SCRIPT -c -v https://ccf-ontology.hubmapconsortium.org/ccf-asctb.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/pr.owl
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/vario.owl
# 'chebi' is at the end because it takes forever to run....
$OWLNETS_SCRIPT -c -v http://purl.obolibrary.org/obo/chebi.owl
echo "*** Done!"
