#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for analyzer module
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from load_analyzer.config import Config
from load_analyzer.analyzer.analyzer import Analyzer
from load_analyzer.analyzer.models import AnalysisResult, Issue, IssueType, IssueSeverity, LoadStatus
from load_analyzer.collector.models import (
    MetricsData, LoadMetrics, CPUMetrics, MemoryMetrics, 
    DiskIOMetrics, NetworkMetrics, ProcessInfo
)


class TestAnalyzer:
    """Test cases for Analyzer"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = Config()
        self.analyzer = Analyzer(self.config)
    
    def create_test_metrics(self, **kwargs) -> MetricsData:
        """Create test metrics with defaults"""
        defaults = {
            'timestamp': '2025-07-11T10:30:00.123456',
            'load': LoadMetrics(1.0, 1.5, 2.0, 4),
            'cpu': CPUMetrics([10.0, 20.0, 30.0, 40.0], 25.0, 
                             {'user': 100, 'system': 50, 'idle': 800, 'iowait': 50, 'interrupt': 10}, 
                             5.0, 1000, 500),
            'memory': MemoryMetrics(8.0, 50.0, 4.0, 10.0, 2.0, 0.5, 1.0),
            'disk_io': DiskIOMetrics(1000, 500, 1024**3, 512*1024**2, 1000, 500),
            'network': NetworkMetrics({'ESTABLISHED': 100}, 100, 1024**2, 2*1024**2, 1000, 2000),
            'top_processes': {
                'by_cpu': [ProcessInfo(1234, 'test_proc', 50.0, 25.0, 4, 'test_proc --arg', 0)],
                'by_memory': [ProcessInfo(5678, 'mem_proc', 10.0, 80.0, 2, 'mem_proc', 0)],
                'by_io': []
            }
        }
        defaults.update(kwargs)
        return MetricsData(**defaults)
    
    def test_determine_load_status_normal(self):
        """Test normal load status determination"""
        metrics = self.create_test_metrics()
        status = self.analyzer._determine_load_status(metrics)
        assert status == LoadStatus.NORMAL
    
    def test_determine_load_status_high(self):
        """Test high load status determination"""
        # Load threshold = 4 * 1.5 = 6.0, so load1 = 10.0 should be high
        metrics = self.create_test_metrics(
            load=LoadMetrics(10.0, 8.0, 6.0, 4)
        )
        status = self.analyzer._determine_load_status(metrics)
        assert status == LoadStatus.HIGH
    
    def test_determine_load_status_critical(self):
        """Test critical load status determination"""
        # Load threshold = 4 * 1.5 = 6.0, so load1 = 15.0 should be critical
        metrics = self.create_test_metrics(
            load=LoadMetrics(15.0, 12.0, 10.0, 4)
        )
        status = self.analyzer._determine_load_status(metrics)
        assert status == LoadStatus.CRITICAL
    
    def test_analyze_load_high(self):
        """Test load analysis with high load"""
        metrics = self.create_test_metrics(
            load=LoadMetrics(10.0, 8.0, 6.0, 4)  # High load
        )
        result = AnalysisResult(timestamp=metrics.timestamp, load_status=LoadStatus.HIGH)
        
        self.analyzer._analyze_load(metrics, result)
        
        assert len(result.primary_issues) > 0
        load_issue = next((issue for issue in result.primary_issues if issue.type == IssueType.LOAD), None)
        assert load_issue is not None
        assert load_issue.severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]
    
    def test_analyze_cpu_high(self):
        """Test CPU analysis with high usage"""
        metrics = self.create_test_metrics(
            cpu=CPUMetrics([90.0, 85.0, 95.0, 88.0], 89.5,  # High CPU usage
                          {'user': 800, 'system': 100, 'idle': 100, 'iowait': 0, 'interrupt': 0}, 
                          0.0, 1000, 500)
        )
        result = AnalysisResult(timestamp=metrics.timestamp, load_status=LoadStatus.NORMAL)
        
        self.analyzer._analyze_cpu(metrics, result)
        
        cpu_issues = [issue for issue in result.get_all_issues() if issue.type == IssueType.CPU]
        assert len(cpu_issues) > 0
        assert cpu_issues[0].severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]
    
    def test_analyze_cpu_high_iowait(self):
        """Test CPU analysis with high I/O wait"""
        metrics = self.create_test_metrics(
            cpu=CPUMetrics([10.0, 15.0, 20.0, 25.0], 17.5,
                          {'user': 100, 'system': 50, 'idle': 400, 'iowait': 450, 'interrupt': 0}, 
                          45.0, 1000, 500)  # High iowait
        )
        result = AnalysisResult(timestamp=metrics.timestamp, load_status=LoadStatus.NORMAL)
        
        self.analyzer._analyze_cpu(metrics, result)
        
        iowait_issues = [issue for issue in result.get_all_issues() if issue.type == IssueType.IOWAIT]
        assert len(iowait_issues) > 0
        assert iowait_issues[0].severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]
    
    def test_analyze_memory_high(self):
        """Test memory analysis with high usage"""
        metrics = self.create_test_metrics(
            memory=MemoryMetrics(8.0, 90.0, 0.8, 10.0, 2.0, 0.5, 1.0)  # High memory usage
        )
        result = AnalysisResult(timestamp=metrics.timestamp, load_status=LoadStatus.NORMAL)
        
        self.analyzer._analyze_memory(metrics, result)
        
        memory_issues = [issue for issue in result.get_all_issues() if issue.type == IssueType.MEMORY]
        assert len(memory_issues) > 0
    
    def test_analyze_network_high_connections(self):
        """Test network analysis with high connections"""
        metrics = self.create_test_metrics(
            network=NetworkMetrics({'ESTABLISHED': 1500}, 1500, 1024**3, 2*1024**3, 10000, 20000)  # High connections
        )
        result = AnalysisResult(timestamp=metrics.timestamp, load_status=LoadStatus.NORMAL)
        
        self.analyzer._analyze_network(metrics, result)
        
        network_issues = [issue for issue in result.get_all_issues() if issue.type == IssueType.NETWORK]
        assert len(network_issues) > 0
    
    def test_analyze_complete(self):
        """Test complete analysis"""
        metrics = self.create_test_metrics(
            load=LoadMetrics(10.0, 8.0, 6.0, 4),  # High load
            cpu=CPUMetrics([90.0, 85.0, 95.0, 88.0], 89.5,  # High CPU
                          {'user': 800, 'system': 100, 'idle': 100, 'iowait': 0, 'interrupt': 0}, 
                          0.0, 1000, 500),
            memory=MemoryMetrics(8.0, 90.0, 0.8, 10.0, 2.0, 0.5, 1.0)  # High memory
        )
        
        result = self.analyzer.analyze(metrics)
        
        assert isinstance(result, AnalysisResult)
        assert result.load_status == LoadStatus.HIGH
        assert len(result.get_all_issues()) > 0
        assert len(result.recommendations) > 0
        assert result.summary['total_issues'] > 0
        assert result.summary['load_ratio'] > 1.0
    
    def test_get_severity_by_ratio(self):
        """Test severity calculation by ratio"""
        # Test different severity levels
        assert self.analyzer._get_severity_by_ratio(50, 40, 1.5, 2.0) == IssueSeverity.MEDIUM
        assert self.analyzer._get_severity_by_ratio(70, 40, 1.5, 2.0) == IssueSeverity.HIGH
        assert self.analyzer._get_severity_by_ratio(90, 40, 1.5, 2.0) == IssueSeverity.CRITICAL
        assert self.analyzer._get_severity_by_ratio(30, 40, 1.5, 2.0) == IssueSeverity.LOW
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        result = AnalysisResult(
            timestamp='2025-07-11T10:30:00.123456',
            load_status=LoadStatus.HIGH
        )
        
        # Add some test issues
        result.primary_issues.append(
            Issue(IssueType.CPU, IssueSeverity.HIGH, "High CPU", 90.0, 80.0, "Scale CPU")
        )
        result.secondary_issues.append(
            Issue(IssueType.MEMORY, IssueSeverity.MEDIUM, "High Memory", 85.0, 80.0, "Add memory")
        )
        
        self.analyzer._generate_recommendations(result)
        
        assert len(result.recommendations) > 0
        assert "Scale CPU" in result.recommendations
        assert "Add memory" in result.recommendations
    
    def test_create_summary(self):
        """Test summary creation"""
        metrics = self.create_test_metrics()
        result = AnalysisResult(
            timestamp=metrics.timestamp,
            load_status=LoadStatus.NORMAL
        )
        
        # Add some test issues
        result.primary_issues.append(
            Issue(IssueType.CPU, IssueSeverity.HIGH, "High CPU", 90.0, 80.0, "Scale CPU")
        )
        result.secondary_issues.append(
            Issue(IssueType.MEMORY, IssueSeverity.MEDIUM, "High Memory", 85.0, 80.0, "Add memory")
        )
        
        self.analyzer._create_summary(metrics, result)
        
        assert 'total_issues' in result.summary
        assert 'critical_issues' in result.summary
        assert 'high_issues' in result.summary
        assert 'load_ratio' in result.summary
        assert 'cpu_usage' in result.summary
        assert 'memory_usage' in result.summary
        
        assert result.summary['total_issues'] == 2
        assert result.summary['high_issues'] == 1
        assert result.summary['cpu_usage'] == 25.0
        assert result.summary['memory_usage'] == 50.0


if __name__ == '__main__':
    # Simple test runner
    import unittest
    
    class TestAnalyzerUnittest(unittest.TestCase, TestAnalyzer):
        pass
    
    unittest.main()
