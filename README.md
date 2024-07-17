# 1_species_w/_taxid_get_gbifID.py
Reads output.csv from [BOLD-to-skim2mito-sample-submission](https://github.com/SchistoDan/BOLD-to-skim2mito-sample-submission?tab=readme-ov-file#2_sample2taxidpy), filters rows where matched_rank != "Species," renames and reorders columns, and saves results to .tsv file.

Requires [pygbif](https://github.com/gbif/pygbif) to be installed in conda env to grab GBIF ID's from [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c) using GBIF API, and updates the description column of output .tsv with the GBIF speciesKey.

Species with inconsistencies in their GBIF ID's are output to a separate .tsv called gbif_inconsistent.tsv for review.

**usage: python 1_species_wo_taxid_get_gbifID.py [path/to/output.csv] [[trimmed_parent_dir_name]_taxonomy_request.tsv]**




