from pathlib import Path

import pytest

from jobscanner.config import ListSpec, load_config

ROOT = Path(__file__).parent.parent


def test_repo_config_loads():
    cfg = load_config(ROOT / "config.yaml")
    assert [l.key for l in cfg.lists][:3] == ["eng", "swe", "github"]
    sites = {l.key: l for l in cfg.lists if l.is_site}
    assert "site:nvidia" in sites and sites["site:rtx"].workday.startswith("https://globalhr.wd5")
    assert sites["site:nvidia"].wants("Analog IC Design Intern") and not sites["site:nvidia"].wants("Analog IC Designer")
    assert not sites["site:nvidia"].wants("Internal Network Engineer")
    assert cfg.criteria.skip_phd_only and cfg.criteria.graduation == (2028, 5)
    assert "Texas Instruments" in cfg.criteria.priority_companies and "NXP Semiconductors" in cfg.criteria.priority_companies
    assert cfg.lists[2].repo == "SimplifyJobs/Summer2027-Internships"
    assert cfg.criteria.min_hourly_pay == 28
    assert cfg.criteria.locations[0] == "CT" and {"Boston", "TX", "WY", "DC"} <= set(cfg.criteria.locations)
    assert "NVIDIA" in cfg.criteria.priority_companies
    assert cfg.max_age_hours == 2
    assert cfg.empty_email_every_hours == 5
    assert cfg.quiet_hours == (0, 4)
    assert cfg.check_every_minutes == 30


@pytest.mark.parametrize("title,wanted", [
    ("Analog/Mixed-Signal IC Design Intern", True),
    ("RF Validation Intern (Summer 2027)", True),
    ("Digital RTL Design Engineer Intern", True),
    ("Embedded Software Engineer Intern", True),
    ("Senior Technical Intern - Firmware", True),
    ("Hardware/Software Testing Intern", True),
    ("PMU Intern", True),
    ("Public Policy Intern", False),                                 # "ic" inside a word
    ("Performance Engineering Intern", False),                       # "rf" inside a word
    ("Industrial Engineering Intern - Portland, OR", False),         # "rtl" inside Portland
    ("Power BI Intern", False),
    ("Software Development Engineer in Test", False),
    ("Civil Engineering & Construction Materials Testing Co-op", False),
    ("Software Engineer Intern", False),
])
def test_repo_config_ee_title_filter(title, wanted):
    eng = load_config(ROOT / "config.yaml").lists[0]
    assert eng.wants(title) is wanted


def test_list_spec_wants():
    s = ListSpec("eng", title_include=["Network Engineer"], title_exclude=["electrical"])
    assert s.wants("Network Engineering Intern, Summer 2027")
    assert not s.wants("Electrical Network Engineer Intern")
    assert not s.wants("Mechanical Intern")
    assert ListSpec("cs").wants("anything")


def test_bad_match_value(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("lists: [cs]\nmatch: some\n")
    with pytest.raises(ValueError, match="match"):
        load_config(p)


def test_company_sites_and_eligibility(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("""
lists: [cs]
company_sites:
  title_require: [intern]
  sites:
    - {company: Palo Alto Networks, greenhouse: pan}
eligibility: {graduation: 2028-05}
""")
    cfg = load_config(p)
    site = cfg.lists[-1]
    assert site.key == "site:palo-alto-networks" and site.company == "Palo Alto Networks"
    assert cfg.criteria.graduation == (2028, 5) and not cfg.criteria.skip_phd_only
    for bad in ("company_sites: {sites: [{company: X}]}",
                "company_sites: {sites: [{company: X, greenhouse: a, workday: b}]}",
                "company_sites: {sites: [{company: X, careers: meta}]}",
                "eligibility: {graduation: 2028}"):
        p.write_text("lists: [cs]\n" + bad + "\n")
        with pytest.raises(ValueError):
            load_config(p)


def test_skills_section(tmp_path):
    from jobscanner.config import load_config
    p = tmp_path / "c.yaml"
    p.write_text("lists: [cs]\nskills:\n  have: [Python, [Security+, Sec+]]\n  lack: [Java]\n")
    s = load_config(p).criteria.skills
    assert [x.name for x in s.have] == ["Python", "Security+"] and [x.name for x in s.lack] == ["Java"]
    p.write_text("lists: [cs]\nskills:\n  have: [[]]\n")
    with pytest.raises(ValueError, match="skills"):
        load_config(p)
