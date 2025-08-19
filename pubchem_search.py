# --- START OF FILE pubchem_search.py (Translated and Commented) ---

import pubchempy as pcp
import pandas as pd

def main():
    # 1. Search by compound name
    compound_name = 'Aspirin'
    compounds = pcp.get_compounds(compound_name, 'name')
    if compounds:
        # If results are found, take the first one from the list
        compound = compounds[0]
        print(f"First search result for '{compound_name}':")
        print(f"CID: {compound.cid}")
        print(f"IUPAC Name: {compound.iupac_name}")
        print(f"Molecular Formula: {compound.molecular_formula}")
        print(f"Molecular Weight: {compound.molecular_weight}")
        print(f"Canonical SMILES: {compound.canonical_smiles}")
        print(f"Synonyms: {compound.synonyms}")
    else:
        print(f"No compound found with the name '{compound_name}'.")

    # ---
    # 2. Search by SMILES
    smiles = 'CC(=O)OC1=CC=CC=C1C(=O)O'  # SMILES for Aspirin
    compounds_by_smiles = pcp.get_compounds(smiles, 'smiles')
    if compounds_by_smiles:
        compound = compounds_by_smiles[0]
        print(f"\nFirst result for SMILES search '{smiles}':")
        print(f"CID: {compound.cid}")
        print(f"IUPAC Name: {compound.iupac_name}")
        print(f"Molecular Formula: {compound.molecular_formula}")
        print(f"Molecular Weight: {compound.molecular_weight}")
        print(f"Canonical SMILES: {compound.canonical_smiles}")
        print(f"Synonyms: {compound.synonyms}")
    else:
        print(f"No compound matching the SMILES '{smiles}' was found.")

    # ---
    # 3. Get 2D and 3D coordinates
    # NOTE: The original code here is incorrect, it does not fetch coordinates.
    if compounds:
        compound = compounds[0]
        # This only retrieves the SMILES again, not the coordinates.
        compound_info = compound.to_dict(properties=['canonical_smiles'])
        print(f"\nGetting information (example):")
        print(compound_info)
    else:
        print("Cannot get information because the compound was not found.")
        
    # ---
    # 4. Calculate fingerprints and descriptors
    # NOTE: Like step 3, this code does not calculate what it claims.
    if compounds:
        compound = compounds[0]
        # This also just gets the SMILES.
        fingerprint_example = compound.to_dict(properties=['canonical_smiles'])
        print(f"\nExample of fetching a property (SMILES):")
        print(fingerprint_example)
    else:
        print("Cannot get descriptors because the compound was not found.")

    # ---
    # 5. Use pandas to build a properties table
    if compounds:
        compound = compounds[0]
        # A dictionary is created with the data
        data = {
            'Property': ['CID', 'IUPAC Name', 'Molecular Formula', 'Molecular Weight', 'SMILES', 'Synonyms'],
            'Value': [compound.cid, compound.iupac_name, compound.molecular_formula,
                      compound.molecular_weight, compound.canonical_smiles,
                      ', '.join(compound.synonyms)] # Joins the list of synonyms into a single string
        }
        # The dictionary is converted into a pandas DataFrame to be displayed as a table
        df = pd.DataFrame(data)
        print(f"\nProperties table for '{compound_name}':")
        print(df)
    else:
        print("Cannot create properties table because the compound was not found.")

# Standard Python entry point: if this script is executed, call the main() function
if __name__ == '__main__':
    main()