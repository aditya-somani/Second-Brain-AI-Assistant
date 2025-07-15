#So , the big question is , why make this config file ?
# Answer : It solves the common problem of scattering configuration values throughout a codebase or managing them in insecure, error-prone ways. 
# Hardcoding secrets is a security risk, and manually loading from files can lead to missing values or type errors at runtime. 
# This code ensures that all required settings are present and correctly formatted before the application starts.

# How it works: It uses the Pydantic library to automatically read settings from environment variables and a .env file. 
# It validates their data types (e.g., ensuring a key is a string) and even runs custom checks (like making sure an API key isn't empty). 
# If any configuration is invalid, the application fails immediately with a clear error message.

# NOTE :- Check the pydantic documentation for more details on all things used in this file


from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict #refer to the pydantic -> Settings Management documentation for more details

class Settings(BaseSettings):
    """
    A Pydantic-based settings class for managing application configurations.
    """
    # ---Pydantic Settings---

    # model_config is a special variable name that Pydantic looks for. 
    # It is assigned a SettingsConfigDict, which is essentially a dictionary for configuration.
    model_config:SettingsConfigDict = SettingsConfigDict(
        env_file = '.env',
        env_file_encoding = 'utf-8'
    ) 

    # ---AWS Configuration---
    AWS_ACCESS_KEY:str | None = Field(
        default = None, description = "AWS Access Key for authentication"
    )

    AWS_SECRET_KEY:str | None = Field(
        default = None, description = "AWS Secret Key for authentication"
    )

    AWS_DEFAULT_REGION:str = Field(
        default = 'eu-central-1', description = "AWS Region for the cloud services"
    )

    AWS_S3_BUCKET_NAME:str = Field(
        default="decodingml-public-data", #Gotta change this to the actual bucket name currently using this for testing purposes
        description = "AWS S3 Bucket Name for the application data"
    )

    # --- Comet ML & Opik Configuration ---
    COMET_API_KEY:str | None = Field(
        default = None, description = "API key for Comet ML and Opik services."
    )

    COMET_PROJECT: str = Field(
        default="second_brain_course", #Gotta change this to the actual project name currently using this for testing purposes
        description="Project name for Comet ML and Opik tracking.",
    )

    # --- Hugging Face Configuration ---
    HUGGINGFACE_ACCESS_TOKEN: str | None = Field(
        default=None, description="Access token for Hugging Face API authentication."
    )
    HUGGINGFACE_DEDICATED_ENDPOINT: str | None = Field(
        default=None,
        description="Dedicated endpoint URL for real-time inference. "
        "If provided, we will use the dedicated endpoint instead of OpenAI. "
        "For example, https://um18v2aeit3f6g1b.eu-west-1.aws.endpoints.huggingface.cloud/v1/, "
        "with /v1 after the endpoint URL.",
    )

    # --- MongoDB Atlas Configuration ---
    MONGODB_DATABASE_NAME: str = Field(
        default="second_brain_course",
        description="Name of the MongoDB database.",
    )
    MONGODB_URI: str = Field(
        default="mongodb://decodingml:decodingml@localhost:27017/?directConnection=true",
        description="Connection URI for the local MongoDB Atlas instance.",
    )

    # --- Notion API Configuration ---
    NOTION_SECRET_KEY: str | None = Field(
        default=None, description="Secret key for Notion API authentication."
    )

    # ---Gemini Configuration ---
    GEMINI_API_KEY: str = Field(
        description="API key for Gemini API authentication."
    )

    @field_validator('GEMINI_API_KEY')
    # This is a custom validator function for a specific field.
    # Purpose: To add validation logic that goes beyond simple type checking. In this case, it ensures the OPENAI_API_KEY is not an empty string.
    @classmethod #Validators in Pydantic are typically class methods 
    def check_not_empty(cls, value:str, info) -> str:
        # cls: This is the class itself (Settings in this case).
        # value: This is the value of the field being validated (e.g., the actual API key string).
        # info: An object containing metadata about the field, such as its name (info.field_name).
        if not value or value.strip() == '':
            logger.error(f"The {info.field_name} cannot be empty")
            raise ValueError(f"The {info.field_name} cannot be empty")
        return value
    
try:
    settings = Settings()
except Exception as e:
    logger.error(f"Error loading configuration: {e}")
    raise SystemExit(e)

    

    





