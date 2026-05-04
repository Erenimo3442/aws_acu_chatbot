"""Pre-configured scrape targets for Acibadem University.

URLs documented from Playwright exploration of both sites (2026-05-04).

Two site architectures:
  Site A — acibadem.edu.tr   : Drupal CMS, consistent HTML structure
  Site B — obs.acibadem.edu.tr: ASP.NET, content via iframe/dynConPage.aspx
"""

# ---------------------------------------------------------------------------
# Site A — Main university website (Drupal)
# ---------------------------------------------------------------------------

MAIN_SITE_BASE = "https://www.acibadem.edu.tr"

DRUPAL_PAGES: list[dict] = [
    # --- Admissions & International ---
    {
        "url": "/en/international-office/international-students",
        "title": "International Students — Admissions Overview",
        "source_tag": "acibadem_international",
        "category": "admissions",
    },
    {
        "url": "/en/international-office/international-students/useful-information/visa-residence-permit-and-health-insurance",
        "title": "Visa, Residence Permit and Health Insurance",
        "source_tag": "acibadem_visa",
        "category": "admissions",
    },
    # --- Academics & Programs ---
    {
        "url": "/en/academic",
        "title": "Academic Programs Overview",
        "source_tag": "acibadem_academics",
        "category": "programs",
    },
    {
        "url": "/en/akademik/lisans",
        "title": "Undergraduate Programs — Acibadem University",
        "source_tag": "acibadem_undergraduate",
        "category": "programs",
    },
    # --- Tuition & Scholarships ---
    {
        "url": "/en/international-office/international-students/useful-information/tuition-fees-and-scholarships",
        "title": "Tuition Fees and Scholarships",
        "source_tag": "acibadem_tuition",
        "category": "tuition",
    },
    {
        "url": "/en/student/about-payment",
        "title": "About Payment — Student Finance",
        "source_tag": "acibadem_payment",
        "category": "tuition",
    },
    # --- Campus Life ---
    {
        "url": "/en/node/6744",
        "title": "Life at ACU — Campus and Student Life",
        "source_tag": "acibadem_campus_life",
        "category": "campus_life",
    },
    {
        "url": "/en/student/life-at-acu/kerem-aydinlar-student-dormitories/about",
        "title": "Kerem Aydinlar Student Dormitories",
        "source_tag": "acibadem_dormitories",
        "category": "campus_life",
    },
    # --- Student Services ---
    {
        "url": "/en/ogrenci/ogrenci-isleri/academic-calendar",
        "title": "Academic Calendar",
        "source_tag": "acibadem_calendar",
        "category": "student_services",
    },
    {
        "url": "/en/international-office/international-students/useful-information/transportation",
        "title": "Transportation Information",
        "source_tag": "acibadem_transportation",
        "category": "student_services",
    },
    # --- University Info ---
    {
        "url": "/en/university",
        "title": "About Acibadem University",
        "source_tag": "acibadem_about",
        "category": "university_info",
    },
    {
        "url": "/en/university/about",
        "title": "About University — History and Mission",
        "source_tag": "acibadem_history",
        "category": "university_info",
    },
    # --- Research ---
    {
        "url": "/en/research",
        "title": "Research at Acibadem University",
        "source_tag": "acibadem_research",
        "category": "research",
    },
    # --- Sustainable Campus ---
    {
        "url": "/en/surdurulebilirlik/sustainable-campus",
        "title": "Sustainable Campus",
        "source_tag": "acibadem_sustainable",
        "category": "campus_life",
    },
]

# ---------------------------------------------------------------------------
# Site B — Bologna Information System (ASP.NET)
# ---------------------------------------------------------------------------

BOLOGNA_BASE = "https://obs.acibadem.edu.tr/oibs/bologna"

# Static content pages loaded via dynConPage.aspx?curPageId=X&lang=en
BOLOGNA_STATIC_PAGES: list[dict] = [
    # --- Information on the Institution ---
    {"curPageId": 100, "title": "Management", "category": "bologna_institution"},
    {"curPageId": 101, "title": "About University", "category": "bologna_institution"},
    {"curPageId": 102, "title": "Bologna Coordination Commission", "category": "bologna_institution"},
    {"curPageId": 103, "title": "Contact", "category": "bologna_institution"},
    {"curPageId": 104, "title": "ECTS Catalog", "category": "bologna_institution"},
    # --- General Information for Students ---
    {"curPageId": 300, "title": "About City", "category": "bologna_student_info"},
    {"curPageId": 301, "title": "About Campus", "category": "bologna_student_info"},
    {"curPageId": 302, "title": "Food", "category": "bologna_student_info"},
    {"curPageId": 303, "title": "Health Services", "category": "bologna_student_info"},
    {"curPageId": 304, "title": "Sports and Social Life", "category": "bologna_student_info"},
    {"curPageId": 305, "title": "Student Clubs", "category": "bologna_student_info"},
    {"curPageId": 309, "title": "Accommodation", "category": "bologna_student_info"},
    {"curPageId": 311, "title": "Facilities for Special Needs Students", "category": "bologna_student_info"},
    # --- Erasmus ---
    {"curPageId": 401, "title": "Erasmus+ Charter", "category": "bologna_erasmus"},
    # --- Bologna Process ---
    {"curPageId": 400, "title": "Bologna Process", "category": "bologna_process"},
]

# Degree-level program listing pages
# type=myo (Associate's), lis (Bachelor's), yls (Master's), dok (Doctorate)
BOLOGNA_DEGREE_LEVELS: list[dict] = [
    {"type": "myo", "level": "Associate's Degree"},
    {"type": "lis", "level": "Bachelor's Degree"},
    {"type": "yls", "level": "Master's Degree"},
    {"type": "dok", "level": "Doctorate Degree"},
]

# Program detail sub-pages discovered on 2026-05-04.
# Each program (identified by curSunit) has these accessible sub-pages.
# Pattern: {func}.aspx?lang=en&curSunit={curSunit}
BOLOGNA_PROGRAM_SUBPAGES: list[dict] = [
    {"func": "progGoalsObjectives", "label": "Type of Education (Goal) and Objectives"},
    {"func": "progAbout", "label": "About Programme"},
    {"func": "progProfile", "label": "Profile of the Programme"},
    {"func": "progOfficials", "label": "Programme Director or Equivalent"},
    {"func": "progDegree", "label": "Qualification Awarded"},
    {"func": "progAdmissionReq", "label": "Specific Admission Requirements"},
    {"func": "progAccessFurhterStudies", "label": "Access to Further Studies"},
    {"func": "progGraduationReq", "label": "Graduation Requirements"},
    {"func": "progRecogPriorLearning", "label": "Recognition of Prior Learning"},
    {"func": "progQualifyReqReg", "label": "Qualification Req. and Regulations"},
    {"func": "progOccupationalProf", "label": "Occupational Profiles of Graduates"},
    {"func": "progLearnOutcomes", "label": "Program Learning Outcomes"},
    {"func": "progCourses", "label": "Course Structure"},
    {"func": "progCourseMatrix", "label": "Course & Programme Outcomes Matrix"},
    {"func": "progTYYCMatrix", "label": "NQF - Fields & Programme Outcomes Matrix"},
    {"func": "progAcademicStaff", "label": "Academic Staff"},
    {"func": "progContact", "label": "Contact Information"},
]


def build_drupal_full_urls() -> list[dict]:
    """Return Drupal pages with full absolute URLs."""
    return [
        {**page, "url": f"{MAIN_SITE_BASE}{page['url']}"}
        for page in DRUPAL_PAGES
    ]


def build_bologna_static_urls() -> list[dict]:
    """Return Bologna static pages with full dynConPage URLs."""
    return [
        {
            **page,
            "url": f"{BOLOGNA_BASE}/dynConPage.aspx?curPageId={page['curPageId']}&lang=en",
        }
        for page in BOLOGNA_STATIC_PAGES
    ]


def build_bologna_unit_selection_urls() -> list[dict]:
    """Return unit selection pages for each degree level."""
    return [
        {
            **level,
            "url": f"{BOLOGNA_BASE}/unitSelection.aspx?type={level['type']}&lang=en",
            "category": "bologna_program_listing",
        }
        for level in BOLOGNA_DEGREE_LEVELS
    ]


def build_program_detail_url(cur_sunit: int, func: str) -> str:
    """Build a single program detail sub-page URL."""
    return f"{BOLOGNA_BASE}/{func}.aspx?lang=en&curSunit={cur_sunit}"


def build_program_landing_url(cur_unit: int, cur_sunit: int) -> str:
    """Build the landing/index URL for a specific program."""
    return (
        f"{BOLOGNA_BASE}/index.aspx?lang=en&curOp=showPac"
        f"&curUnit={cur_unit}&curSunit={cur_sunit}"
    )
