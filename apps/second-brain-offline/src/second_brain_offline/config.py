#So , the big question is , why make this config file ?
# Answer : It solves the common problem of scattering configuration values throughout a codebase or managing them in insecure, error-prone ways. 
# Hardcoding secrets is a security risk, and manually loading from files can lead to missing values or type errors at runtime. 
# This code ensures that all required settings are present and correctly formatted before the application starts.

# How it works: It uses the Pydantic library to automatically read settings from environment variables and a .env file. 
# It validates their data types (e.g., ensuring a key is a string) and even runs custom checks (like making sure an API key isn't empty). 
# If any configuration is invalid, the application fails immediately with a clear error message.



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

    
