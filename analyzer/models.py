#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis models and data structures
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.models import MetricsData, ProcessInfo


class IssueType(Enum):
    """Types of system issues"""
    CPU = "cpu"
    MEMORY = "memory" 
    IOWAIT = "iowait"
    NETWORK = "network"
    DISK_IO = "disk_io"
    LOAD = "load"
    PROCESS = "process"


class IssueSeverity(Enum):
    """Severity levels for issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LoadStatus(Enum):
    """Load status enumeration"""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Issue:
    """Represents a system issue"""
    type: IssueType
    severity: IssueSeverity
    message: str
    value: float
    threshold: float
    recommendation: str
    related_processes: List[ProcessInfo] = field(default_factory=list)
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type.value,
            'severity': self.severity.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'recommendation': self.recommendation,
            'related_processes': [
                {
                    'pid': proc.pid,
                    'name': proc.name,
                    'cpu_percent': proc.cpu_percent,
                    'memory_percent': proc.memory_percent,
                    'cmdline': proc.cmdline
                }
                for proc in self.related_processes[:3]  # Limit to top 3
            ],
            'additional_data': self.additional_data
        }


@dataclass
class AnalysisResult:
    """Complete analysis result"""
    timestamp: str
    load_status: LoadStatus
    primary_issues: List[Issue] = field(default_factory=list)
    secondary_issues: List[Issue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_issues(self) -> List[Issue]:
        """Get all issues combined"""
        return self.primary_issues + self.secondary_issues
    
    def get_critical_issues(self) -> List[Issue]:
        """Get only critical issues"""
        return [issue for issue in self.get_all_issues() 
                if issue.severity == IssueSeverity.CRITICAL]
    
    def get_high_issues(self) -> List[Issue]:
        """Get high severity issues"""
        return [issue for issue in self.get_all_issues() 
                if issue.severity == IssueSeverity.HIGH]
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return len(self.get_critical_issues()) > 0
    
    def has_high_issues(self) -> bool:
        """Check if there are high severity issues"""
        return len(self.get_high_issues()) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'load_status': self.load_status.value,
            'primary_issues': [issue.to_dict() for issue in self.primary_issues],
            'secondary_issues': [issue.to_dict() for issue in self.secondary_issues],
            'recommendations': self.recommendations,
            'summary': self.summary
        }
