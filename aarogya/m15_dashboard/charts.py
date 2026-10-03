import matplotlib.pyplot as plt


def plot_age_distribution(df):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(df["age"], bins=10, color="steelblue", edgecolor="white")
    ax.set_title("Patient Age Distibution")
    ax.set_xlabel("Age")
    ax.set_ylabel("Count")
    return fig


def plot_bmi_vs_age(df):
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = df["gender"].map({"Male": "blue", "Female": "pink"})
    ax.scatter(df["age"], df["bmi"], c=colors, alpha=0.6)
    ax.set_title("BMI vs Age")
    ax.set_xlabel("Age")
    ax.set_ylabel("BMI")
    return fig


def plot_city_patient_count(df):
    fig, ax = plt.subplots(figsize=(8, 4))
    city_counts = df["city"].value_counts()
    ax.bar(city_counts.index, city_counts.values, colors="steelblue")
    ax.set_title("Patients per City")
    ax.set_xlabel("City")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45)
    return fig


def plot_dashboard(df):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0][0].hist(df["age"], bins=10, color="steelblue")
    axes[0][0].set_title("Age Distribution")
    axes[0][1].scatter(df["age"], df["bmi"], alpha=0.6, color="green")
    axes[0][1].set_title("BMI vs Age")

    city_counts = df["city"].value_counts()
    axes[1][0].bar(city_counts.index, city_counts.values)
    axes[1][0].set_title("Patients per City")
    plt.setp(axes[1][0].xaxis.get_majorticklabels(), rotation=45)
    axes[1][1].bar(
        ["High BP", "Diabetics"],
        [
            len(df[df["bp_systolic"] > 140]),
            len(df[df["sugar_fasting"] > 126]),
        ],
        color=["red", "orange"],
    )
    axes[1][1].set_title("Risk Factors")

    fig.tight_layout()
    return fig
