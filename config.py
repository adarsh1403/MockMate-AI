import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Application configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        basedir, "database.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Groq API Configuration
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
