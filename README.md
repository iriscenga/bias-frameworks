# Bias Mitigation Frameworks in Machine Learning Models

This project aims to evaluate the effectiveness of AI Fairness 360 (AIF360) and Fairlearn frameworks in detecting and mitigating bias in machine learning models trained on the COMPAS and Adult Income datasets. The project includes training and assessing Logistic Regression, Random Forest, and LightGBM models for both performance and fairness. Additionally, various bias mitigation techniques, such as reweighing, are applied and evaluated to ensure unbiased predictions.

## Project Description

The main objective of this project is to evaluate the effectiveness of the AIF360 and Fairlearn frameworks in detecting and mitigating bias in machine learning models. We focus on the following aspects:

- **Machine Learning Models:** Train and assess Logistic Regression, Random Forest, and LightGBM models for performance and fairness.

- **Bias Mitigation Techniques:** Apply and evaluate techniques such as reweighing to determine the most effective method for ensuring unbiased predictions.

  
Datasets used in this project:

COMPAS Dataset
Adult Income Dataset


## Supported bias mitigation algorithms

**AIF360**:

1. Preprocessing Techniques:

* Reweighing

2. In-processing Techniques:

* GridSearch with Equalized Odds
  
3. Postprocessing Techniques:

* Calibrated Equalized Odds Postprocessing

  
**Fairlearn**:

1. In-processing Techniques:

* Exponentiated Gradient with Demographic Parity
* GridSearch with Equalized Odds

2. Postprocessing Techniques:

* Equalized Odds Postprocessing

## Supported fairness metrics

**AIF360**:

* Disparate Impact
* Statistical Parity Difference
* Equalized Odds Difference

**Fairlearn**:

* Demographic Parity Ratio
* Demographic Parity Difference
* Equalized Odds Difference

## Supported performance metrics

* Accuracy
* Precision
* Recall
* F1 Score


## Setup


### Install with `pip`

To install the latest stable version of AIF360 from PyPI, run:

```bash
pip install aif360
```

or, for complete functionality, run:

```bash
pip install 'aif360[all]'
```

To install the latest stable version of FairLearn from PyPI, run:

```bash
pip install fairlearn
```


If you'd like to run the notebooks, download the datasets now and place them in
their respective folders.

To download and prepare the datasets, please follow the instructions in the respective folders:

- Compas dataset -> data/compas/README.md

- Adult Income Dataset -> data/adult/README.md

### Prerequisites

In order to run the notebooks, you need to install the following dependencies:

```bash
pip install raiwidgets matplotlib numpy seaborn pandas sklearn lightgbm
```

We used Python **3.10.6** for this project. Please ensure you have this version installed to avoid any compatibility issues.

### Running the Notebooks

The notebooks are intended to be run in Jupyter Notebook. The fairness dashboards, in particular, are designed to work within this environment, allowing for interactive exploration and analysis of fairness metrics and mitigation strategies. While the code works in any environment, using Jupyter Notebook provides an enhanced interactive experience.

If you do not have Jupyter Notebook installed, you can install it using pip:

```bash
pip install jupyter
```

## Contributing

We welcome contributions to this project. Please open an issue or submit a pull request on GitHub.
