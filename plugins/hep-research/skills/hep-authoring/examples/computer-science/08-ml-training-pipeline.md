# CS 8: ML training pipeline

**Request:** "Draw the ML pipeline from raw data to deployment, with tuning."
**Type:** pipeline with training and inference paths separated; leakage-safe.

```mermaid
flowchart LR
    RAW[(Raw data)] --> PRE[Cleaning and preprocessing]
    PRE --> SPL{Train / val / test split}
    SPL --> TR[(Train set)]
    SPL --> VA[(Validation set)]
    SPL --> TE[(Test set)]
    TR --> FIT["Fit preprocessing + features<br/>(train only)"]
    FIT --> TRN[Model training]
    TRN --> HP[Hyperparameter tuning]
    VA --> HP
    HP --> TRN
    TRN --> FIN[Selected model]
    TE --> EV[Final evaluation]
    FIN --> EV
    EV --> DEP[Deployment]
    subgraph INF["Inference path"]
        REQ([New data]) --> FT2[Same fitted preprocessing] --> SERVE[Deployed model] --> PRED([Predictions])
    end
    DEP -.-> SERVE
```
**Checks:** the split happens before fitting any data-dependent preprocessing; the test set is used once, after selection; validation feeds tuning only; inference reuses the *fitted* preprocessing.
**Caption:** Machine-learning pipeline. Data are split before any statistics are estimated; preprocessing and features are fitted on the training set only, hyperparameters are tuned on the validation set, and the selected model is evaluated once on the held-out test set before deployment. The inference path (bottom) applies the same fitted preprocessing to new data.
