# 1_species_w/_taxid_get_gbifID.py
Reads .csv, filters rows where matched_rank != "Species," renames and reorders columns, and saves results to .tsv file.

Requires [pygbif](https://github.com/gbif/pygbif) to be installed in conda env to grab GBIF ID's from [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c) using GBIF API, and updates the description column of output .tsv with the GBIF speciesKey.


**usage: python 1_species_wo_taxid_get_gbifID.py [path/to/output.csv] [[trimmed_parent_dir_name]_taxonomy_request.tsv]**
- path/to/output.csv = path to user-named output.csv file from [BOLD-to-skim2mito-sample-submission](https://github.com/SchistoDan/BOLD-to-skim2mito-sample-submission?tab=readme-ov-file#2_sample2taxidpy)
- [trimmed_parent_dir_name]_taxonomy_request.tsv = .tsv file containing necessary fields for requesting taxonomic id creation by ENA (see below)

| propsoed_name  | name_type | host | project_id | description |
| --------- | --------- |--------- | --------- | --------- |
| 177658  | Apatania stylata |  | BGE | 1441211 | 
| 177627 | Agapetus iridipennis |  | BGE | 1430666 | 
| 177860 | Diplectrona meridionalis |  | BGE | 1439205 | 

Species with inconsistencies in their GBIF ID's  (i.e. multiple synonymous ID's, those < 95% confdence, or those without 'ACCEPTED' status, or where Class != Insecta, or where MatchType != EXACT) are output to a separate .tsv called [trimmed_parent_dir_name]_gbif_inconsistent.tsv for review.

[trimmed_parent_dir_name]_taxonomy_request.tsv emailed to ENA.






