# ena_taxonomy_request.py
Reads [sample2taxid].csv (see [sample-processing repo](https://github.com/SchistoDan/sample-processing)), filters rows where matched_rank != "Species", renames and reorders columns based on taxonomy request spreadsheet requirements, and outputs results to .tsv file to be emailed to ENA for taxid creation.

Requires [pygbif](https://github.com/gbif/pygbif) be installed in conda env to grab GBIF ID's from [GBIF Backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c) using API.


**usage: python ena_taxonomy_request.py [path/to/sample2taxid.csv] taxonomy_request.tsv species_output.csv**
- path/to/[sample2taxid].csv = path to user-named output.csv file from [sample-processing repo](https://github.com/SchistoDan/sample-processing).
- taxonomy_request.tsv = .tsv file containing necessary fields for requesting taxonomic id creation by ENA. Can be named anything (see below).
- specis_output.csv = .csv file containing rows from sample2taxid.csv where matched_rank == 'species'.

| proposed_name  | name_type | host | project_id | description |
| --------- | --------- |--------- | --------- | --------- |
| 177658  | Apatania stylata |  | BGE: [Process ID] | https://www.gbif.org/species/[GBIF ID] | 
| 177627 | Agapetus iridipennis |  | BGE: [Process ID] | https://www.gbif.org/species/[GBIF ID] | 
| 177860 | Diplectrona meridionalis |  | BGE: [Process ID] | https://www.gbif.org/species/[GBIF ID] | 

Species with inconsistencies in their GBIF ID's output to gbif_inconsistent.tsv for review. Parameter thresholds for 'inconsistent GBIF IDs):
- Multiple synonymous GBIF ID's
- < 95% confidence (for species-level), or < 90% (for genus-level)
- Without 'ACCEPTED' status
- MatchType != EXACT

**taxonomy_request.tsv emailed to ENA to request species-level taxID creation**

## TO DO ##

GBIF ID inconsistency example:

| usageKey |	scientificName |	canonicalName |	rank |	status |	confidence |	matchType |	kingdom |	phylum | order |	family |	genus |	species |	kingdomKey |	phylumKey |	classKey |	orderKey |	familyKey |	genusKey |	speciesKey |	synonym |	class |	index	| acceptedUsageKey |
| --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- | --- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	--- |	---	| --- |
| 8753555	| Erotesis melanella McLachlan, 1884 | Erotesis melanella	| SPECIES	| SYNONYM	| 98	| EXACT	| Animalia	| Arthropoda |	Trichoptera |	Leptoceridae |	Adicella |	Adicella melanella |	1 |	54 |	216 | 1003	| 4395	| 1436670	| 1436745	| True |	Insecta	| 5	| 1436745 |

  - Erotesis melanella McLachlan, 1884 == [8753555](https://www.gbif.org/species/8753555)
  - Adicella melanella (McLachlan, 1884) == [1436745](https://www.gbif.org/species/1436745)
