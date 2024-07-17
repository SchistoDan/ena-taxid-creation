#Initially reads input CSV, filters rows where matched_rank is not "species," renames and reorders columns, and saves the intermediate result to a temporary TSV file.
#resolve_names_and_update_file function uses pygbif library to grab gbif id's from GBIF, and updates the description column with the GBIF speciesKey.
#Updated DataFrame saved to taxaonomy_request.tsv
#Rows with inconsistencies in GBIF ID are saved to a separate gbif_inconsistent.tsv file.

##pygbif usage - 'from pygbif import species'
	#species.name_backbone(name='Helianthus annuus', kingdom='plants')
	#species.name_backbone(name='Helianthus', rank='genus', kingdom='plants')
	#species.name_backbone(name='Poa', rank='genus', family='Poaceae')




import sys
import os
import pandas as pd
from pygbif import species #NEEDS pygbif INSTALLED IN CONDA ENV TO WORK



def tax_request(input_csv, output_tsv):
    df = pd.read_csv(input_csv)
    
#filter rows where 'matched_rank' does not equal 'species'
    filtered_df = df[df['matched_rank'].str.lower() != 'species']
    
#select necessary columns and rename them
    selected_columns = {
        'taxid': 'proposed_name',  # Rename 'taxid' to 'proposed_name'
        'Species': 'name_type'  # Rename 'Species' to 'name_type'
    }

    output_df = filtered_df[list(selected_columns.keys())].copy()
    output_df.rename(columns=selected_columns, inplace=True)
    
#convert 'proposed_name' to integer to remove decimals and handle NaN
    output_df['proposed_name'] = pd.to_numeric(output_df['proposed_name'], errors='coerce').astype('Int64')
    
#add new columns 'host', 'project_id', and 'description'
    output_df['host'] = ''  # Empty column - not needed
    output_df['project_id'] = 'BGE'  # Populate 'project_id' with 'BGE' string
    output_df['description'] = ''  # Will be populated with GBIF ID
   
    output_df = output_df[['proposed_name', 'name_type', 'host', 'project_id', 'description']]
    
#save filtered DataFrame to temp TSV file
    temp_tsv = 'temp_taxonomy_request.tsv'
    output_df.to_csv(temp_tsv, sep='\t', index=False)
    
#resolve names using GBIF and update the 'description' column
    resolve_names_and_update_file(temp_tsv, output_tsv)

    os.remove(temp_tsv)
    print(f"Species without species-level taxids saved to {output_tsv}")




def resolve_names_and_update_file(input_filename, output_filename):
    input_df = pd.read_csv(input_filename, sep='\t')

#ensure the description column is treated as string type
    input_df['description'] = input_df['description'].astype(str)

#check if the required column exists
    if 'name_type' not in input_df.columns:
        print("Error: The input file must contain a 'name_type' column.")
        sys.exit(1)

    results = []

#iterate over each row in the DataFrame
    for index, row in input_df.iterrows():
        name_info = {'name': row['name_type']}

        try:
#perform taxonomic name resolution using species.name_backbone
            result = species.name_backbone(**name_info)
            result['index'] = index  #keep track of the original index
#append to results list
            results.append(result)
        except Exception as e:
#handle any exceptions and append error message to results
            print(f"Error resolving name: {name_info}. Error: {e}")
            results.append({"Error": str(e), **name_info, "index": index})

    result_df = pd.DataFrame(results)

#filter results based on GBIF - consistent = ID confidence > 95% ,status = ACCEPTED, and class == Insecta, otherwise = inconsistent. 
    consistent_df = result_df[(result_df['confidence'] > 95) & 
                              (result_df['status'] == 'ACCEPTED') & 
                              (result_df['class'] == 'Insecta') &
                              (result_df['matchType'] == 'EXACT')]
    
    inconsistent_df = result_df[(result_df['confidence'] <= 95) | 
                                (result_df['status'] != 'ACCEPTED') | 
                                (result_df['class'] != 'Insecta') |
                              (result_df['matchType'] != 'EXACT')]


#update the 'description' column in the input DataFrame
    for index, row in consistent_df.iterrows():
        # Ensure the 'description' column does not contain 'nan' strings
        current_description = input_df.at[row['index'], 'description']
        if pd.isna(current_description) or current_description.lower() == 'nan':
            current_description = ''
        else:
            current_description = str(current_description)
        
#append speciesKey to description column
        species_key = int(row['speciesKey'])  # Ensure speciesKey is an integer
        input_df.at[row['index'], 'description'] = f"{current_description} {species_key}".strip()

#write updated df to the output TSV 
    input_df.to_csv(output_filename, sep='\t', index=False, float_format='%d')
    print(f"Updated file written to {output_filename}")

#write inconsistent GBIF rows based on filtering criteria to TSV 
    inconsistent_filename = "gbif_inconsistent.tsv"
    inconsistent_df.to_csv(inconsistent_filename, sep='\t', index=False, float_format='%d')
    print(f"Inconsistent rows written to {inconsistent_filename}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python 1_species_wo_taxid_get_gbifID.py path/to/samples2taxid.csv [run#]_taxonomy_request.tsv")
    else:
        tax_request(sys.argv[1], sys.argv[2])
