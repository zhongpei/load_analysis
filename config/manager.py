#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration classes and enums for load analyzer
"""
import os
import json
import yaml
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path


class OutputFormat(Enum):
    """Output format enumeration"""
    TEXT = "text"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class Config:
    """Configuration for load analyzer"""
    # Sampling configuration
    sample_interval: int = 1
    sample_count: int = 1
    
    # Output configuration
    output_format: OutputFormat = OutputFormat.TEXT
    output_file: Optional[str] = None
    enable_colors: bool = True
    
    # Thresholds
    load_threshold_multiplier: float = 1.5
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0
    swap_threshold: float = 50.0
    iowait_threshold: float = 30.0
    
    # Network thresholds
    tcp_connections_threshold: int = 1000
    tcp_backlog_threshold: int = 100
    
    # Process analysis
    top_processes_count: int = 10
    
    # Advanced thresholds
    context_switches_threshold: int = 10000
    interrupts_threshold: int = 5000
    disk_io_read_threshold: int = 100 * 1024 * 1024  # 100MB/s
    disk_io_write_threshold: int = 100 * 1024 * 1024  # 100MB/s
    
    # Alert configuration
    enable_alerts: bool = False
    alert_webhook_url: Optional[str] = None
    alert_slack_token: Optional[str] = None
    alert_slack_channel: Optional[str] = None
    
    # Prometheus exporter
    enable_prometheus: bool = False
    prometheus_port: int = 8000
    
    # Data retention
    enable_history: bool = False
    history_file: Optional[str] = None
    history_retention_days: int = 7
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()
    
    def validate(self) -> None:
        """Validate configuration values"""
        if self.sample_interval <= 0:
            raise ValueError("sample_interval must be positive")
        
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        
        if not 0 < self.load_threshold_multiplier <= 10:
            raise ValueError("load_threshold_multiplier must be between 0 and 10")
        
        if not 0 <= self.cpu_threshold <= 100:
            raise ValueError("cpu_threshold must be between 0 and 100")
        
        if not 0 <= self.memory_threshold <= 100:
            raise ValueError("memory_threshold must be between 0 and 100")
        
        if not 0 <= self.iowait_threshold <= 100:
            raise ValueError("iowait_threshold must be between 0 and 100")
        
        if self.tcp_connections_threshold <= 0:
            raise ValueError("tcp_connections_threshold must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary"""
        config_data = data.copy()
        
        # Convert output_format string to enum
        if 'output_format' in config_data:
            config_data['output_format'] = OutputFormat(config_data['output_format'])
        
        return cls(**config_data)


class ConfigManager:
    """Configuration manager for loading and saving configurations"""
    
    DEFAULT_CONFIG_PATHS = [
        "config/default.yaml",
        "~/.load_analyzer/config.yaml",
        "/etc/load_analyzer/config.yaml"
    ]
    
    @staticmethod
    def load_config(config_file: Optional[str] = None) -> Config:
        """Load configuration from file or use defaults"""
        config = Config()
        
        config_path = ConfigManager._find_config_file(config_file)
        
        if config_path:
            try:
                config_data = ConfigManager._load_config_file(config_path)
                config = Config.from_dict(config_data)
            except Exception as e:
                print(f"Warning: Failed to load config file {config_path}: {e}")
                print("Using default configuration...")
        
        return config
    
    @staticmethod
    def _find_config_file(config_file: Optional[str] = None) -> Optional[str]:
        """Find configuration file to use"""
        if config_file:
            if os.path.exists(config_file):
                return config_file
            else:
                raise FileNotFoundError(f"Specified config file not found: {config_file}")
        
        # Try default paths
        for path in ConfigManager.DEFAULT_CONFIG_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
        
        return None
    
    @staticmethod
    def _load_config_file(config_path: str) -> Dict[str, Any]:
        """Load configuration data from file"""
        path = Path(config_path)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f) or {}
            elif path.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
    
    @staticmethod
    def save_config(config: Config, config_file: str) -> None:
        """Save configuration to file"""
        path = Path(config_file)
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = config.to_dict()
        
        with open(config_file, 'w', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            elif path.suffix.lower() == '.json':
                json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
    
    @staticmethod
    def create_default_config(config_file: str) -> None:
        """Create a default configuration file"""
        config = Config()
        ConfigManager.save_config(config, config_file)
        print(f"Default configuration saved to {config_file}")
