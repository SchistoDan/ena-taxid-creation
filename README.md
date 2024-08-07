# 1_species_wo_taxid_get_gbifID.py
Reads [sample2taxid].csv (see [sample-processing repo](https://github.com/SchistoDan/sample-processing)), filters rows where matched_rank != "Species", renames and reorders columns based on taxonomy request spreadsheet requirements, and outputs results to .tsv file.

Requires [pygbif](https://github.com/gbif/pygbif) be installed in conda env to grab GBIF ID's from [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c) using API.


**usage: python 1_species_wo_taxid_get_gbifID.py [path/to/sample2taxid.csv] [trimmed_parent_dir_name]_taxonomy_request.tsv**
- path/to/[sample2taxid].csv = path to user-named output.csv file from [sample-processing repo](https://github.com/SchistoDan/sample-processing).
- [trimmed_parent_dir_name]_taxonomy_request.tsv = .tsv file containing necessary fields for requesting taxonomic id creation by ENA (see below)

| proposed_name  | name_type | host | project_id | description |
| --------- | --------- |--------- | --------- | --------- |
| 177658  | Apatania stylata |  | BGE | 1441211 | 
| 177627 | Agapetus iridipennis |  | BGE | 1430666 | 
| 177860 | Diplectrona meridionalis |  | BGE | 1439205 | 

Species with inconsistencies in their GBIF ID's (i.e. multiple synonymous ID's, those < 95% confdence, without 'ACCEPTED' status, where Class != Insecta, or where MatchType != EXACT) are output to a separate .tsv called [trimmed_parent_dir_name]_gbif_inconsistent.tsv for review.

**[trimmed_parent_dir_name]_taxonomy_request.tsv emailed to ENA to request species-level taxID creation**

## TO DO ##
- Figure out what to do when GBIF IDs are inconsistent.
- Parse new taxIDs created by ENA to file. Currently unsure how new taxIDs will be returned by ENA after creation, and how to get them into ENA sample registration form for sample accession number creation (if even necessary).

GBIF ID inconsistency example:

| usageKey |	scientificName |	canonicalName |	rank |	status |	confidence |	matchType |	kingdom |	phylum | order |	family |	genus |	species |	kingdomKey |	phylumKey |	classKey |	orderKey |	familyKey |	genusKey |	speciesKey |	synonym |	class |	index	| acceptedUsageKey |
| --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- | --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	---	| --- |
| 8753555	| Erotesis melanella McLachlan, 1884 | Erotesis melanella	| SPECIES	| SYNONYM	| 98	| EXACT	| Animalia	| Arthropoda |	Trichoptera |	Leptoceridae |	Adicella |	Adicella melanella |	1 |	54 |	216 | 1003	| 4395	| 1436670	| 1436745	| True |	Insecta	| 5	| 1436745 |

  - Erotesis melanella McLachlan, 1884 == [8753555](https://www.gbif.org/species/8753555)
  - Adicella melanella (McLachlan, 1884) == [1436745](https://www.gbif.org/species/1436745)








