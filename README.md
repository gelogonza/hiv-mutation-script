# HIV Drug Resistance Model Evaluation Pipeline

A comprehensive evaluation framework for comparing machine learning model predictions against HIVdb reference calls for HIV drug resistance analysis.

## Directory Structure

```text
hiv-mutation-script/
├── README.md                           # This file
├── src/                               # Python scripts
│   ├── compare_vs_hivdb.py           # Main evaluation script
│   └── flatten_hivdb.py              # HIVdb JSON to CSV converter
├── notebooks/                        # Jupyter notebooks
│   └── HIV_drug_recommendation.ipynb # ML model development
├── data/                             # Model predictions and datasets
├── hivdb/                            # HIVdb reference data
└── results/                          # Evaluation outputs (auto-created)
```

## Installation

### Dependencies

Install the required Python packages:

```bash
# Option 1: Install from requirements.txt
pip install -r requirements.txt

# Option 2: Install manually
pip install pandas scikit-learn numpy
```

### sierra-local Setup

To generate HIVdb reference calls, you'll need sierra-local (Stanford HIVdb's local resistance analysis tool):

1. **Download sierra-local:**

   ```bash
   # Download the latest release from GitHub
   wget https://github.com/hivdb/sierra-local/releases/latest/download/sierra-local-linux.zip
   unzip sierra-local-linux.zip
   ```

2. **Make it executable:**

   ```bash
   chmod +x sierra-local
   ```

3. **Test installation:**

   ```bash
   ./sierra-local --help
   ```

## Usage Workflow

### Step 1: Generate HIVdb Reference Calls

Run sierra-local on your HIV sequences to get HIVdb reference calls:

```bash
# Example: Process FASTA sequences
./sierra-local fasta your_sequences.fasta > hivdb/hivdb_output.json

# Or process individual sequences
echo ">seq1\nATGCCCATCCTCAAGTTCGGTGGTAGG..." | ./sierra-local stdin > hivdb/hivdb_output.json
```

### Step 2: Flatten HIVdb JSON Output

Convert the sierra-local JSON output to a standardized CSV format:

```bash
python src/flatten_hivdb.py hivdb/hivdb_output.json data/hivdb_calls.csv --verbose
```

**Options:**

- `--mapping {default,conservative,strict}`: HIVdb level to S/I/R mapping strategy
  - `default`: Levels 1→S, 2-3→I, 4-5→R
  - `conservative`: Levels 1-2→S, 3→I, 4-5→R
  - `strict`: Level 1→S, 2→I, 3-5→R
- `--verbose`: Print detailed processing information

**Output CSV schema:**

```csv
patient_id,gene,drug,hivdb_level,hivdb_score,website_label,hivdb_version
seq1,RT,3TC,1,0,S,9.5
seq1,RT,AZT,3,15,I,9.5
seq2,PR,ATV/r,5,85,R,9.5
```

### Step 3: Export Model Predictions

Generate predictions from your machine learning model and save to CSV format. Your model predictions CSV should follow this schema:

**Required columns:**

```csv
patient_id,drug,pred_label
seq1,3TC,S
seq1,AZT,I
seq2,ATV/r,R
```

**Optional columns for enhanced metrics:**

```csv
patient_id,drug,pred_label,prob_S,prob_I,prob_R,model_version
seq1,3TC,S,0.95,0.03,0.02,RandomForest_v1.0
seq1,AZT,I,0.25,0.70,0.05,RandomForest_v1.0
seq2,ATV/r,R,0.10,0.15,0.75,RandomForest_v1.0
```

**Example code to export from your model:**

```python
import pandas as pd

# Assume you have predictions and patient/drug info
predictions_data = {
    'patient_id': patient_ids,
    'drug': drug_names, 
    'pred_label': predicted_labels,
    'prob_S': probabilities[:, 0],  # Optional
    'prob_I': probabilities[:, 1],  # Optional
    'prob_R': probabilities[:, 2],  # Optional
    'model_version': 'YourModel_v1.0'  # Optional
}

pred_df = pd.DataFrame(predictions_data)
pred_df.to_csv('data/model_predictions.csv', index=False)
```

### Step 4: Run Model Evaluation

Compare your model predictions against HIVdb reference calls:

```bash
# Using CSV inputs
python src/compare_vs_hivdb.py data/model_predictions.csv data/hivdb_calls.csv --output results/

# Using JSON input (will be flattened automatically)
python src/compare_vs_hivdb.py data/model_predictions.csv hivdb/hivdb_output.json --output results/
```

**Options:**

- `--output results/`: Output directory for results files
- `--mapping {default,conservative,strict}`: HIVdb resistance level mapping
- `--verbose`: Print detailed evaluation information

## Output Files

The evaluation script generates several output files in the specified directory:

### 1. `merged_eval_rows.csv`

Complete dataset with predictions and ground truth merged:

```csv
patient_id,drug,pred_label,prob_S,prob_I,prob_R,model_version,gene,hivdb_level,hivdb_score,website_label,hivdb_version
seq1,3TC,S,0.95,0.03,0.02,RandomForest_v1.0,RT,1,0,S,9.5
```

### 2. `confusion_matrix_SIR.csv`

Confusion matrix in CSV format:

```csv
,Pred_S,Pred_I,Pred_R
True_S,850,45,12
True_I,67,234,89
True_R,23,78,456
```

### 3. `classification_report.json`

Detailed per-class metrics:

```json
{
  "S": {"precision": 0.92, "recall": 0.89, "f1-score": 0.91},
  "I": {"precision": 0.78, "recall": 0.82, "f1-score": 0.80},
  "R": {"precision": 0.88, "recall": 0.91, "f1-score": 0.89},
  "accuracy": 0.87,
  "macro avg": {"precision": 0.86, "recall": 0.87, "f1-score": 0.87}
}
```

### 4. `summary.json`

Overall performance summary:

```json
{
  "accuracy": 0.8732,
  "macro_f1": 0.8689,
  "micro_f1": 0.8732,
  "weighted_f1": 0.8745,
  "cohen_kappa": 0.7834,
  "f1_susceptible": 0.9067,
  "f1_intermediate": 0.8012,
  "f1_resistant": 0.8987,
  "top_2_accuracy": 0.9456
}
```

## Key Metrics Explained

- **Accuracy**: Overall proportion of correct predictions
- **Macro F1**: Unweighted average of per-class F1 scores
- **Weighted F1**: Sample-weighted average of per-class F1 scores  
- **Cohen's Kappa**: Agreement between predictions and ground truth, accounting for chance
- **Top-2 Accuracy**: Proportion where true label is in top 2 predicted probabilities
- **Per-class F1**: F1 score for each resistance category (S/I/R)

## HIVdb Resistance Level Mappings

The pipeline supports three mapping strategies for converting HIVdb's 5-level system to S/I/R:

| HIVdb Level | Description | Default | Conservative | Strict |
|------------|-------------|---------|--------------|--------|
| 1 | Susceptible | S | S | S |
| 2 | Potential Low-Level | I | S | I |
| 3 | Low-Level | I | I | R |
| 4 | Intermediate | R | R | R |
| 5 | High-Level | R | R | R |

Choose the mapping that best aligns with your clinical interpretation needs.

## Example Complete Workflow

```bash
# 1. Generate HIVdb reference calls
./sierra-local fasta sequences.fasta > hivdb/raw_output.json

# 2. Flatten to CSV
python src/flatten_hivdb.py hivdb/raw_output.json data/hivdb_calls.csv --verbose

# 3. Export model predictions (in your Python code)
# ... generate predictions and save to data/model_predictions.csv

# 4. Run evaluation
python src/compare_vs_hivdb.py data/model_predictions.csv data/hivdb_calls.csv --output results/ --verbose

# 5. Review results
cat results/summary.json
```

## Troubleshooting

**Common Issues:**

1. **Missing patient_id + drug combinations**: Ensure both datasets use identical patient IDs and drug names
2. **Invalid resistance labels**: Check that all labels are 'S', 'I', or 'R'
3. **Sierra-local errors**: Verify sequence format and sierra-local installation
4. **Memory issues**: For large datasets, process sequences in batches

**Getting Help:**

- Check file formats match the expected schemas
- Use `--verbose` flag for detailed processing information
- Verify patient_id and drug name consistency between files

## License

This evaluation pipeline is designed for research and educational purposes. Please ensure compliance with HIVdb usage terms when using sierra-local.
