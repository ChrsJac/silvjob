from __future__ import annotations

import re
from dataclasses import dataclass


TOPIC_PATTERNS: dict[str, str] = {
    "silviculture": r"\bsilvicultur(?:e|al)\b",
    "quantitative silviculture": r"\bquantitative silviculture\b",
    "forest biometrics": r"\bforest biometric(?:s)?\b|\bbiometrician\b",
    "mensuration": r"\bmensuration\b",
    "growth and yield": r"\bgrowth\s*(?:and|&)\s*yield\b|\bgrowth/yield\b",
    "forest modeling": r"\bforest model(?:ing|er)?\b|\bmodeling forest\b",
    "forest ecology": r"\bforest ecology\b|\bforest ecolog(?:y|ical)\b",
    "forest health": r"\bforest health\b",
    "forest management": r"\bforest management\b",
    "forest resources": r"\bforest resource(?:s)?\b",
    "forest operations": r"\bforest operations\b",
    "forestry": r"\bforestr(?:y|ies)\b",
    "tree breeding": r"\btree breeding\b|\bforest genetics\b|\bgenomics\b",
    "extension forestry": r"\bextension\b.{0,40}\bforestr(?:y|ies)\b|\bforestr(?:y|ies)\b.{0,40}\bextension\b",
    "agroforestry": r"\bagroforestr(?:y|ies)\b",
    "urban forestry": r"\burban forestr(?:y|ies)\b|\burban forest\b",
}

ROLE_PATTERNS: dict[str, str] = {
    "assistant professor": r"\bassistant professor\b",
    "associate professor": r"\bassociate professor\b",
    "professor": r"\bprofessor\b",
    "faculty": r"\bfaculty\b",
    "open-rank": r"\bopen[- ]rank\b",
    "postdoc": r"\bpost\s*-?doctoral?\b|\bpostdoc\b|\bpostdoctoral scholar\b|\bpostdoctoral fellow\b",
    "research scientist": r"\bresearch scientist\b|\bresearch faculty\b|\bscientist\b|\bresearch fellow\b",
    "research associate": r"\bresearch associate\b|\bresearch scholar\b",
    "extension specialist": r"\bextension specialist\b|\bextension professor\b|\bextension forester\b",
    "lecturer/instructor": r"\blecturer\b|\binstructor\b",
    "director": r"\bdirector\b",
}

DOCTORATE_HINT_PATTERNS: dict[str, str] = {
    "doctorate": r"\bdoctorate\b|\bph\.?d\.?\b|\bdoctoral\b",
    "preferred doctorate": r"\bdoctorate preferred\b|\bph\.?d\.? preferred\b",
}

EXCLUDE_PATTERNS: dict[str, str] = {
    # NOTE: these patterns are intentionally checked against the *title* only in classify_job,
    # not the full description — faculty descriptions routinely mention supervising students,
    # interns, and technicians, which must not disqualify those postings.
    "student": r"\bgraduate opportunity\b|\bgraduate opportunities\b|\bundergraduate\b|\bstudent\b",
    "assistantship": r"\bassistantship\b|\bgraduate assistant\b|\bgraduate research assistant\b|\bgra\b",
    "intern": r"\bintern\b|\binternship\b",
    "technician": r"\btechnician\b|\bfield assistant\b|\bcrew member\b",
    "hourly temporary": r"\bhourly\b|\btemporary\b|\bseasonal\b|\bpart-time\b|\bpart time\b",
}


@dataclass(slots=True)
class FilterResult:
    keep: bool
    matched_terms: list[str]
    matched_roles: list[str]
    matched_doctorate_hints: list[str]
    matched_exclusions: list[str]


def classify_job(title: str, description: str = "", education_required: str = "") -> FilterResult:
    full_text = " ".join([title, description, education_required]).lower()
    title_lower = title.lower()

    matched_terms = [name for name, pattern in TOPIC_PATTERNS.items() if re.search(pattern, full_text)]
    matched_roles = [name for name, pattern in ROLE_PATTERNS.items() if re.search(pattern, full_text)]
    matched_doctorate_hints = [name for name, pattern in DOCTORATE_HINT_PATTERNS.items() if re.search(pattern, full_text)]
    # Apply exclusions to the title only: legitimate faculty/research job descriptions routinely
    # mention graduate students, interns, and technicians they will supervise, which should not
    # disqualify the posting.
    matched_exclusions = [name for name, pattern in EXCLUDE_PATTERNS.items() if re.search(pattern, title_lower)]

    keep = bool(matched_terms) and bool(matched_roles) and not matched_exclusions
    return FilterResult(
        keep=keep,
        matched_terms=matched_terms,
        matched_roles=matched_roles,
        matched_doctorate_hints=matched_doctorate_hints,
        matched_exclusions=matched_exclusions,
    )


def infer_job_type(title: str, description: str = "") -> str:
    text = f"{title} {description}".lower()
    if re.search(ROLE_PATTERNS["postdoc"], text):
        return "Postdoc"
    if re.search(ROLE_PATTERNS["extension specialist"], text):
        return "Extension"
    if re.search(ROLE_PATTERNS["research scientist"], text) or re.search(ROLE_PATTERNS["research associate"], text):
        return "Research"
    if re.search(ROLE_PATTERNS["director"], text):
        return "Director"
    if re.search(ROLE_PATTERNS["faculty"], text) or re.search(ROLE_PATTERNS["open-rank"], text):
        return "Faculty/Academic"
    return "Faculty/Academic"
