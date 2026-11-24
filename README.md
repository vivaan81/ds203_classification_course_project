# Classifying Countries by Human Development Index (DS203 Project)

**Group members:**

| Name | Roll number |
|---|---|
| Vivaan Singhania | 25B2136 |
| Shivam Kushwaha | 25B2146 |
| Tanush Chilakwad | 25B2208 |

## What this project does

We try to predict a country's Human Development Index (HDI) category using only economic, infrastructure,
health and geographic indicators. Each row in our dataset is one country in 2023.

The target has three classes, cut from the UNDP HDI score:

| Class | HDI score | Countries |
|---|---|---|
| 0: Low | below 0.550 | 26 |
| 1: Medium/High | 0.550 to 0.799 | 93 |
| 2: Very High | 0.800 and above | 74 |

This three-class grouping was made for this project. It is not an official UNDP classification (UNDP uses four
categories).

The predictors are 9 World Bank indicators (GDP growth, inflation, unemployment, infant mortality, electricity
access, internet use, agriculture share, industry share, trade), the World Bank region, and an engineered
`DominantSector` feature (agriculture, industry or services, whichever has the largest share of GDP). To avoid
target leakage we do not use the HDI score itself, life expectancy, years of schooling or GNI per capita.

## Results in short

| Model | Test accuracy | Test balanced accuracy | Test macro F1 |
|---|---|---|---|
| Majority-class baseline | 0.487 | 0.333 | 0.218 |
| Logistic regression | 0.821 | 0.730 | 0.726 |
| Decision tree | 0.795 | 0.605 | 0.565 |
| **Random forest (final model)** | **0.821** | **0.725** | **0.729** |

- The random forest was chosen because it had the best cross-validation score on the training set
  (macro F1 0.924 ± 0.056). On the test set it is basically tied with logistic regression.
- Infant mortality, internet use, agriculture share and electricity access are the most informative indicators.
  Adding region mainly helps logistic regression, and DominantSector doesn't help.
- Very High countries are classified almost perfectly. Low is the hardest class (the random forest
  finds 2 of the 5 Low test countries). All 7 random forest mistakes are within 0.04 of the 0.550 or 0.800 cut-offs.

The code and outputs are in the two notebooks, and the discussion is in `report/report.pdf`.

## Folder structure

```
.
├── README.md
├── requirements.txt
├── src/
│   └── build_dataset.py        downloads the raw data and builds the dataset CSV
├── data/
│   ├── hdi_dataset_2023.csv    the final dataset (193 countries), with missing values kept
│   ├── DATA_DICTIONARY.md      every column, the sources, and how the data was built
│   └── raw/                    the original downloads (UNDP + World Bank), so the build can be re-run offline
├── notebooks/
│   ├── 01_eda.ipynb            exploratory data analysis
│   └── 02_modeling.ipynb       preprocessing, models, PCA, evaluation and interpretation
├── outputs/
│   ├── figures/                all plots (created by the notebooks)
│   └── tables/                 result tables as CSV (created by the notebooks)
├── report/
│   ├── report.tex              the LaTeX source of our report
│   ├── report.pdf              the compiled report
│   └── figures/                copies of the figures used in the report
└── presentation/
    └── HDI_presentation.pptx   the slides for our video
```

## Setup

You need Python 3.10 or newer (we used 3.10).

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## How to run

**1. Build the dataset (optional).** `data/hdi_dataset_2023.csv` is already included, so you can skip this step.
To rebuild it from the saved raw files:

```bash
python src/build_dataset.py
```

To download everything again from UNDP and the World Bank (needs internet):

```bash
python src/build_dataset.py --refresh
```

Either way, the script prints a summary at the end (number of countries, class counts, missing values, and which
countries were dropped or didn't match).

**2. Run the notebooks, in order.**

```bash
jupyter notebook
```

Open `notebooks/01_eda.ipynb` and run all cells, then do the same for `notebooks/02_modeling.ipynb`. In VS Code you
can also just open the notebooks and select the `.venv` Python as the kernel.

To run both notebooks from the terminal without opening them:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/02_modeling.ipynb
```

The notebooks use relative paths (`../data/...`), so they need to be run from inside the `notebooks/` folder.
Jupyter and VS Code do this automatically. The EDA notebook takes a few seconds and the modeling notebook about a
minute. The notebooks are saved with their outputs, so you can also read them without running anything.

## Data sources

| Source | Used for |
|---|---|
| [UNDP Human Development Report 2025](https://hdr.undp.org/data-center/documentation-and-downloads), composite indices time series | HDI score for 2023 (the target) |
| [World Bank World Development Indicators](https://datatopics.worldbank.org/world-development-indicators/), via the World Bank API | the 9 indicators |
| World Bank country API | region of each country |

The data was downloaded on 22 November 2026. Countries are matched on their ISO3 code, and all 195 UNDP countries
matched a World Bank country. North Korea and Monaco have no 2023 HDI and are dropped, which leaves 193 countries. If an
indicator is missing for 2023, we use the latest value from 2020 to 2022 and record the year used. All the details
are in [data/DATA_DICTIONARY.md](data/DATA_DICTIONARY.md).

## Methods

- **Split:** stratified 60/20/20 train/validation/test split with a fixed seed (42).
- **Preprocessing** (scikit-learn `Pipeline` + `ColumnTransformer`, fitted on training data only):
  - signed-log transform for the 6 skewed features
  - mean or median imputation, optionally with missingness indicators
  - standardization
  - a "Missing" category plus one-hot encoding for the categorical features
- **Models:** majority-class baseline, multinomial logistic regression, decision tree and random forest. Each is
  tuned with 5-fold stratified cross-validation on the training set, using macro F1.
- **Experiments:**
  - median vs mean imputation, with and without missingness indicators
  - models with vs without PCA
  - numerical-only vs categorical-only vs combined features
- **Evaluation:** accuracy, balanced accuracy, macro F1, per-class precision/recall/F1 and confusion matrices on the
  held-out test set, which is used only once at the end.
- **Interpretation:** logistic regression coefficients, random forest permutation importance, the decision tree
  structure, and a look at the misclassified countries.

## Reproducibility

Everything uses a fixed random seed (42). Running the build script and both notebooks gives exactly the same
dataset, splits and results every time.
