from app.model import * 
from sqlmodel import create_engine
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL") 

# Create engine
engine = create_engine(DATABASE_URL, echo=True)