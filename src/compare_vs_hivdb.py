#!/usr/bin/env python3
"""
compare_vs_hivdb.py

Comprehensive evaluation script to compare machine learning model predictions
against HIVdb reference calls.

Usage:
    python src/compare_vs_hivdb.py model_predictions.csv hivdb_calls.csv --output results/
    python src/compare_vs_hivdb.py model_predictions.csv hivdb_data.json --output results/

Input formats:
    Model predictions CSV: patient_id, drug, pred_label, [prob_S, prob_I, prob_R], [model_version]
    HIVdb calls CSV: patient_id, drug, website_label, [hivdb_level, hivdb_score, gene, hivdb_version]
    HIVdb JSON: Raw sierra-local JSON output (will be flattened automatically)

Output files:
    - merged_eval_rows.csv: Merged predictions and ground truth
    - confusion_matrix_SIR.csv: Confusion matrix in CSV format
    - classification_report.json: Detailed per-class metrics
    - summary.json: Overall performance summary
"""

import pandas as pd
import numpy as np
import json
import argparse
import sys
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, f1_score, cohen_kappa_score,
    confusion_matrix, classification_report, top_k_accuracy_score
)

# Configurable HIVdb resistance level mapping to S/I/R categories
# This matches the Stanford HIVdb website interpretation
HIVDB_LEVEL_MAPPING = {
    1: "S",  # Susceptible
    2: "I",  # Potential Low-Level Resistance (Intermediate)  
    3: "I",  # Low-Level Resistance (Intermediate)
    4: "R",  # Intermediate Resistance (Resistant)
    5: "R"   # High-Level Resistance (Resistant)
}

# Alternative mapping configurations (can be modified as needed)
ALTERNATIVE_MAPPINGS = {
    "conservative": {1: "S", 2: "S", 3: "I", 4: "R", 5: "R"},
    "strict": {1: "S", 2: "I", 3: "R", 4: "R", 5: "R"},
    "default": HIVDB_LEVEL_MAPPING
}

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
        pd.DataFrame: DataFrame with flattened resistance data
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
    
    return pd.DataFrame(flattened_rows)

def load_and_validate_predictions(pred_path):
    """Load and validate model predictions CSV"""
    try:
        df = pd.read_csv(pred_path)
        required_cols = ['patient_id', 'drug', 'pred_label']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Validate prediction labels
        valid_labels = {'S', 'I', 'R'}
        invalid_labels = set(df['pred_label'].unique()) - valid_labels
        if invalid_labels:
            raise ValueError(f"Invalid prediction labels found: {invalid_labels}")
        
        print(f"✓ Loaded {len(df)} model predictions")
        return df
        
    except Exception as e:
        print(f"✗ Error loading predictions: {e}", file=sys.stderr)
        sys.exit(1)

def load_and_validate_hivdb(hivdb_path, mapping=None):
    """Load and validate HIVdb calls from CSV or JSON file"""
    if mapping is None:
        mapping = HIVDB_LEVEL_MAPPING
        
    hivdb_file = Path(hivdb_path)
    
    try:
        # Determine file type and load accordingly
        if hivdb_file.suffix.lower() == '.json':
            # Load JSON and flatten it
            with open(hivdb_path, 'r') as f:
                json_data = json.load(f)
            df = flatten_hivdb_json(json_data, mapping)
            print(f"✓ Loaded and flattened {len(df)} HIVdb calls from JSON")
            
        elif hivdb_file.suffix.lower() == '.csv':
            # Load CSV directly
            df = pd.read_csv(hivdb_path)
            required_cols = ['patient_id', 'drug', 'website_label']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # If hivdb_level is present but website_label is missing, map it
            if 'hivdb_level' in df.columns and df['website_label'].isna().any():
                df['website_label'] = df['hivdb_level'].map(mapping)
                
            print(f"✓ Loaded {len(df)} HIVdb calls from CSV")
            
        else:
            raise ValueError(f"Unsupported file format: {hivdb_file.suffix}. Use .csv or .json")
        
        # Validate HIVdb labels
        valid_labels = {'S', 'I', 'R'}
        invalid_labels = set(df['website_label'].unique()) - valid_labels
        if invalid_labels:
            raise ValueError(f"Invalid HIVdb labels found: {invalid_labels}")
        
        return df
        
    except Exception as e:
        print(f"✗ Error loading HIVdb calls: {e}", file=sys.stderr)
        sys.exit(1)

def merge_datasets(pred_df, hivdb_df):
    """Merge predictions with HIVdb ground truth"""
    # Merge on patient_id + drug
    merged = pd.merge(
        pred_df, 
        hivdb_df.add_suffix('_hivdb'),
        left_on=['patient_id', 'drug'],
        right_on=['patient_id_hivdb', 'drug_hivdb'],
        how='inner'
    )
    
    if len(merged) == 0:
        print("✗ Error: No matching patient_id + drug combinations found", file=sys.stderr)
        sys.exit(1)
    
    # Clean up duplicate columns
    merged = merged.drop(columns=['patient_id_hivdb', 'drug_hivdb'])
    merged = merged.rename(columns={'website_label_hivdb': 'hivdb_label'})
    
    print(f"✓ Successfully merged {len(merged)} evaluation pairs")
    print(f"  - {len(pred_df)} model predictions")
    print(f"  - {len(hivdb_df)} HIVdb calls") 
    print(f"  - {len(merged)} matched pairs")
    
    return merged

def compute_metrics(merged_df, has_probabilities=False):
    """Compute comprehensive evaluation metrics"""
    y_true = merged_df['hivdb_label']
    y_pred = merged_df['pred_label']
    
    # Basic metrics
    accuracy = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average='macro')
    micro_f1 = f1_score(y_true, y_pred, average='micro')
    weighted_f1 = f1_score(y_true, y_pred, average='weighted')
    kappa = cohen_kappa_score(y_true, y_pred)
    
    # Per-class F1 scores
    per_class_f1 = f1_score(y_true, y_pred, average=None, labels=['S', 'I', 'R'])
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=['S', 'I', 'R'])
    
    # Classification report
    class_report = classification_report(y_true, y_pred, labels=['S', 'I', 'R'], output_dict=True)
    
    # Top-k accuracy (if probabilities available)
    top_k_metrics = {}
    if has_probabilities:
        prob_cols = ['prob_S', 'prob_I', 'prob_R']
        if all(col in merged_df.columns for col in prob_cols):
            y_proba = merged_df[prob_cols].values
            label_map = {'S': 0, 'I': 1, 'R': 2}
            y_true_numeric = [label_map[label] for label in y_true]
            
            top_k_metrics['top_2_accuracy'] = top_k_accuracy_score(y_true_numeric, y_proba, k=2)
    
    metrics = {
        'accuracy': accuracy,
        'macro_f1': macro_f1,
        'micro_f1': micro_f1,
        'weighted_f1': weighted_f1,
        'cohen_kappa': kappa,
        'f1_susceptible': per_class_f1[0],
        'f1_intermediate': per_class_f1[1], 
        'f1_resistant': per_class_f1[2],
        'confusion_matrix': cm.tolist(),
        'classification_report': class_report,
        **top_k_metrics
    }
    
    return metrics

def print_summary(metrics, merged_df):
    """Print evaluation summary to stdout"""
    print("\n" + "="*60)
    print("HIV DRUG RESISTANCE MODEL EVALUATION SUMMARY")
    print("="*60)
    
    print(f"Dataset Size: {len(merged_df)} predictions")
    print(f"Unique Patients: {merged_df['patient_id'].nunique()}")
    print(f"Unique Drugs: {merged_df['drug'].nunique()}")
    
    print(f"\nOverall Performance:")
    print(f"  Accuracy:        {metrics['accuracy']:.4f}")
    print(f"  Macro F1:        {metrics['macro_f1']:.4f}")
    print(f"  Weighted F1:     {metrics['weighted_f1']:.4f}")
    print(f"  Cohen's Kappa:   {metrics['cohen_kappa']:.4f}")
    
    if 'top_2_accuracy' in metrics:
        print(f"  Top-2 Accuracy:  {metrics['top_2_accuracy']:.4f}")
    
    print(f"\nPer-Class F1 Scores:")
    print(f"  Susceptible (S): {metrics['f1_susceptible']:.4f}")
    print(f"  Intermediate(I): {metrics['f1_intermediate']:.4f}")
    print(f"  Resistant (R):   {metrics['f1_resistant']:.4f}")
    
    # Print confusion matrix
    cm = np.array(metrics['confusion_matrix'])
    print(f"\nConfusion Matrix:")
    print("         Pred:  S    I    R")
    labels = ['S', 'I', 'R']
    for i, true_label in enumerate(labels):
        print(f"True {true_label}:      {cm[i, 0]:4d} {cm[i, 1]:4d} {cm[i, 2]:4d}")
    
    # Distribution analysis
    print(f"\nLabel Distribution:")
    hivdb_dist = merged_df['hivdb_label'].value_counts().sort_index()
    pred_dist = merged_df['pred_label'].value_counts().sort_index()
    
    for label in ['S', 'I', 'R']:
        hivdb_count = hivdb_dist.get(label, 0)
        pred_count = pred_dist.get(label, 0)
        print(f"  {label}: HIVdb={hivdb_count:4d}, Model={pred_count:4d}")

def save_outputs(merged_df, metrics, output_dir):
    """Save all output files"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save merged evaluation data
    merged_path = output_path / 'merged_eval_rows.csv'
    merged_df.to_csv(merged_path, index=False)
    print(f"✓ Saved merged evaluation data: {merged_path}")
    
    # Save confusion matrix
    cm_df = pd.DataFrame(
        metrics['confusion_matrix'],
        index=['True_S', 'True_I', 'True_R'],
        columns=['Pred_S', 'Pred_I', 'Pred_R']
    )
    cm_path = output_path / 'confusion_matrix_SIR.csv'
    cm_df.to_csv(cm_path)
    print(f"✓ Saved confusion matrix: {cm_path}")
    
    # Save classification report
    report_path = output_path / 'classification_report.json'
    with open(report_path, 'w') as f:
        json.dump(metrics['classification_report'], f, indent=2)
    print(f"✓ Saved classification report: {report_path}")
    
    # Save summary metrics
    summary_metrics = {k: v for k, v in metrics.items() 
                      if k not in ['confusion_matrix', 'classification_report']}
    summary_path = output_path / 'summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary_metrics, f, indent=2)
    print(f"✓ Saved summary metrics: {summary_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Compare ML model predictions against HIVdb reference',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('model_predictions', help='CSV file with model predictions')
    parser.add_argument('hivdb_calls', help='CSV or JSON file with HIVdb calls')
    parser.add_argument('--output', '-o', default='results/', 
                       help='Output directory for results')
    parser.add_argument('--mapping', choices=['default', 'conservative', 'strict'],
                       default='default', help='HIVdb level to S/I/R mapping strategy')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print detailed output')
    
    args = parser.parse_args()
    
    # Select mapping strategy
    selected_mapping = ALTERNATIVE_MAPPINGS[args.mapping]
    if args.verbose:
        print(f"Using {args.mapping} mapping: {selected_mapping}")
    
    # Load datasets
    pred_df = load_and_validate_predictions(args.model_predictions)
    hivdb_df = load_and_validate_hivdb(args.hivdb_calls, selected_mapping)
    
    # Merge datasets
    merged_df = merge_datasets(pred_df, hivdb_df)
    
    # Check for probability columns
    has_probabilities = all(col in pred_df.columns for col in ['prob_S', 'prob_I', 'prob_R'])
    if has_probabilities and args.verbose:
        print("✓ Found probability columns for advanced metrics")
    
    # Compute metrics
    metrics = compute_metrics(merged_df, has_probabilities)
    
    # Print summary
    print_summary(metrics, merged_df)
    
    # Save outputs
    save_outputs(merged_df, metrics, args.output)
    
    print(f"\n✓ Evaluation complete! Results saved to: {args.output}")

if __name__ == '__main__':
    main()
