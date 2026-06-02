import os


class Config:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY environment variable is required")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self.gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))
        self.max_memory_messages = int(os.getenv("MAX_MEMORY_MESSAGES", "20"))

        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")

        # Cal.com booking integration
        self.calcom_username = os.getenv("CALCOM_USERNAME")
        self.calcom_api_key = os.getenv("CALCOM_API_KEY")
        self.calcom_event_slug = os.getenv("CALCOM_EVENT_SLUG", "30min")

        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        self.port = int(os.getenv("PORT", "8080"))
        self.env = os.getenv("ENV", "development")
