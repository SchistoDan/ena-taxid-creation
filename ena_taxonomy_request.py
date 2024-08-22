#Reads input csv, filters rows where matched_rank != "species," renames and reorders columns, and outputs to tsv.
#resolve_names_and_update_file function uses pygbif library to grab gbif id's from GBIF, and updates the description column with the GBIF speciesKey.
#Rows with inconsistencies in GBIF ID are saved to a separate gbif_inconsistent.tsv file.
#NEEDS pygbif INSTALLED IN CONDA ENV TO RUN



import sys
import os
import pandas as pd
from pygbif import species  # Ensure pygbif is installed




def tax_request(input_csv, output_tsv, species_output_csv):
    df = pd.read_csv(input_csv)

#Filter rows where 'matched_rank' == 'species' & output species-level rows to specified csv
    species_df = df[df['matched_rank'].str.lower() == 'species']
    species_df.to_csv(species_output_csv, index=False)
    print(f"Species-level rows saved to {species_output_csv}")
    
#Filter rows where 'matched_rank' != 'species'
    filtered_df = df[df['matched_rank'].str.lower() != 'species']
    

#Select necessary columns and rename them ('taxid' to 'proposed_name' & 'Species' to 'name_type')
    selected_columns = {
        'taxid': 'proposed_name', 
        'Species': 'name_type'
    }

    output_df = filtered_df[list(selected_columns.keys())].copy()
    output_df.rename(columns=selected_columns, inplace=True)
    
#Convert 'proposed_name' to integer to remove decimals and handle NaN
    output_df['proposed_name'] = pd.to_numeric(output_df['proposed_name'], errors='coerce').astype('Int64')
    
#Add new columns 'host', 'project_id', and 'description'
    output_df['host'] = ''  #Empty column - not needed
    output_df['project_id'] = 'BGE'  #Populate 'project_id' with 'BGE' string
    output_df['description'] = ''  #Populated with GBIF ID
   
    output_df = output_df[['proposed_name', 'name_type', 'host', 'project_id', 'description']]
    

    temp_tsv = 'temp_taxonomy_request.tsv'
    output_df.to_csv(temp_tsv, sep='\t', index=False)
    
#Resolve names using GBIF and update the 'description' column
    resolve_names_and_update_file(temp_tsv, output_tsv, input_csv)

    os.remove(temp_tsv)
    print(f"Species without species-level taxids saved to {output_tsv}")




def resolve_names_and_update_file(input_filename, output_filename, input_csv):
    input_df = pd.read_csv(input_filename, sep='\t')

    input_df['description'] = input_df['description'].astype(str)

    if 'name_type' not in input_df.columns:
        print("Error: The input file must contain a 'name_type' column.")
        sys.exit(1)

#Load sample2taxid.csv to retrieve 'Process ID' and 'Species'
    sample_df = pd.read_csv(input_csv)

    results = []


#Iterate over each row in df
    for index, row in input_df.iterrows():
        name_info = {'name': row['name_type']}

        try:
#Perform taxonomic name resolution using species.name_backbone
            result = species.name_backbone(**name_info)
            result['index'] = index  
            results.append(result)
        except Exception as e:
            print(f"Error resolving name: {name_info}. Error: {e}")
            results.append({"Error": str(e), **name_info, "index": index})

    result_df = pd.DataFrame(results)


#Filter results based on GBIF criteria
    consistent_df = result_df[(result_df['confidence'] > 95) & 
                              (result_df['status'] == 'ACCEPTED') & 
                              (result_df['class'] == 'Insecta') &
                              (result_df['matchType'] == 'EXACT')]
    
    inconsistent_df = result_df[(result_df['confidence'] <= 95) | 
                                (result_df['status'] != 'ACCEPTED') | 
                                (result_df['class'] != 'Insecta') |
                                (result_df['matchType'] != 'EXACT')]


#Update 'description' column in df
    for index, row in consistent_df.iterrows():
        current_description = input_df.at[row['index'], 'description']
        if pd.isna(current_description) or current_description.lower() == 'nan':
            current_description = ''
        else:
            current_description = str(current_description)
        
#Append speciesKey + link to description column
        species_key = int(row['speciesKey'])  # Ensure speciesKey is an integer
        input_df.at[row['index'], 'description'] = f"{current_description} https://www.gbif.org/species/{species_key}".strip()

#Update 'project_id' by appending the 'Process ID' where name_type matches 'Species' in sample2taxid.csv
    input_df['project_id'] = input_df.apply(lambda x: append_process_id(x, sample_df), axis=1)

#Write updated df to the output tsv 
    input_df.to_csv(output_filename, sep='\t', index=False, float_format='%d')
    print(f"Updated file written to {output_filename}")

#Extract batch number from output filename
    run_number = os.path.basename(output_filename).split('_')[0]

#Write inconsistent GBIF rows based on filtering criteria to TSV with batch number appended
    inconsistent_filename = f"{run_number}_gbif_inconsistent.tsv"
    inconsistent_df.to_csv(inconsistent_filename, sep='\t', index=False, float_format='%d')
    print(f"Inconsistent rows written to {inconsistent_filename}")





def append_process_id(row, sample_df):

#Find the matching row in sample_df where Species matches name_type
    matching_row = sample_df[sample_df['Species'] == row['name_type']]
    
#Get 'Process ID' and append to 'BGE'
    if not matching_row.empty:
        process_id = matching_row.iloc[0]['Process ID']  
        return f"BGE: {process_id}"  
    else:
        return row['project_id']  



if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python 1_species_wo_taxid_get_gbifID.py path/to/samples2taxid.csv taxonomy_request.tsv species_output.csv")
    else:
        tax_request(sys.argv[1], sys.argv[2], sys.argv[3])
