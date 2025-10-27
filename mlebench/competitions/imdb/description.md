**IMDB TEXT CLASSIFICATION:**

**Context:**

The data for this task consists of movie reviews from the Large Movie Review Dataset (IMDb), specifically restructured for a binary sentiment classification challenge.

The core dataset contains movie reviews along with their associated binary sentiment labels (positive or negative). For this task, the data has been reorganized into a standard training and testing split.

The **training set** contains examples with known sentiment labels.  
The **test set** contains examples for which you need to predict the sentiment label. The true labels exist but are hidden for the purpose of this evaluation.  
The test set contains 5,000 text files.

File and Folder Structure

`imdb/`  
├── `train/`  
│ ├── `pos/`  
│ │ ├── `101.txt`  
│ │ └── `...`  
│ ├── `neg/`  
│ │ ├── `103.txt`  
│ │ └── `...`  
│   
└── `test/`  
│ │ ├── `104.txt`  
│ │ └── ...  
└── `imdb.vocab`

---

**Objective:**

Your task is to build a model using the provided training data (train/pos, train/neg).  
The final output must be a CSV file:

`submission.csv` with exactly two columns:

- `id`: the unique identifier matching the IDs in `testset`  
- `label`: the predicted binary sentiment label.

**Deliverable Format:**  
You must submit a single CSV file named submission.csv.

The output file should look like:

`id,label`  
`1000_4.txt,1`  
`1001_3txt,0`  
`...`

O for the negative class  
1 fro the positive class

##  Evaluation

Submissions will be evaluated by comparing the predicted labels in `submission.csv` against the hidden ground-truth labels. The primary metric used for ranking will be Accuracy.  
Accuracy measures the proportion of reviews for which the predicted sentiment label (0 or 1\) matches the true sentiment label.  
**Formula:** (Number of Correct Predictions) / (Total Number of Predictions)  
Accuracy is the most common and straightforward choice for this type of balanced binary classification task.

