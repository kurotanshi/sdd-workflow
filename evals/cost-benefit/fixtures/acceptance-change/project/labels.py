def clean_labels(labels: list[str]) -> list[str]:
    return [label.strip() for label in labels if label.strip()]
