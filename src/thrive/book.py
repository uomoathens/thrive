from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    author: str
    title: str
    subtitle: str
    publisher: str
    place: str
    year: int
    isbn_hardcover: str
    isbn_ebook: str
    url: str

    @property
    def full_title(self) -> str:
        return f"{self.title}: {self.subtitle}"

    def citation(self) -> str:
        return (
            f"{self.author} ({self.year}). {self.full_title}. "
            f"{self.publisher}, {self.place}. ISBN {self.isbn_hardcover}. {self.url}"
        )


@dataclass(frozen=True)
class Framework:
    acronym: str
    name: str
    chapter: int
    table: str
    phase: str


BOOK = Book(
    author="Sargiotis, D.",
    title="AI for Resilient Cities",
    subtitle="Predicting, Protecting, and Thriving in a Changing Climate",
    publisher="Springer",
    place="Cham",
    year=2027,
    isbn_hardcover="978-3-032-36416-6",
    isbn_ebook="978-3-032-36417-3",
    url="https://link.springer.com/book/9783032364166",
)

PHASES = ("Predicting", "Protecting", "Fairness check", "Thriving")

PHASE_NOTES = {
    "Fairness check": "audit method of Who Gets Help First? (Sargiotis, 2026, doi:10.5281/zenodo.23684889)",
    "Thriving": "new in THRIVE, extends the social-impact feedback layer of EA-CURA (Table 3.5)",
}

FRAMEWORKS = (
    Framework("HEFF-RC", "Hybrid ensemble AI for flood forecasting and risk classification", 1, "1.6", "Predicting"),
    Framework("LSTM-AFFUW", "LSTM-based adaptive flood forecasting in ungauged watersheds", 1, "1.7", "Predicting"),
    Framework("AIF-EWS", "AI-driven flood early warning system", 1, "1.8", "Predicting"),
    Framework("VAE-LVM", "Variational Autoencoder with Latent Vulnerability Mapping", 4, "4.8", "Predicting"),
    Framework("EA-CURA", "Ethical AI-constrained urban resilience architecture", 3, "3.5", "Protecting"),
    Framework("FCFL", "Fairness-constrained federated learning framework", 5, "5.8", "Protecting"),
    Framework("DPFL-EDA", "Differentially private federated learning for ethical disaster AI", 1, "1.5", "Protecting"),
)


def frameworks_for(phase: str) -> tuple[Framework, ...]:
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    return tuple(f for f in FRAMEWORKS if f.phase == phase)
