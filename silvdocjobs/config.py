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
        notes="Broad academic board; useful for faculty roles in ecology and forestry."
    ),
    SourceConfig(
        name="HigherEdJobs Natural Resources",
        engine="generic_board",
        url="https://www.higheredjobs.com/faculty/search.cfm?JobCat=154",
        organization="HigherEdJobs",
        notes="Natural resources and conservation faculty positions on HigherEdJobs."
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
        notes="Direct forestry board from the Society of American Foresters."
    ),
    SourceConfig(
        name="ESA Career Center",
        engine="generic_board",
        url="https://careers.esa.org/jobs/",
        organization="Ecological Society of America",
        notes="Academic and research positions in ecology, including forestry-related roles."
    ),
    SourceConfig(
        name="IUFRO Job Advertisements",
        engine="generic_board",
        url="https://www.iufro.org/science/other-activities/job-advertisements/",
        organization="IUFRO",
        notes="International forestry research jobs from the International Union of Forest Research Organizations."
    ),
    SourceConfig(
        name="Society for Conservation Biology Jobs",
        engine="generic_board",
        url="https://conbio.org/professional-development/job-board/",
        organization="Society for Conservation Biology",
        notes="Conservation biology faculty, postdoc, and research positions, including forest conservation."
    ),
    SourceConfig(
        name="USDA Forest Service Research Jobs",
        engine="generic_board",
        url="https://research.fs.usda.gov/jobs",
        organization="USDA Forest Service",
        notes="Research scientist and postdoc positions at USDA Forest Service research stations."
    ),
    SourceConfig(
        name="Yale School of the Environment Jobs",
        engine="generic_board",
        url="https://environment.yale.edu/about/jobs",
        organization="Yale School of the Environment",
        notes="Faculty and research positions at a top forestry and environmental school."
    ),
    SourceConfig(
        name="Oregon State College of Forestry Employment",
        engine="generic_board",
        url="https://forestry.oregonstate.edu/about/employment-opportunities",
        organization="Oregon State University College of Forestry",
        notes="Employment opportunities at one of the nation's top forestry programs."
    ),
    SourceConfig(
        name="Nature Careers Ecology and Forestry",
        engine="generic_board",
        url="https://www.nature.com/naturecareers/job-search/results/?discipline%5B%5D=ecology&term=forestry+silviculture",
        organization="Nature Careers",
        notes="International academic positions in ecology and forestry from Nature Careers."
    ),
]
