import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        (
            f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', 'root')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'iam_db')}"
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    PASSWORD_RESET_TOKEN_EXPIRES_SECONDS = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRES_SECONDS", "1800")
    )
    SECURITY_RECOVERY_MAX_ATTEMPTS = int(
        os.getenv("SECURITY_RECOVERY_MAX_ATTEMPTS", "5")
    )
    SECURITY_RECOVERY_LOCKOUT_MINUTES = int(
        os.getenv("SECURITY_RECOVERY_LOCKOUT_MINUTES", "15")
    )
    SECURITY_RECOVERY_CHALLENGE_TTL_MINUTES = int(
        os.getenv("SECURITY_RECOVERY_CHALLENGE_TTL_MINUTES", "10")
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///test.db")


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
