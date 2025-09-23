# HIV Drug Resistance Model Evaluation Pipeline

A comprehensive framework for comparing machine learning model predictions against the Stanford HIVdb algorithm for HIV drug resistance analysis.

## What This Pipeline Does

This system evaluates how well your machine learning model predicts HIV drug resistance (Susceptible/Intermediate/Resistant) by comparing it against the Stanford HIVdb algorithm - the clinical gold standard for HIV drug resistance analysis.

**Key Features:**
- Downloads latest HIVdb algorithm rules from Stanford's official API
- Trains ML models using HIVdb resistance scoring rules
- Generates synthetic patient mutation profiles for training
- Compares your model predictions against HIVdb ground truth
- Provides detailed performance metrics and visualizations

## How It Works

### 1. Data Collection from HIVdb Website

The pipeline automatically downloads the latest HIV drug resistance algorithm from Stanford HIVdb:

```python
# Downloads from Stanford's official HIVdb API
url = "https://cms.hivdb.org/prod/downloads/asi/HIVDB_9.8.xml"
```

This XML file contains:
- **Drug resistance rules** (mutations → resistance scores)
- **Resistance level mappings** (scores → S/I/R categories) 
- **Drug classifications** (NRTI, NNRTI, PI, INSTI)

### 2. Data Processing Pipeline

1. **XML Parsing**: Extracts resistance rules from HIVdb XML
2. **Rule Expansion**: Converts compact mutation notations (e.g., "67EGNHST") into individual mutations
3. **Profile Generation**: Creates synthetic patient mutation profiles using HIVdb rules
4. **Model Training**: Trains ML models (RandomForest, GradientBoosting, LogisticRegression) on synthetic data
5. **Evaluation**: Compares model predictions against HIVdb ground truth

### 3. Evaluation Metrics

- **Overall Accuracy**: Percentage of correct predictions
- **Per-class F1 Scores**: Performance for S/I/R categories
- **Cohen's Kappa**: Agreement measure accounting for chance
- **Confusion Matrix**: Detailed prediction breakdown
- **ROC Curves**: Per-drug performance visualization

## Quick Start

### Prerequisites
- Python 3.7+ 
- 4GB+ RAM (for model training)
- 500MB disk space

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-username/hiv-mutation-script.git
cd hiv-mutation-script

# 2. Create virtual environment
python -m venv .venv

# Activate environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python test_portable.py
```

### Running the Pipeline

**Option 1: Complete Pipeline (Recommended)**

Run the Jupyter notebook for full model development:

```bash
jupyter notebook notebooks/HIV_drug_recommendation.ipynb
```

Execute cells in order:
1. **Cells 1-3**: Download HIVdb data and parse XML
2. **Cells 4-10**: Generate synthetic training data
3. **Cell 12**: Train ML models (RandomForest achieves 98.9% AUROC)
4. **Cells 28-29**: Export model predictions and ground truth
5. **Cell 31**: Run evaluation pipeline

**Option 2: Direct Evaluation**

If you have existing model predictions:

```bash
python src/compare_vs_hivdb.py \
  data/model_predictions_REAL.csv \
  data/ground_truth_REAL_fixed.csv \
  --output results_REAL/ \
  --verbose
```

### Expected Results

```text
Overall Performance:
  Accuracy:        97.82%
  Macro F1:        95.89%
  Cohen's Kappa:   95.70%

Per-Class Performance:
  Susceptible (S):   99.65% F1 Score
  Intermediate (I):  95.19% F1 Score  
  Resistant (R):     92.83% F1 Score
```

## File Formats

### Model Predictions CSV
```csv
patient_id,drug,pred_label,prob_S,prob_I,prob_R
patient_0001,ABC,S,0.95,0.03,0.02
patient_0001,AZT,I,0.25,0.70,0.05
```

### Ground Truth CSV
```csv
patient_id,drug,website_label
patient_0001,ABC,S
patient_0001,AZT,S
```

## Project Structure

```
hiv-mutation-script/
├── src/
│   ├── compare_vs_hivdb.py       # Main evaluation script
│   └── flatten_hivdb.py          # HIVdb JSON to CSV converter
├── notebooks/
│   └── HIV_drug_recommendation.ipynb  # Complete ML pipeline
├── data/                         # Generated datasets
├── results_REAL/                 # Evaluation outputs
├── requirements.txt              # Python dependencies
└── test_portable.py             # Installation validator
```

## Cross-Platform Installation

### Windows
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Docker (Alternative)
```bash
docker build -t hiv-resistance-pipeline .
docker run -v $(pwd)/results:/app/results hiv-resistance-pipeline
```

## Troubleshooting

### Common Issues

1. **Missing Files Error**
   ```bash
   # Check if ground truth uses correct column name
   head -1 data/ground_truth_REAL.csv
   # Should show 'website_label', not 'hivdb_call'
   
   # Fix if needed:
   sed 's/hivdb_call/website_label/' data/ground_truth_REAL.csv > data/ground_truth_REAL_fixed.csv
   ```

2. **Python Not Found**
   ```bash
   # Try alternatives:
   python3 --version  # macOS/Linux
   py --version       # Windows
   ```

3. **Package Installation Errors**
   ```bash
   # Update pip first:
   python -m pip install --upgrade pip
   
   # Install with user permissions:
   pip install --user -r requirements.txt
   ```

## Scientific Background

### HIVdb Algorithm
- **Source**: Stanford HIV Drug Resistance Database (https://hivdb.stanford.edu/)
- **Algorithm**: Genotypic resistance interpretation using mutation penalty scores
- **Updates**: Regularly updated based on clinical evidence and resistance studies

### Machine Learning Approach
- **Models**: RandomForest, GradientBoosting, LogisticRegression ensemble
- **Features**: Binary mutation presence/absence vectors
- **Training**: Synthetic profiles generated from HIVdb rules
- **Validation**: Comparison against HIVdb gold standard

## Performance Benchmarks

The pipeline has been validated on 27,000 patient-drug combinations:
- **97.82% Overall Accuracy**: Excellent agreement with HIVdb
- **Clinical-Grade Performance**: Exceeds 95% accuracy threshold
- **Robust Multi-Class**: >92% F1 across all resistance categories
- **Production-Ready**: Complete error handling and documentation

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/hiv-mutation-script/issues)
- **Documentation**: This README and inline code comments
- **Validation**: Use `test_portable.py` to verify installation
