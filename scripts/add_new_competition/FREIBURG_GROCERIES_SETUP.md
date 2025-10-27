# Freiburg Groceries Competition - Setup Complete! 🎉

## What Was Created

### Competition Files (in `mlebench/competitions/freiburg-groceries/`)
✅ `config.yaml` - Competition configuration
✅ `description.md` - Competition description for agents
✅ `prepare.py` - Data preparation script (handles local data)
✅ `grade.py` - Grading function using accuracy metric
✅ `classes.py` - List of 25 grocery categories
✅ `leaderboard.csv` - Synthetic leaderboard for medal thresholds
✅ `kernels.txt` - Placeholder for reference kernels

### Helper Scripts
✅ `prepare_local_competition.py` - Script to prepare competitions with local data (bypasses Kaggle download)
✅ `experiments/splits/freiburg-groceries.txt` - Competition split file for running agents

### Prepared Data (in `~/Library/Caches/mle-bench/data/freiburg-groceries/`)
✅ `raw/` - Original data copied from `custom_data/dataset_id_1/`
✅ `prepared/public/` - Data visible to agents (train.csv, test.csv, images, description.md)
✅ `prepared/private/` - Hidden test labels for grading
✅ Checksums generated for data integrity

## Dataset Statistics
- **Training images**: 3,945
- **Test images**: 1,002
- **Classes**: 25 grocery categories
- **Format**: PNG images with CSV metadata

## Testing Results
✅ **Grading Tested**: Sample submission scored 0.02794 (2.8% accuracy)
✅ **Medal Thresholds**:
  - Gold: 96.2%
  - Silver: 93.8%
  - Bronze: 88.8%
  - Median: 86.1%

---

## How to Use

### Test Grading Manually
```bash
# Activate virtual environment
source .venv/bin/activate

# Create a test submission (or use your own)
mlebench grade-sample <path_to_submission.csv> freiburg-groceries
```

### Run AIDE Agent on This Competition

#### 1. Build Docker Images (if not done already)

Build the base environment:
```bash
docker build --platform=linux/amd64 -t mlebench-env -f environment/Dockerfile .
```

Build the AIDE agent:
```bash
export SUBMISSION_DIR=/home/submission
export LOGS_DIR=/home/logs
export CODE_DIR=/home/code
export AGENT_DIR=/home/agent

docker build --platform=linux/amd64 -t aide agents/aide/ \
  --build-arg SUBMISSION_DIR=$SUBMISSION_DIR \
  --build-arg LOGS_DIR=$LOGS_DIR \
  --build-arg CODE_DIR=$CODE_DIR \
  --build-arg AGENT_DIR=$AGENT_DIR
```

#### 2. Set Up API Key

For Claude Sonnet 4.5, set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

#### 3. Configure AIDE for Claude Sonnet 4.5

The AIDE agent config already has configurations for various models. To use Claude Sonnet 3.5 (closest available):
```bash
# Use the existing claude-3-5-sonnet configuration
AGENT_ID="aide/claude-3-5-sonnet"
```

Or add a new configuration in `agents/aide/config.yaml`:
```yaml
aide/claude-sonnet-4.5:
  <<: *defaults
  kwargs:
    <<: *kwargs_common
    agent.code.model: claude-sonnet-4.5  # Use exact model name from Anthropic API
    agent.feedback.model: claude-sonnet-4.5
    agent.steps: *step_count
  env_vars:
    <<: *env_vars
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### 4. Run the Agent

```bash
python run_agent.py \
  --agent-id aide/claude-3-5-sonnet \
  --competition-set experiments/splits/freiburg-groceries.txt \
  --n-workers 1 \
  --n-seeds 1
```

This will:
- Start a Docker container with AIDE
- Give the agent access to the competition data and description
- Run for up to 24 hours (or 500 steps, whichever comes first)
- Save results to `runs/<timestamp>_run-group_aide/freiburg-groceries/`

#### 5. Grade the Results

After the agent finishes:
```bash
# Find your run group directory
RUN_GROUP=$(ls -t runs/ | head -1)

# Generate submission JSONL
python experiments/make_submission.py \
  --metadata runs/$RUN_GROUP/metadata.json \
  --output runs/$RUN_GROUP/submission.jsonl

# Grade the submission
mlebench grade \
  --submission runs/$RUN_GROUP/submission.jsonl \
  --output-dir runs/$RUN_GROUP
```

---

## Competition Details

### What the Agent Sees

The agent has access to:
- `train.csv` - 3,945 training images with labels
- `test.csv` - 1,002 test images without labels  
- `train/` - Training images organized by class folders
- `test/` - Test images (no class organization)
- `description.md` - Full competition description
- `sample_submission.csv` - Example submission format

### What the Agent Must Produce

A file at `/home/submission/submission.csv` with format:
```csv
id,label
test_000001,BEANS
test_000002,PASTA
test_000003,CEREAL
...
```

### Evaluation Metric

**Top-1 Accuracy**: Percentage of correct predictions

$$\text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} \mathbf{1}\{\hat{y}_i = y_i\}$$

### Available Classes

```
BEANS, CAKE, CANDY, CEREAL, CHIPS, CHOCOLATE, COFFEE, CORN, 
FISH, FLOUR, HONEY, JAM, JUICE, MILK, NUTS, OIL, PASTA, RICE, 
SODA, SPICES, SUGAR, TEA, TOMATO_SAUCE, VINEGAR, WATER
```

---

## Quick Commands Reference

```bash
# Activate environment
source .venv/bin/activate

# Test grading
mlebench grade-sample <submission.csv> freiburg-groceries

# Run AIDE agent
python run_agent.py \
  --agent-id aide/claude-3-5-sonnet \
  --competition-set experiments/splits/freiburg-groceries.txt

# Check agent progress (in another terminal)
tail -f runs/<run-group>/freiburg-groceries/logs/*.log

# Grade after completion
python experiments/make_submission.py --metadata runs/<run-group>/metadata.json --output runs/<run-group>/submission.jsonl
mlebench grade --submission runs/<run-group>/submission.jsonl --output-dir runs/<run-group>
```

---

## Troubleshooting

### If you need to re-prepare the data:
```bash
python prepare_local_competition.py -c freiburg-groceries --force
```

### If you want to verify the competition was added:
```bash
python -c "from mlebench.registry import registry; print('freiburg-groceries' in registry.list_competition_ids())"
```

### Check prepared data location:
```bash
ls -lh ~/Library/Caches/mle-bench/data/freiburg-groceries/prepared/public/
```

---

## Notes

- **Time Limit**: Default is 24 hours per run (configurable in `agents/aide/config.yaml`)
- **Step Limit**: Default is 500 steps (configurable)
- **Hardware**: By default runs on CPU. Edit `environment/config/container_configs/default.json` to add GPU support
- **Data Location**: All data is cached in `~/Library/Caches/mle-bench/data/`
- **Custom Prepare Script**: The `prepare_local_competition.py` script can be used for other local competitions too!

---

## What's Next?

1. **Test the grading** with your own submission
2. **Run AIDE** on the competition
3. **Analyze results** in the runs directory
4. **Iterate** - you can run multiple seeds or different agent configurations

Good luck! 🚀

