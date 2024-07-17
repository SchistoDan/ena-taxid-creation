Reads output.csv from [BOLD-to-skim2mito-sample-submission](https://github.com/SchistoDan/BOLD-to-skim2mito-sample-submission?tab=readme-ov-file#2_sample2taxidpy), filters rows where matched_rank != "Species," renames and reorders columns, and saves results to .tsv file.

Requires use of [pygbif](https://github.com/gbif/pygbif) to grab GBIF ID's from [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c) using GBIF API, and updates the description column of output .tsv with the GBIF speciesKey.

Species with inconsistencies in their GBIF ID's are output to a separate .tsv called gbif_inconsistent.tsv for review.


