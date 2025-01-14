"""
This script processes taxonomic data to create properly formatted TSV files for submission
to the European Nucleotide Archive (ENA) for taxonomy ID creation. It specifically handles
cases where species-level taxonomy IDs are not available and need to be requested from ENA.

Process Overview:
    1. Reads input CSV containing specimen data and matched taxonomic information
    2. Filters data to identify entries requiring new taxonomy IDs (non-species level matches)
    3. Formats data according to ENA's taxonomy request specifications
    4. Validates species names against GBIF using the pygbif library
    5. Performs taxonomic rank validation against GBIF data
    6. Creates output files:
        - A TSV file formatted for ENA taxonomy requests
        - A CSV file containing taxonomic validation failures
        - A TSV file listing GBIF inconsistencies (synonyms, fuzzy matches, etc.)

The script implements a hierarchical fallback system for taxonomic names:
    1. Uses species name if available
    2. Falls back to "Genus sp. {ID}" if only genus is available
    3. Falls back to "Family sp. {ID}" if only family is available
    4. Uses "not collected" as a last resort
"""

import sys
import os
import pandas as pd
from pygbif import species
import logging
from datetime import datetime

def setup_logging(prefix):
    """Set up logging to both file and console"""
    log_filename = f"{prefix}.log"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])
    
    # Create a formatter
    formatter = logging.Formatter('%(message)s')
    
    # Set up file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def format_taxonomic_name(row, logger):
    """
    Format taxonomic name based on available classification levels.
    Falls back from species to genus to family, appending Process ID for novel entries.
    Implements hierarchical fallback logic as specified in requirements.
    
    Args:
        row (pd.Series): DataFrame row containing taxonomic information
        logger (logging.Logger): Logger instance
        
    Returns:
        str: Formatted taxonomic name following the hierarchy:
            1. Species name if available
            2. Genus sp. + Process ID if genus available
            3. Family sp. + Process ID if only family available
            4. 'not collected' as last resort
    """
    species = str(row['species']).strip()
    genus = str(row['genus']).strip()
    family = str(row['family']).strip()
    process_id = str(row['Process ID']).strip()
    
    # Log the values we're working with
    logger.debug(f"Processing: ID={process_id}, species={species}, genus={genus}, family={family}")
    
    # Case 1: Valid species name
    if species.lower() != 'not collected' and species:
        logger.debug(f"Using species name: {species}")
        return species
    
    # Case 2: Fall back to genus level identification
    if genus.lower() != 'not collected' and genus:
        proposed = f"{genus} sp. {process_id}"
        logger.debug(f"Using genus-based name: {proposed}")
        return proposed
    
    # Case 3: Fall back to family level identification
    if family.lower() != 'not collected' and family:
        proposed = f"{family} sp. {process_id}"
        logger.debug(f"Using family-based name: {proposed}")
        return proposed
    
    # Case 4: No valid taxonomic information available
    logger.debug("No valid taxonomic name found, using 'not collected'")
    return 'not collected'

def determine_name_type(name, original_name=''):
    """
    Determine the name type based on the proposed name and original species name.
    Updated to handle new taxonomic name formatting cases.
    
    Args:
        name (str): The proposed name for submission
        original_name (str): The original species name from the data
        
    Returns:
        str: The determined name type:
            - 'novel_species' for sp. entries or when original is 'not collected'
            - 'not_collected' for entries marked as not collected
            - 'published_name' for standard species entries
    """
    name = str(name).strip()
    original_name = str(original_name).strip().lower()
    
    # Case 1: Handle explicit "not collected" entries
    if name.lower() == 'not collected':
        return 'not_collected'
        
    # Case 2: Handle sp. entries (genus or family level identifications)
    if 'sp.' in name:
        return 'novel_species'
        
    # Case 3: Handle cases where original name was not collected but we have a valid name
    if original_name == 'not collected' and name != original_name:
        return 'novel_species'
    
    # Case 4: Default to published name for standard species entries
    name_parts = name.split()
    return 'published_name' if len(name_parts) >= 2 else ''

def tax_request(input_csv, ids_csv, output_prefix):
    """
    Process taxonomy data and create ENA taxonomy request files.
    New: Also handles taxonomic validation failures output
    """
    # Set up logging
    logger = setup_logging(output_prefix)
    
    # Generate output filenames from prefix
    output_tsv = f"{output_prefix}_taxonomy_request.tsv"
    
    # Read both CSV files
    df = pd.read_csv(input_csv)
    ids_df = pd.read_csv(ids_csv)
    
    logger.info("\nDebugging Info:")
    logger.info("Process IDs in metadata file: %s", sorted(df['Process ID'].unique())[:5])
    logger.info("Process IDs in samples file: %s", sorted(ids_df['ID'].unique()))
    
    # Print available columns for debugging
    logger.info("\nColumns in metadata file: %s", df.columns.tolist())
    logger.info("Initial rows in metadata file: %d", len(df))
    
    # Find the ID column in the second CSV
    id_column = None
    possible_id_columns = ['ID', 'Process ID', 'process_id', 'ProcessID', 'PROCESS_ID']
    for col in possible_id_columns:
        if col in ids_df.columns:
            id_column = col
            break
    
    if id_column is None:
        logger.error("Error: No valid ID column found in the second CSV")
        sys.exit(1)
    
    # Clean and standardise Process IDs
    filter_ids = set(ids_df[id_column].astype(str).str.strip())
    df['Process ID'] = df['Process ID'].astype(str).str.strip()
    
    logger.info("\nNumber of unique IDs in filter file: %d", len(filter_ids))
    logger.info("Example IDs from filter file: %s", list(filter_ids)[:5])
    
    # Filter the main dataframe
    mask = df['Process ID'].isin(filter_ids)
    df = df[mask].copy()
    
    logger.info("Number of matching rows found: %d", len(df))
    if len(df) == 0:
        logger.error("Error: No matching Process IDs found between the files")
        sys.exit(1)
        
    unmapped_ids = [id for id in filter_ids if id not in df['Process ID'].values]
    if unmapped_ids:
        logger.warning("\nWarning: %d IDs from samples file not found in metadata:", len(unmapped_ids))
        logger.warning("%s %s", unmapped_ids[:5], "..." if len(unmapped_ids) > 5 else "")
    
    # Check for duplicates
    if df['Process ID'].duplicated().any():
        logger.warning("Warning: Found duplicate Process IDs in metadata after filtering:")
        logger.warning(df['Process ID'][df['Process ID'].duplicated()].value_counts())
        df = df.drop_duplicates(subset=['Process ID'])
    
    logger.info("Rows after ID filtering: %d", len(df))
    
    if df.empty:
        logger.error("Error: No matching Process IDs found between the two files")
        sys.exit(1)

    # Filter rows where 'matched_rank' == 'species'
    species_df = df[df['matched_rank'].str.lower() == 'species']
    logger.info("Number of species-level matches: %d", len(species_df))
    
    # Filter rows where 'matched_rank' != 'species'
    filtered_df = df[df['matched_rank'].str.lower() != 'species']
    logger.info("Number of non-species-level matches: %d", len(filtered_df))
    
    # Find the species column
    species_col = None
    possible_species_cols = ['Species', 'species', 'scientific_name', 'Scientific_Name', 'scientific name']
    for col in possible_species_cols:
        if col in filtered_df.columns:
            species_col = col
            break
    
    if species_col is None:
        logger.error("\nError: Could not find species column. Available columns are: %s", filtered_df.columns.tolist())
        sys.exit(1)
    
    logger.info("\nUsing '%s' as species column", species_col)
    
    # Create proposed names using the taxonomic hierarchy
    logger.info("Creating proposed names...")
    filtered_df['proposed_name'] = filtered_df.apply(lambda row: format_taxonomic_name(row, logger), axis=1)
    logger.info("Sample of proposed names: %s", filtered_df['proposed_name'].head())
    
    # Select and prepare output DataFrame with all necessary columns
    output_df = filtered_df[['proposed_name', 'Process ID', species_col]].copy()
    output_df.rename(columns={'Process ID': 'process_id'}, inplace=True)
    
    # Add name_type column using updated logic and original species name
    output_df['name_type'] = output_df.apply(
        lambda row: determine_name_type(row['proposed_name'], row[species_col]), 
        axis=1
    )
    
    # Log some samples to verify
    logger.info("\nSample of processed entries:")
    for _, row in output_df.head().iterrows():
        logger.info(f"Process ID: {row['process_id']}")
        logger.info(f"Proposed name: {row['proposed_name']}")
        logger.info(f"Name type: {row['name_type']}\n")
    
    # Add new columns
    output_df['host'] = ''
    output_df['project_id'] = 'BGE'
    output_df['description'] = ''
   
    # Keep process_id in the DataFrame for logging but don't include in final output
    output_df_with_process = output_df.copy()
    output_df = output_df[['proposed_name', 'name_type', 'host', 'project_id', 'description']]
    
    temp_tsv = 'temp_taxonomy_request.tsv'
    output_df.to_csv(temp_tsv, sep='\t', index=False)
    
    # Pass the original DataFrame for taxonomic validation
    resolve_names_and_update_file(temp_tsv, output_tsv, input_csv, output_prefix, logger, 
                                output_df_with_process['process_id'], df)

    os.remove(temp_tsv)
    logger.info("Species without species-level taxids saved to %s", output_tsv)

def resolve_names_and_update_file(input_filename, output_filename, input_csv, output_prefix, logger, process_ids, original_df):
    """
    Resolve names using GBIF and update the taxonomy request file with descriptions.
    """
    # Read and validate input DataFrame
    input_df = pd.read_csv(input_filename, sep='\t')
    input_df['description'] = input_df['description'].astype(str)

    if 'name_type' not in input_df.columns:
        logger.error("Error: The input file must contain a 'name_type' column.")
        sys.exit(1)

    # Initialise DataFrame for taxonomic validation failures
    tax_validation_fails = []

    # Log initial DataFrame info
    logger.info("\nInput DataFrame Info:")
    logger.info("Number of rows: %d", len(input_df))
    logger.info("Index range: %s to %s", input_df.index.min(), input_df.index.max())
    logger.info("Columns: %s", input_df.columns.tolist())

    results = []

    logger.info("\nProcessing species names through GBIF:")
    for index, row in input_df.iterrows():
        name = row['proposed_name']
        name_type = row['name_type']
        current_process_id = process_ids.iloc[index]
        
        # Get original metadata for this Process ID
        original_row = original_df[original_df['Process ID'] == current_process_id].iloc[0]
        
        # Log current processing details
        logger.info("\n----------------------------------------")
        logger.info("Processing row %d:", index)
        logger.info("Current DataFrame index: %d", index)
        logger.info("Process ID: %s", current_process_id)
        logger.info("Name: %s", name)
        logger.info("Name type: %s", name_type)
        
        # Handle 'not collected' entries
        if name_type == 'not_collected':
            logger.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Entry is 'not collected' - skipping GBIF lookup")
            not_collected_result = {
                'index': int(index),
                'process_id': current_process_id,
                'confidence': 100,
                'status': 'NOT_COLLECTED',
                'class': 'NA',
                'matchType': 'NONE',
                'proposed_name': name
            }
            logger.info("Not collected result created with index: %s", not_collected_result['index'])
            results.append(not_collected_result)
            continue

        try:
            # Determine if we need to do a genus-level search
            if 'sp.' in name:
                # Extract genus name for genus-level search
                genus = name.split('sp.')[0].strip()
                name_info = {
                    'name': genus,
                    'rank': 'GENUS'
                }
                logger.info("Performing genus-level GBIF search: %s", name_info)
            else:
                name_info = {'name': name}
                logger.info("Performing standard GBIF search: %s", name_info)
            
            result = species.name_backbone(**name_info)
            
            # Log GBIF result details
            logger.info("GBIF result received:")
            logger.info("Scientific name: %s", result.get('scientificName', 'No scientific name'))
            logger.info("Status: %s", result.get('status', 'Unknown'))
            logger.info("Confidence: %s", result.get('confidence', 'Unknown'))
            
            # Check taxonomic ranks
            gbif_order = result.get('order')
            gbif_class = result.get('class')
            original_order = original_row['order']
            original_class = original_row['class']
            
            logger.info("Taxonomic comparison:")
            logger.info(f"Order - Original: {original_order}, GBIF: {gbif_order}")
            logger.info(f"Class - Original: {original_class}, GBIF: {gbif_class}")
            
            # Validate taxonomic ranks
            tax_valid = False
            failure_reason = None
            
            if gbif_order is None or gbif_class is None:
                failure_reason = "Missing taxonomic ranks in GBIF data"
                logger.info(f"Taxonomic validation failed: {failure_reason}")
            elif original_order == gbif_order:
                tax_valid = True
                logger.info("Order match found")
            elif original_class == gbif_class:
                tax_valid = True
                logger.info("Class match found")
            else:
                failure_reason = "No match at order or class level"
                logger.info(f"Taxonomic validation failed: {failure_reason}")
            
            if not tax_valid:
                # Add to validation failures
                fail_record = {
                    'Process_ID': current_process_id,
                    'phylum': original_row['phylum'],
                    'class': original_row['class'],
                    'order': original_row['order'],
                    'family': original_row['family'],
                    'genus': original_row['genus'],
                    'species': original_row['species'],
                    'taxid': original_row['taxid'],
                    'matched_rank': original_row['matched_rank'],
                    'GBIF_class': gbif_class,
                    'GBIF_order': gbif_order,
                    'failure_reason': failure_reason
                }
                tax_validation_fails.append(fail_record)
                continue
            
            result['index'] = int(index)
            result['process_id'] = current_process_id
            result['proposed_name'] = name
            logger.info("Added index to result: %s", result['index'])
            results.append(result)
            
        except Exception as e:
            logger.error("Error resolving name: %s. Error: %s", name_info, e)
            error_result = {
                "Error": str(e),
                **name_info,
                "index": int(index),
                "process_id": current_process_id,
                "proposed_name": name
            }
            logger.info("Error result created with index: %s", error_result['index'])
            results.append(error_result)

    if not results:
        logger.warning("\nWarning: No valid results from GBIF name resolution")
        return

    # Create DataFrame from results and validate
    result_df = pd.DataFrame(results)
    logger.info("\nGBIF Results DataFrame Info:")
    logger.info("Columns: %s", result_df.columns.tolist())
    logger.info("Number of results: %d", len(result_df))

    # Add missing columns if needed
    required_cols = ['confidence', 'status', 'matchType']
    for col in required_cols:
        if col not in result_df.columns:
            result_df[col] = None
            logger.info("Added missing column: %s", col)

    # Debug each condition for species-level matches
#    species_conditions = {
#        'valid_binomial': (result_df['proposed_name'].str.split().str.len() >= 2) & 
#                         (~result_df['proposed_name'].str.contains('sp.', case=False, na=False)),
#        'confidence_ok': result_df['confidence'].fillna(0) > 95,
#        'status_accepted': result_df['status'].fillna('').str.strip() == 'ACCEPTED',
#        'match_exact': result_df['matchType'].fillna('').str.strip() == 'EXACT'
#    }
    species_conditions = {
        'valid_binomial': result_df.apply(lambda x: 
                                        len(x['proposed_name'].split()) >= 2 and 
                                        'sp.' not in x['proposed_name'].lower(), 
                                        axis=1),
        'confidence_ok': result_df['confidence'].fillna(0) > 95,
        'status_accepted': result_df['status'].fillna('').str.strip() == 'ACCEPTED',
        'match_exact': result_df['matchType'].fillna('').str.strip() == 'EXACT'
    }

    # Add debug logging for each part of valid_binomial
    two_words = result_df['proposed_name'].str.split().str.len() >= 2
    no_sp = ~result_df['proposed_name'].str.contains('sp.', case=False, na=False)
    logger.info(f"\nDebugging valid_binomial components:")
    logger.info(f"two_words condition: {two_words}")
    logger.info(f"no_sp condition: {no_sp}")

    # Log conditions for specific samples
    debug_samples = ['BSNHM012-24', 'BSNHM017-24', 'BSNHM039-24', 'BSNHM065-24']
    logger.info("\nApplied GBIF filter conditions:")
    for pid in debug_samples:
        sample_rows = result_df[result_df['process_id'] == pid]
        if not sample_rows.empty:
            idx = sample_rows.index[0]
            logger.info(f"\nDebug conditions for {pid}:")
            logger.info(f"Proposed name: {result_df.loc[idx, 'proposed_name']}")
            logger.info(f"Status: {result_df.loc[idx, 'status']}")
            logger.info(f"Confidence: {result_df.loc[idx, 'confidence']}")
            logger.info(f"Match type: {result_df.loc[idx, 'matchType']}")
            for cond_name, condition in species_conditions.items():
                logger.info(f"{cond_name}: {condition.iloc[idx]}")
            logger.info(f"All conditions met: {all(cond.iloc[idx] for cond in species_conditions.values())}")

    # Create mask using the conditions
    mask = (
        # Case 1: Not collected entries
        ((result_df['status'] == 'NOT_COLLECTED') & (result_df['matchType'] == 'NONE')) |
        
        # Case 2: Species-level matches
        (species_conditions['valid_binomial'] &
         species_conditions['confidence_ok'] &
         species_conditions['status_accepted'] &
         species_conditions['match_exact']) |
        
        # Case 3: Genus-level matches
        ((result_df['proposed_name'].str.contains('sp.', na=False)) &
         (result_df['status'].fillna('').str.strip() == 'ACCEPTED') &
         (result_df['rank'].fillna('').str.strip() == 'GENUS') &
         (result_df['confidence'].fillna(0) > 90))
    )
    
    consistent_df = result_df[mask]
    inconsistent_df = result_df[~mask]

    # Log filtering results
    logger.info("\nGBIF Results Summary:")
    logger.info("Total valid results: %d", len(result_df))
    logger.info("Consistent matches: %d", len(consistent_df))
    logger.info("Inconsistent matches: %d", len(inconsistent_df))

    # Write taxonomic validation failures to file
    if tax_validation_fails:
        tax_fails_df = pd.DataFrame(tax_validation_fails)
        tax_fails_filename = f"{output_prefix}_tax_validation_fails.csv"
        tax_fails_df.to_csv(tax_fails_filename, index=False)
        logger.info(f"\nWrote {len(tax_validation_fails)} taxonomic validation failures to {tax_fails_filename}")

    # Log inconsistent matches
    if len(inconsistent_df) > 0:
        logger.info("\nInconsistent matches details:")
        for _, row in inconsistent_df.iterrows():
            process_id = row.get('process_id', 'Unknown')
            logger.info(f"\nInconsistent match for {process_id}:")
            logger.info(f"Scientific name: {row.get('scientificName', 'Unknown')}")
            logger.info(f"Status: {row.get('status', 'Unknown')}")
            logger.info(f"Confidence: {row.get('confidence', 'Unknown')}")
            logger.info(f"Match Type: {row.get('matchType', 'Unknown')}")
            if process_id in debug_samples:
                logger.info("Debug conditions:")
                for cond_name, condition in species_conditions.items():
                    logger.info(f"{cond_name}: {condition.iloc[row.name]}")

    # Update descriptions for consistent matches
    logger.info("\nUpdating descriptions for consistent matches:")
    for _, row in consistent_df.iterrows():
        row_index = row.get('index')
        
        logger.info("\nProcessing consistent match:")
        logger.info("Row index: %s (type: %s)", row_index, type(row_index))
        logger.info("Process ID: %s", row.get('process_id'))
        
        # Skip if index is invalid
        if pd.isna(row_index):
            logger.warning("NaN index found - skipping description update")
            continue
        
        # Convert index to integer and validate
        try:
            row_index = int(row_index)
        except (ValueError, TypeError):
            logger.warning("Could not convert index to integer - skipping description update")
            continue
            
        if row_index not in input_df.index:
            logger.warning("Index %s not found in input DataFrame - skipping", row_index)
            continue
            
        # Skip 'not collected' entries
        if row.get('status') == 'NOT_COLLECTED':
            logger.info("Skipping description update for 'not collected' entry")
            continue

        # Update description
        try:
            current_description = input_df.at[row_index, 'description']
            if pd.isna(current_description) or current_description.lower() == 'nan':
                current_description = ''
            
            # For genus-level matches
            if 'sp.' in str(row.get('proposed_name', '')) and 'genusKey' in row and not pd.isna(row['genusKey']):
                try:
                    genus_key = int(row['genusKey'])
                    input_df.at[row_index, 'description'] = f"{current_description} https://www.gbif.org/species/{genus_key}".strip()
                    logger.info("Updated description for index %d with genus key %d", row_index, genus_key)
                except (ValueError, TypeError) as e:
                    logger.warning("Warning: Could not process genusKey for index %d: %s", row_index, e)
            
            # For species-level matches (both accepted and synonym)
            elif 'usageKey' in row and not pd.isna(row['usageKey']):
                try:
                    key = int(row['usageKey'])
                    input_df.at[row_index, 'description'] = f"{current_description} https://www.gbif.org/species/{key}".strip()
                    logger.info("Updated description for index %d with key %d", row_index, key)
                except (ValueError, TypeError) as e:
                    logger.warning("Warning: Could not process key for index %d: %s", row_index, e)

        except KeyError as e:
            logger.warning(f"Could not access index {row_index} in input DataFrame: {e}")

    # Write output files
    logger.info("\nWriting %d rows to output file", len(input_df))
    input_df.to_csv(output_filename, sep='\t', index=False, float_format='%d')
    logger.info("Updated file written to %s", output_filename)

    inconsistent_filename = f"{output_prefix}_gbif_inconsistent.tsv"
    logger.info("\nWriting %d inconsistent matches to separate file", len(inconsistent_df))
    inconsistent_df.to_csv(inconsistent_filename, sep='\t', index=False, float_format='%d')
    logger.info("Inconsistent rows written to %s", inconsistent_filename)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py path/to/sample_metadata.csv path/to/samples.csv prefix")
    else:
        tax_request(sys.argv[1], sys.argv[2], sys.argv[3])
