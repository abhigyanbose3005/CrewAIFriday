from pathlib import Path

# Home Directory
HOME_DIR = Path(Path(__file__).resolve()).parent.parent

# Subdirectories
CONFIG_DIR = Path(HOME_DIR, "config")
PAGES_DIR = Path(HOME_DIR, "pages")
CSS_DIR = Path(CONFIG_DIR, "css")

# Database and Data Paths
#DATA_DIR = Path(HOME_DIR, "data")
#CHROMADB_DIR = Path(DATA_DIR, "chromadb")
#TEMP_DIR = Path(DATA_DIR, "temp")

if __name__ == "__main__":
    print(f"HOME_DIR: {HOME_DIR}")
    print(f"CONFIG_DIR: {CONFIG_DIR}")
    

APPS = [
    {"name": "Personal ChatBot",
     "description": "Personal ChatBot",
     "page": "home.py",
     "access_privilege_role": ["user"],
    },
    {"name": "Personal ChatBot",
     "description": "Personal ChatBot",
     "page": "home.py",
     "access_privilege_role": ["admin"],
    },
]