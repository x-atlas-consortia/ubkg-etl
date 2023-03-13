#!/usr/bin/env python
# coding: utf-8

# Obtain "edges and nodes" files to ingest an ontology (set of assertions) into the UBKG.
# The formats for the files are described in the UBKG user guide in the source repo.

# Unlike ontologies that are available as either OWL files or SimpleKnowledge format, the "edges and nodes"
# files will be obtained from a file location and ingested directly, without conversions to OWLNETS format.

# The file location is currently planned to be a Globus collection.

# TO DO:
# Connect to Globus collection.
# Fetch files in location indicated by parameters.
# Write to owlnets_output folder for conversion to CSV.
# Python logging.

