# config.py
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')

    HTTP_SERVER_PORT = int(os.getenv('HTTP_SERVER_PORT')) if os.getenv('HTTP_SERVER_PORT') else None
    HTTP_SERVER_ADDRESS= os.getenv('HTTP_SERVER_ADDRESS')
    HTTP_SERVER_DEBUG= os.getenv('HTTP_SERVER_DEBUG').lower() in ['true', '1', 't', 'y', 'yes']