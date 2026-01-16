import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5004))

    @staticmethod
    def validate():
        """Valida se as configurações necessárias estão presentes"""
        if not Config.SUPABASE_URL:
            raise ValueError("SUPABASE_URL não configurada")
        if not Config.SUPABASE_KEY:
            raise ValueError("SUPABASE_KEY não configurada")
        return True