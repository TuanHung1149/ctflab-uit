from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    OVPN_SERVER_IP: str = "0.0.0.0"
    OVPN_SERVER_PORT: int = 1194
    OVPN_PROTO: str = "udp"
    DOCKER_SUBNET_PREFIX: str = "10.100"
    MAX_INSTANCES_PER_USER: int = 1
    INSTANCE_LIFETIME_HOURS: int = 4
    MAX_SLOT: int = 50

    model_config = {"env_file": ".env"}


settings = Settings()
