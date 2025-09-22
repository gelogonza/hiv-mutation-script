#!/usr/bin/env python3
"""
flatten_hivdb.py

Helper script to convert sierra-local JSON output into a flattened CSV format
for comparison with model predictions.

Usage:
    python src/flatten_hivdb.py input.json output.csv

Output CSV columns:
    - patient_id: Unique identifier for the sequence/patient
    - gene: HIV gene (RT, PR, IN)
    - drug: Drug name
    - hivdb_level: Original HIVdb resistance level (1-5)
    - hivdb_score: HIVdb resistance score
    - website_label: Mapped resistance category (S/I/R)
    - hivdb_version: Version of HIVdb algorithm used
"""

import json
import pandas as pd
import sys
import argparse
from pathlib import Path

# HIVdb resistance level mapping to S/I/R categories
# This matches the Stanford HIVdb website interpretation
HIVDB_LEVEL_MAPPING = {
    1: "S",  # Susceptible
    2: "I",  # Potential Low-Level Resistance (Intermediate)
    3: "I",  # Low-Level Resistance (Intermediate)
    4: "R",  # Intermediate Resistance (Resistant)
    5: "R"   # High-Level Resistance (Resistant)
}

# Alternative mapping configurations
ALTERNATIVE_MAPPINGS = {
    "conservative": {1: "S", 2: "S", 3: "I", 4: "R", 5: "R"},
    "strict": {1: "S", 2: "I", 3: "R", 4: "R", 5: "R"},
    "default": HIVDB_LEVEL_MAPPING
}

# Alternative mapping for score-based thresholds
def score_to_level(score):
    """Convert HIVdb score to resistance level (1-5)"""
    if score <= 9:
        return 1
    elif score <= 14:
        return 2
    elif score <= 29:
        return 3
    elif score <= 59:
        return 4
    else:
        return 5

def flatten_hivdb_json(json_data, mapping=None):
    """
    Extract drug resistance data from sierra-local JSON output.
    
    Args:
        json_data (dict): Parsed JSON from sierra-local
        mapping (dict): HIVdb level to S/I/R mapping (default: HIVDB_LEVEL_MAPPING)
        
    Returns:
        list: List of dictionaries with flattened resistance data
    """
    if mapping is None:
        mapping = HIVDB_LEVEL_MAPPING
        
    flattened_rows = []
    
    # Handle both single sequence and batch processing formats
    sequences = json_data if isinstance(json_data, list) else [json_data]
    
    for seq_idx, sequence in enumerate(sequences):
        # Extract patient/sequence identifier
        patient_id = sequence.get('inputSequence', {}).get('header', f'seq_{seq_idx}')
        if not patient_id or patient_id.startswith('>'):
            patient_id = patient_id.lstrip('>')
        if not patient_id:
            patient_id = f'seq_{seq_idx}'
            
        # Extract HIVdb version
        hivdb_version = sequence.get('algorithmVersion', 'unknown')
        
        # Process drug resistance results by gene
        drug_resistance = sequence.get('drugResistance', [])
        
        for gene_data in drug_resistance:
            gene = gene_data.get('gene', {}).get('name', 'unknown')
            drug_scores = gene_data.get('drugScores', [])
            
            for drug_data in drug_scores:
                drug_name = drug_data.get('drug', {}).get('name', 'unknown')
                hivdb_score = drug_data.get('score', 0)
                hivdb_level = score_to_level(hivdb_score)
                website_label = mapping.get(hivdb_level, 'S')
                
                flattened_rows.append({
                    'patient_id': patient_id,
                    'gene': gene,
                    'drug': drug_name,
                    'hivdb_level': hivdb_level,
                    'hivdb_score': hivdb_score,
                    'website_label': website_label,
                    'hivdb_version': hivdb_version
                })
    
    return flattened_rows

def main():
    parser = argparse.ArgumentParser(
        description='Convert sierra-local JSON to flattened CSV format',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('input_json', help='Path to sierra-local JSON file')
    parser.add_argument('output_csv', help='Path to output CSV file')
    parser.add_argument('--mapping', choices=['default', 'conservative', 'strict'],
                       default='default', help='HIVdb level to S/I/R mapping strategy')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Print verbose output')
    
    args = parser.parse_args()
    
    # Select mapping strategy
    selected_mapping = ALTERNATIVE_MAPPINGS[args.mapping]
    if args.verbose:
        print(f"Using {args.mapping} mapping: {selected_mapping}")
    
    # Validate input file
    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Load JSON data
    try:
        with open(input_path, 'r') as f:
            json_data = json.load(f)
        if args.verbose:
            print(f"Loaded JSON data from {input_path}")
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to read file - {e}", file=sys.stderr)
        sys.exit(1)
    
    # Flatten the data
    try:
        flattened_data = flatten_hivdb_json(json_data, selected_mapping)
        if args.verbose:
            print(f"Extracted {len(flattened_data)} drug resistance entries")
    except Exception as e:
        print(f"Error: Failed to flatten JSON data - {e}", file=sys.stderr)
        sys.exit(1)
    
    if not flattened_data:
        print("Warning: No drug resistance data found in JSON file", file=sys.stderr)
    
    # Create DataFrame and save CSV
    try:
        df = pd.DataFrame(flattened_data)
        
        # Ensure output directory exists
        output_path = Path(args.output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False)
        
        if args.verbose:
            print(f"Saved flattened data to {output_path}")
            print(f"Shape: {df.shape}")
            print("\nFirst few rows:")
            print(df.head())
            print("\nDrug distribution:")
            print(df['drug'].value_counts().head(10))
            print("\nResistance level distribution:")
            print(df['website_label'].value_counts())
        else:
            print(f"Successfully converted {len(flattened_data)} entries to {output_path}")
            
    except Exception as e:
        print(f"Error: Failed to save CSV file - {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
