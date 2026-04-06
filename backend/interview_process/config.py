import os
from dotenv import load_dotenv
# Configuration settings

# Load .env explicitly from this directory or parent
current_dir = os.path.dirname(__file__)
env_path = os.path.join(current_dir, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(current_dir, "..", ".env")

load_dotenv(env_path, override=True)

OPENROUTER_API_KEY = os.getenv("GROQ_API_KEY")

# Fallback or Error
if not OPENROUTER_API_KEY:
    print(f"WARNING: GROQ_API_KEY not found in {env_path}. Checking system env...")
    OPENROUTER_API_KEY = os.getenv("GROQ_API_KEY")

if not OPENROUTER_API_KEY:
    print("CRITICAL WARNING: GROQ_API_KEY is missing. AI features will fail.")

OPENROUTER_BASE_URL = "https://api.groq.com/openai/v1"
MODEL_NAME = "llama-3.3-70b-versatile"

# Interview settings
MAX_QUESTIONS = 20
MIN_QUESTIONS = 3
QUESTION_DIFFICULTY_LEVELS = ["basic", "intermediate", "advanced", "scenario-based"]

# Skill categories
SKILL_CATEGORIES = {
    # Core Engineering / Specialized Domains (Moved to TOP for priority matching)
    "CAE-MECHANICAL":[
        "CAE", "Mechanical Engineering", "CAE-MECHANICAL",
        "HyperMesh", "OptiStruct", "LS-DYNA",
        "HyperView", "FEA fundamentals", "Structural Mechanics",
        "Material Science", "GD&T", "PLM Systems", "Thermal Analysis",
        "ANSYS", "Abaqus", "SolidWorks", "Catia"
    ],

    "Steel_detailing": [
        "tekla", "autocad", "SDS2", "Bluebeam",
        "Shop Drawings", "GA Drawings", "OSHA standards",
        "isometric views", "projection", "Steel detailing",
        "Tekla EPM", "Power Fab", "PowerFab", "ABM", "KSS",
        "3D Modeling", "2D drawings", "AISC", "CISC",
        "Structural detailing", "Estimation", "BOM",
        "RFI management", "Steel construction", "fabrication packages"
    ],

    # Software Development
    "frontend": [
        "Frontend",
        "JavaScript", "React", "Angular", "Vue",
        "HTML", "CSS", "TypeScript"
    ],

    "backend": [
        "Python", "Java", "Node.js", "C#", "Go",
        "Databases", "REST APIs", "Microservices"
    ],

    # Data & AI
    "data_analysis": [
        "Data Science", "Data Engineering",
        "Python", "SQL",
        "Data Analysis",
        "Machine Learning",
        "Deep Learning",
        "PyTorch",
        "TensorFlow",
        "Big Data", 
        "Analytics"
    ],

    "fullstack": [
        "Fullstack",
        "Frontend + Backend",
        "End-to-End Application Development",
        "System Design",
        "DevOps Basics"
    ],

    "devops": [
        "DevOps",
        "AWS", "Azure", "GCP",
        "Docker", "Kubernetes",
        "CI/CD Pipelines",
        "Terraform",
        "Linux"
    ],

    "networking": [
        "Networking", "Network Engineering",
        "Computer Networks",
        "TCP/IP",
        "Routing & Switching",
        "LAN / WAN",
        "DNS",
        "DHCP",
        "Firewalls",
        "VPN",
        "Network Security"
    ],
    # Mobile Development
    "mobile": [
        "App Development",
        "iOS Development", "Android Development",
        "Android",
        "iOS",
        "React Native",
        "Flutter",
        "Swift", "Kotlin"
    ],

    # Human Resources
    "hr": [
        "HR", "Human Resources",
        "Recruitment & Staffing",
        "Talent Acquisition",
        "HR Operations",
        "Payroll Management",
        "Employee Relations",
        "Performance Management",
        "HR Policies & Compliance",
        "Onboarding & Offboarding"
    ],

    # Additional Useful Domains
    "qa_testing": [
        "QA", "Testing", "Quality Assurance",
        "Manual Testing",
        "Automation Testing",
        "Selenium",
        "Cypress",
        "API Testing",
        "Performance Testing"
    ],

    "ui_ux": [
        "UI", "UX", "UI/UX", "Product Design",
        "User Research",
        "Wireframing",
        "Prototyping",
        "Figma",
        "Adobe XD",
        "Usability Testing"
    ],

    "cybersecurity": [
        "Cybersecurity", "Security", "InfoSec",
        "Information Security",
        "Threat Modeling",
        "Vulnerability Assessment",
        "Penetration Testing",
        "IAM",
        "SIEM",
        "SOC Operations"
    ]
}


# Termination keywords
TERMINATION_KEYWORDS = [
    "terminate the interview", "i want to quit", "i want to exit", 
    "i want to end the interview", "quit the interview", "exit the interview",
    "stop the interview", "end this now", "cancel interview"
] 
ABUSIVE_KEYWORDS = [
    "fuck", "shit", "stupid", "idiot", "dumb", "worthless", "hate", "useless",
    "bitch", "bastard", "asshole", "damn", "crap"
]
