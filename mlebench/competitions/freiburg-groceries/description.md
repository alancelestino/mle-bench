# Freiburg Groceries Image Classification Benchmark

## Context
You are provided with the Freiburg Groceries dataset, which contains approximately **5,000 color images** across **25 grocery categories**. Each category includes real-world product photos such as cereal boxes, pasta, spices, milk cartons, canned goods, and beverages.  

The images were collected under natural conditions, including cluttered backgrounds, varying lighting, and different packaging or branding, making classification challenging and realistic for retail applications such as **automated shelf recognition**, **self-checkout systems**, and **inventory management**.

The dataset has been split into training and test subsets:
- `train.csv` contains training image IDs, file paths, and ground-truth labels.
- `test.csv` contains only image IDs and file paths (no labels).
- The hidden file `test_golden_answer.csv` contains the true labels for the test set and is used internally for evaluation.

All images are provided in PNG/JPEG format under the `freiburg_groceries/train` and `freiburg_groceries/test` folders, with file paths referenced in the CSVs.


```
freiburg_groceries/
├── train/
│ ├── CEREAL/
│ │ ├── CEREAL0277.jpg
│ │ └── ...
│ ├── PASTA/
│ │ ├── PASTA0169.jpg
│ │ └── ...
│ └── ...
└── test/
│ ├── test_000563.png
│ └── ...
```

---

## Objective
Train a model that predicts the correct grocery product category (one of the 25 classes) for each image in the **test set**.  

The final output must be a CSV file `submission.csv` with exactly two columns:
- `id`: the unique identifier matching the IDs in `test.csv`
- `label`: the predicted grocery product category

---

## Deliverable Format
The output file should look like:

```
id,label
test_000563,CEREAL
test_000564,PASTA
...
```


Class labels must be chosen from the 25 official grocery categories provided in the dataset:

`CEREAL, PASTA, SPICES, MILK, CANNED_FOOD, BEVERAGES, CHOCOLATE, COFFEE, TEA, JAM, HONEY, RICE, FLOUR, SUGAR, OIL, VINEGAR, KETCHUP, MUSTARD, SAUCES, SNACKS, BISCUITS, CHIPS, BREAD, FRUITS, VEGETABLES`

---

## Evaluation  

Submissions will be evaluated by comparing the predicted labels in `submission.csv` against the hidden ground-truth labels stored for `test.csv`, evaluation metric is as follows.  

- **Top-1 Accuracy**: The percentage of test images whose predicted label exactly matches the ground truth.  

  $$
  \text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} \mathbf{1}\{\hat{y}_i = y_i\}
  $$
