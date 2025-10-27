# Waste Classification Benchmark

## Context
You are provided with the Waste Classification dataset, which contains approximately **25,000 images** of household waste, divided into two main categories: **organic** and **recyclable**. Of these, around **2,500 images** belong to the test set, while the remaining images are used for training.

This dataset reflects a realistic business application in **waste management and recycling automation**, where the goal is to automatically classify waste to support sorting, sustainability, and efficient disposal. Images were collected under varied conditions, including differences in background, lighting, and object orientation, making the classification task more challenging than simple benchmarks.

The dataset has been split into training and test subsets:
- `train.csv` contains training image IDs, file paths, and ground-truth labels.  
- `test.csv` contains only image IDs and file paths (no labels).  

All images are provided in JPG format under the `waste_classification/train` and `waste_classification/test` folders, with file paths referenced in the CSVs.

```
waste_classification/
├── train.csv
├── test.csv
├── train/
│ ├── organic/
│ │ ├── O_99.jpg
│ │ └── ...
│ ├── recyclable/
│ │ ├── R_91.jpg
│ │ └── ...
└── test/
│ ├── test_002282.jpg
│ ├── test_002283.jpg
└── ...
```


---

## Objective
Train a model that predicts the correct waste category (**organic** or **recyclable**) for each image in the **test set**.  

The final output must be a CSV file `submission.csv` with exactly two columns:

- `id`: the unique identifier matching the IDs in `test.csv`  
- `label`: the predicted waste category  

---

## Deliverable Format
The output file should look like:

```
id,label
test_000001,organic
test_002503,recyclable
...
```


Class labels must be chosen from the following set:  
`organic, recyclable`

---

## Evaluation
Submissions will be evaluated by comparing the predicted labels in `submission.csv` against the hidden ground-truth labels stored for `test.csv`.  

- **Accuracy**  
  Since this is a binary classification task (organic vs. recyclable), the primary evaluation metric is overall classification accuracy:  

  $$
  \text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} \mathbf{1}(\hat{y}_i = y_i)
  $$  