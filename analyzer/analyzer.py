#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligent system load analyzer
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from collector.models import MetricsData
from analyzer.models import (
    AnalysisResult, Issue, IssueType, IssueSeverity, LoadStatus
)


class Analyzer:
    """Intelligent system load analyzer"""
    
    def __init__(self, config: Config):
        self.config = config
        self.previous_metrics: Optional[MetricsData] = None
    
    def analyze(self, metrics: MetricsData) -> AnalysisResult:
        """Perform complete system analysis"""
        result = AnalysisResult(
            timestamp=metrics.timestamp,
            load_status=self._determine_load_status(metrics)
        )
        
        # Analyze different aspects of the system
        self._analyze_load(metrics, result)
        self._analyze_cpu(metrics, result)
        self._analyze_memory(metrics, result)
        self._analyze_disk_io(metrics, result)
        self._analyze_network(metrics, result)
        
        # Generate recommendations
        self._generate_recommendations(result)
        
        # Create summary
        self._create_summary(metrics, result)
        
        # Store for comparison in next analysis
        self.previous_metrics = metrics
        
        return result
    
    def _determine_load_status(self, metrics: MetricsData) -> LoadStatus:
        """Determine overall load status"""
        load_threshold = metrics.load.cpu_count * self.config.load_threshold_multiplier
        load1 = metrics.load.load1
        
        if load1 > load_threshold * 2:
            return LoadStatus.CRITICAL
        elif load1 > load_threshold * 1.5:
            return LoadStatus.HIGH
        elif load1 > load_threshold:
            return LoadStatus.ELEVATED
        else:
            return LoadStatus.NORMAL
    
    def _analyze_load(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Analyze load averages"""
        load_threshold = metrics.load.cpu_count * self.config.load_threshold_multiplier
        
        if metrics.load.load1 > load_threshold:
            severity = self._get_severity_by_ratio(
                metrics.load.load1, load_threshold, 1.5, 2.0
            )
            
            issue = Issue(
                type=IssueType.LOAD,
                severity=severity,
                message=f"High load average: {metrics.load.load1:.2f} (threshold: {load_threshold:.2f})",
                value=metrics.load.load1,
                threshold=load_threshold,
                recommendation="Investigate CPU, I/O, or process issues",
                additional_data={
                    'load5': metrics.load.load5,
                    'load15': metrics.load.load15,
                    'cpu_count': metrics.load.cpu_count
                }
            )
            
            if severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]:
                result.primary_issues.append(issue)
            else:
                result.secondary_issues.append(issue)
    
    def _analyze_cpu(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Analyze CPU metrics"""
        # Overall CPU usage
        if metrics.cpu.avg_usage > self.config.cpu_threshold:
            severity = self._get_severity_by_ratio(
                metrics.cpu.avg_usage, self.config.cpu_threshold, 90.0, 95.0
            )
            
            issue = Issue(
                type=IssueType.CPU,
                severity=severity,
                message=f"High CPU usage: {metrics.cpu.avg_usage:.1f}% (threshold: {self.config.cpu_threshold}%)",
                value=metrics.cpu.avg_usage,
                threshold=self.config.cpu_threshold,
                recommendation="Consider CPU scaling or process optimization",
                related_processes=metrics.top_processes.get('by_cpu', [])[:3],
                additional_data={
                    'usage_per_core': metrics.cpu.usage_per_core,
                    'context_switches': metrics.cpu.context_switches,
                    'interrupts': metrics.cpu.interrupts
                }
            )
            
            if severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]:
                result.primary_issues.append(issue)
            else:
                result.secondary_issues.append(issue)
        
        # I/O wait analysis
        if metrics.cpu.iowait_percent > self.config.iowait_threshold:
            severity = self._get_severity_by_ratio(
                metrics.cpu.iowait_percent, self.config.iowait_threshold, 50.0, 70.0
            )
            
            issue = Issue(
                type=IssueType.IOWAIT,
                severity=severity,
                message=f"High I/O wait: {metrics.cpu.iowait_percent:.1f}% (threshold: {self.config.iowait_threshold}%)",
                value=metrics.cpu.iowait_percent,
                threshold=self.config.iowait_threshold,
                recommendation="Check disk performance and optimize I/O operations",
                related_processes=metrics.top_processes.get('by_io', [])[:3],
                additional_data={
                    'disk_io': metrics.disk_io.to_dict() if hasattr(metrics.disk_io, 'to_dict') else {}
                }
            )
            
            result.primary_issues.append(issue)
        
        # Context switches analysis
        if metrics.cpu.context_switches > self.config.context_switches_threshold:
            issue = Issue(
                type=IssueType.CPU,
                severity=IssueSeverity.MEDIUM,
                message=f"High context switches: {metrics.cpu.context_switches} (threshold: {self.config.context_switches_threshold})",
                value=float(metrics.cpu.context_switches),
                threshold=float(self.config.context_switches_threshold),
                recommendation="Check for excessive process/thread creation or contention",
                additional_data={'interrupts': metrics.cpu.interrupts}
            )
            
            result.secondary_issues.append(issue)
    
    def _analyze_memory(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Analyze memory metrics"""
        # Memory usage
        if metrics.memory.used_percent > self.config.memory_threshold:
            severity = self._get_severity_by_ratio(
                metrics.memory.used_percent, self.config.memory_threshold, 90.0, 95.0
            )
            
            issue = Issue(
                type=IssueType.MEMORY,
                severity=severity,
                message=f"High memory usage: {metrics.memory.used_percent:.1f}% (threshold: {self.config.memory_threshold}%)",
                value=metrics.memory.used_percent,
                threshold=self.config.memory_threshold,
                recommendation="Consider memory scaling or optimize memory-intensive processes",
                related_processes=metrics.top_processes.get('by_memory', [])[:3],
                additional_data={
                    'total_gb': metrics.memory.total_gb,
                    'available_gb': metrics.memory.available_gb,
                    'buffers_gb': metrics.memory.buffers_gb,
                    'cached_gb': metrics.memory.cached_gb
                }
            )
            
            if severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]:
                result.primary_issues.append(issue)
            else:
                result.secondary_issues.append(issue)
        
        # Swap usage
        if metrics.memory.swap_percent > self.config.swap_threshold:
            severity = self._get_severity_by_ratio(
                metrics.memory.swap_percent, self.config.swap_threshold, 70.0, 90.0
            )
            
            issue = Issue(
                type=IssueType.MEMORY,
                severity=severity,
                message=f"High swap usage: {metrics.memory.swap_percent:.1f}% (threshold: {self.config.swap_threshold}%)",
                value=metrics.memory.swap_percent,
                threshold=self.config.swap_threshold,
                recommendation="Increase physical memory or reduce memory usage",
                additional_data={'swap_total_gb': metrics.memory.swap_total_gb}
            )
            
            result.secondary_issues.append(issue)
    
    def _analyze_disk_io(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Analyze disk I/O metrics"""
        # Check read rate
        if metrics.disk_io.read_rate and metrics.disk_io.read_rate > self.config.disk_io_read_threshold:
            issue = Issue(
                type=IssueType.DISK_IO,
                severity=IssueSeverity.MEDIUM,
                message=f"High disk read rate: {metrics.disk_io.read_rate / (1024**2):.1f} MB/s",
                value=metrics.disk_io.read_rate,
                threshold=float(self.config.disk_io_read_threshold),
                recommendation="Check for excessive disk read operations",
                related_processes=metrics.top_processes.get('by_io', [])[:3],
                additional_data={
                    'read_bytes': metrics.disk_io.read_bytes,
                    'read_count': metrics.disk_io.read_count,
                    'read_time': metrics.disk_io.read_time
                }
            )
            
            result.secondary_issues.append(issue)
        
        # Check write rate
        if metrics.disk_io.write_rate and metrics.disk_io.write_rate > self.config.disk_io_write_threshold:
            issue = Issue(
                type=IssueType.DISK_IO,
                severity=IssueSeverity.MEDIUM,
                message=f"High disk write rate: {metrics.disk_io.write_rate / (1024**2):.1f} MB/s",
                value=metrics.disk_io.write_rate,
                threshold=float(self.config.disk_io_write_threshold),
                recommendation="Check for excessive disk write operations",
                related_processes=metrics.top_processes.get('by_io', [])[:3],
                additional_data={
                    'write_bytes': metrics.disk_io.write_bytes,
                    'write_count': metrics.disk_io.write_count,
                    'write_time': metrics.disk_io.write_time
                }
            )
            
            result.secondary_issues.append(issue)
    
    def _analyze_network(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Analyze network metrics"""
        # TCP connections
        if metrics.network.total_connections > self.config.tcp_connections_threshold:
            severity = self._get_severity_by_ratio(
                float(metrics.network.total_connections),
                float(self.config.tcp_connections_threshold),
                float(self.config.tcp_connections_threshold * 1.5),
                float(self.config.tcp_connections_threshold * 2.0)
            )
            
            issue = Issue(
                type=IssueType.NETWORK,
                severity=severity,
                message=f"High TCP connections: {metrics.network.total_connections} (threshold: {self.config.tcp_connections_threshold})",
                value=float(metrics.network.total_connections),
                threshold=float(self.config.tcp_connections_threshold),
                recommendation="Check for connection leaks or scaling needs",
                additional_data={
                    'tcp_states': metrics.network.tcp_connections,
                    'bytes_sent': metrics.network.bytes_sent,
                    'bytes_recv': metrics.network.bytes_recv
                }
            )
            
            result.secondary_issues.append(issue)
        
        # Check for unusual connection states
        tcp_states = metrics.network.tcp_connections
        if isinstance(tcp_states, dict):
            time_wait_count = tcp_states.get('TIME_WAIT', 0)
            close_wait_count = tcp_states.get('CLOSE_WAIT', 0)
            
            if time_wait_count > 1000:
                issue = Issue(
                    type=IssueType.NETWORK,
                    severity=IssueSeverity.MEDIUM,
                    message=f"High TIME_WAIT connections: {time_wait_count}",
                    value=float(time_wait_count),
                    threshold=1000.0,
                    recommendation="Check TCP timeout settings and connection handling",
                    additional_data={'tcp_states': tcp_states}
                )
                
                result.secondary_issues.append(issue)
            
            if close_wait_count > 500:
                issue = Issue(
                    type=IssueType.NETWORK,
                    severity=IssueSeverity.MEDIUM,
                    message=f"High CLOSE_WAIT connections: {close_wait_count}",
                    value=float(close_wait_count),
                    threshold=500.0,
                    recommendation="Application may not be properly closing connections",
                    additional_data={'tcp_states': tcp_states}
                )
                
                result.secondary_issues.append(issue)
    
    def _get_severity_by_ratio(self, value: float, threshold: float, 
                              high_multiplier: float, critical_multiplier: float) -> IssueSeverity:
        """Determine severity based on how much value exceeds threshold"""
        if value > threshold * critical_multiplier:
            return IssueSeverity.CRITICAL
        elif value > threshold * high_multiplier:
            return IssueSeverity.HIGH
        elif value > threshold:
            return IssueSeverity.MEDIUM
        else:
            return IssueSeverity.LOW
    
    def _generate_recommendations(self, result: AnalysisResult) -> None:
        """Generate general recommendations based on issues"""
        recommendations = set()
        
        for issue in result.get_all_issues():
            recommendations.add(issue.recommendation)
        
        # Add general recommendations based on load status
        if result.load_status == LoadStatus.CRITICAL:
            recommendations.add("URGENT: System is under critical load - immediate action required")
        elif result.load_status == LoadStatus.HIGH:
            recommendations.add("System is under high load - investigate primary issues")
        
        # Add specific recommendations based on issue combinations
        cpu_issues = [i for i in result.get_all_issues() if i.type == IssueType.CPU]
        memory_issues = [i for i in result.get_all_issues() if i.type == IssueType.MEMORY]
        iowait_issues = [i for i in result.get_all_issues() if i.type == IssueType.IOWAIT]
        
        if cpu_issues and memory_issues:
            recommendations.add("High CPU and memory usage detected - consider vertical scaling")
        
        if iowait_issues and any(i.type == IssueType.DISK_IO for i in result.get_all_issues()):
            recommendations.add("I/O bottleneck detected - consider faster storage or I/O optimization")
        
        result.recommendations = list(recommendations)
    
    def _create_summary(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """Create analysis summary"""
        result.summary = {
            'total_issues': len(result.get_all_issues()),
            'critical_issues': len(result.get_critical_issues()),
            'high_issues': len(result.get_high_issues()),
            'load_ratio': metrics.load.load1 / (metrics.load.cpu_count * self.config.load_threshold_multiplier),
            'cpu_usage': metrics.cpu.avg_usage,
            'memory_usage': metrics.memory.used_percent,
            'iowait_percent': metrics.cpu.iowait_percent,
            'tcp_connections': metrics.network.total_connections,
            'top_cpu_process': metrics.top_processes['by_cpu'][0].name if metrics.top_processes.get('by_cpu') else None,
            'top_memory_process': metrics.top_processes['by_memory'][0].name if metrics.top_processes.get('by_memory') else None
        }
