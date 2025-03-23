#!/usr/bin/env python3
"""
config_manager.py

Handles configuration loading and validation.
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path

DEFAULT_CONFIG = {
    "processing": {
        "dpi": 300,
        "ocr_lang": "eng",
        "min_confidence": 0.75
    },
    "display": {
        "window_width": 1200,
        "window_height": 800
    },
    "paths": {
        "output_dir": "output",
        "temp_dir": "temp",
        "log_dir": "logs"
    }
}

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file with fallback to defaults.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict containing configuration
    """
    config = DEFAULT_CONFIG.copy()
    
    # If config file exists, update defaults
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                _deep_update(config, file_config)
                
    return config

def _deep_update(base: Dict, update: Dict) -> None:
    """
    Recursively update a nested dictionary.
    
    Args:
        base: Base dictionary to update
        update: Dictionary with updates
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in base:
            _deep_update(base[key], value)
        else:
            base[key] = value

def save_config(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save configuration
    """
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def validate_paths(config: Dict[str, Any]) -> None:
    """
    Validate and create necessary paths from config.
    
    Args:
        config: Configuration dictionary
    """
    for key, path in config['paths'].items():
        Path(path).mkdir(parents=True, exist_ok=True)

def get_temp_dir(config: Dict[str, Any]) -> str:
    """Get temporary directory path."""
    return config['paths']['temp_dir']

def get_output_dir(config: Dict[str, Any]) -> str:
    """Get output directory path."""
    return config['paths']['output_dir']
