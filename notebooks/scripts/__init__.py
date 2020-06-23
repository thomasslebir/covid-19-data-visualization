import os
import logging.config

config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs", "logging.conf"))
logging.config.fileConfig(config_path, disable_existing_loggers=False)
logger = logging.getLogger(__name__)
