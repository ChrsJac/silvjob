from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Engine = Literal["tamu_job_board", "warnell_board", "generic_board"]


@dataclass(frozen=True)
class SourceConfig:
    name: str
    engine: Engine
    url: str
    organization: str
    notes: str = ""
    enabled: bool = True


SOURCES: list[SourceConfig] = [
    SourceConfig(
        name="Texas A&M Natural Resources Job Board",
        engine="tamu_job_board",
        url="https://jobs.rwfm.tamu.edu/search/?PageNum=1&PageSize=10",
        organization="Texas A&M Natural Resources Job Board",
        notes="Public board with published date, salary, education, and full description on public pages."
    ),
    SourceConfig(
        name="UGA Warnell Jobs",
        engine="warnell_board",
        url="https://warnell.uga.edu/jobs",
        organization="Warnell School of Forestry and Natural Resources",
        notes="Strong forestry-specific external board, but not doctorate-only. Filtering is applied after scrape."
    ),
    SourceConfig(
        name="UGA Jobs",
        engine="generic_board",
        url="https://www.ugajobsearch.com/postings/search?page=1&sort=226+desc&utf8=%E2%9C%93",
        organization="University of Georgia",
        notes="Useful for direct forestry faculty searches."
    ),
    SourceConfig(
        name="HigherEdJobs Ecology and Forestry",
        engine="generic_board",
        url="https://www.higheredjobs.com/faculty/search.cfm?JobCat=54",
        organization="HigherEdJobs",
        notes="Broad academic board; useful for faculty roles."
    ),
    SourceConfig(
        name="AcademicJobsOnline",
        engine="generic_board",
        url="https://academicjobsonline.org/ajo/All",
        organization="AcademicJobsOnline",
        notes="Useful mostly for postdocs and some faculty lines."
    ),
    SourceConfig(
        name="Academic Keys Forestry",
        engine="generic_board",
        url="https://sciences-m.academickeys.com/browse_by_field/Environmental_Sciences/Ecology/Forestry",
        organization="Academic Keys",
        notes="Academic aggregator with forestry/ecology pages."
    ),
    SourceConfig(
        name="Chronicle Ecology and Forestry",
        engine="generic_board",
        url="https://jobs.chronicle.com/jobs/environmental-science-ecology-and-forestry/",
        organization="Chronicle of Higher Education",
        notes="Broad academic board; useful for faculty and some extension lines."
    ),
    SourceConfig(
        name="Ecophys Jobs Postdoc",
        engine="generic_board",
        url="https://ecophys-jobs.org/postdoc.html",
        organization="Ecophys Jobs",
        notes="Useful niche source for forest ecophysiology and related postdocs."
    ),
    SourceConfig(
        name="SAF Career Center Faculty",
        engine="generic_board",
        url="https://careercenter.eforester.org/jobs/function/Faculty/",
        organization="Society of American Foresters",
        notes="Direct forestry board; availability can vary."
    ),
]
