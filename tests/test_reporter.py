#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for reporter module
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from load_analyzer.config import Config, OutputFormat
from load_analyzer.reporter.reporters import (
    Reporter, TextReporter, JsonReporter, CsvReporter, HtmlReporter
)
from load_analyzer.collector.models import (
    MetricsData, LoadMetrics, CPUMetrics, MemoryMetrics, 
    DiskIOMetrics, NetworkMetrics, ProcessInfo
)
from load_analyzer.analyzer.models import (
    AnalysisResult, Issue, IssueType, IssueSeverity, LoadStatus
)


class TestReporter:
    """Test cases for Reporter classes"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = Config()
        
        # Create test metrics
        self.metrics = MetricsData(
            timestamp='2025-07-11T10:30:00.123456',
            load=LoadMetrics(8.5, 6.2, 4.1, 4),
            cpu=CPUMetrics([85.0, 78.0, 92.0, 88.0], 85.75,
                          {'user': 800, 'system': 150, 'idle': 50, 'iowait': 0, 'interrupt': 0}, 
                          0.0, 15000, 2500),
            memory=MemoryMetrics(16.0, 82.5, 2.8, 15.0, 8.0, 1.2, 3.5),
            disk_io=DiskIOMetrics(5000, 2500, 2*1024**3, 1024**3, 5000, 2500, 100*1024**2, 50*1024**2),
            network=NetworkMetrics({'ESTABLISHED': 1200, 'TIME_WAIT': 300}, 1500, 5*1024**3, 10*1024**3, 50000, 100000),
            top_processes={
                'by_cpu': [
                    ProcessInfo(1234, 'high_cpu_proc', 45.2, 12.5, 8, 'high_cpu_proc --worker', 5),
                    ProcessInfo(5678, 'another_proc', 38.7, 8.3, 4, 'another_proc -d', 2)
                ],
                'by_memory': [
                    ProcessInfo(9012, 'memory_hog', 15.1, 55.8, 16, 'memory_hog --cache-size=large', 0),
                    ProcessInfo(3456, 'db_process', 8.2, 35.2, 12, 'db_process --config=/etc/db.conf', 100)
                ],
                'by_io': [
                    ProcessInfo(7890, 'io_intensive', 12.5, 18.7, 6, 'io_intensive --batch-process', 1,
                              {'read_bytes': 500*1024**2, 'write_bytes': 200*1024**2, 'total_bytes': 700*1024**2})
                ]
            }
        )
        
        # Create test analysis
        self.analysis = AnalysisResult(
            timestamp=self.metrics.timestamp,
            load_status=LoadStatus.HIGH
        )
        
        # Add test issues
        self.analysis.primary_issues = [
            Issue(
                type=IssueType.CPU,
                severity=IssueSeverity.HIGH,
                message="High CPU usage: 85.8% (threshold: 80.0%)",
                value=85.8,
                threshold=80.0,
                recommendation="Consider CPU scaling or process optimization",
                related_processes=self.metrics.top_processes['by_cpu'][:2]
            ),
            Issue(
                type=IssueType.LOAD,
                severity=IssueSeverity.HIGH,
                message="High load average: 8.50 (threshold: 6.00)",
                value=8.5,
                threshold=6.0,
                recommendation="Investigate CPU, I/O, or process issues"
            )
        ]
        
        self.analysis.secondary_issues = [
            Issue(
                type=IssueType.MEMORY,
                severity=IssueSeverity.MEDIUM,
                message="High memory usage: 82.5% (threshold: 80.0%)",
                value=82.5,
                threshold=80.0,
                recommendation="Consider memory scaling or optimize memory-intensive processes",
                related_processes=self.metrics.top_processes['by_memory'][:1]
            ),
            Issue(
                type=IssueType.NETWORK,
                severity=IssueSeverity.MEDIUM,
                message="High TCP connections: 1500 (threshold: 1000)",
                value=1500.0,
                threshold=1000.0,
                recommendation="Check for connection leaks or scaling needs"
            )
        ]
        
        self.analysis.recommendations = [
            "Consider CPU scaling or process optimization",
            "Investigate CPU, I/O, or process issues",
            "Consider memory scaling or optimize memory-intensive processes",
            "Check for connection leaks or scaling needs"
        ]
        
        self.analysis.summary = {
            'total_issues': 4,
            'critical_issues': 0,
            'high_issues': 2,
            'load_ratio': 1.42,
            'cpu_usage': 85.75,
            'memory_usage': 82.5,
            'iowait_percent': 0.0,
            'tcp_connections': 1500,
            'top_cpu_process': 'high_cpu_proc',
            'top_memory_process': 'memory_hog'
        }
    
    def test_reporter_factory_text(self):
        """Test reporter factory for text format"""
        config = Config()
        config.output_format = OutputFormat.TEXT
        reporter = Reporter(config)
        assert isinstance(reporter._reporter, TextReporter)
    
    def test_reporter_factory_json(self):
        """Test reporter factory for JSON format"""
        config = Config()
        config.output_format = OutputFormat.JSON
        reporter = Reporter(config)
        assert isinstance(reporter._reporter, JsonReporter)
    
    def test_reporter_factory_csv(self):
        """Test reporter factory for CSV format"""
        config = Config()
        config.output_format = OutputFormat.CSV
        reporter = Reporter(config)
        assert isinstance(reporter._reporter, CsvReporter)
    
    def test_reporter_factory_html(self):
        """Test reporter factory for HTML format"""
        config = Config()
        config.output_format = OutputFormat.HTML
        reporter = Reporter(config)
        assert isinstance(reporter._reporter, HtmlReporter)
    
    def test_text_reporter_generate_report(self):
        """Test text reporter report generation"""
        reporter = TextReporter(self.config)
        report = reporter.generate_report(self.metrics, self.analysis)
        
        assert isinstance(report, str)
        assert "SYSTEM LOAD ANALYSIS REPORT" in report
        assert "Load Status: HIGH" in report
        assert "HIGH PRIORITY ISSUES" in report
        assert "High CPU usage: 85.8%" in report
        assert "High load average: 8.50" in report
        assert "high_cpu_proc" in report
        assert "RECOMMENDATIONS" in report
        assert "Consider CPU scaling" in report
    
    def test_text_reporter_colorize(self):
        """Test text reporter colorization"""
        # Test with colors enabled
        config = Config()
        config.enable_colors = True
        reporter = TextReporter(config)
        
        colored_text = reporter.colorize("test", "red")
        assert "\033[91m" in colored_text  # Red color code
        assert "\033[0m" in colored_text   # Reset code
        
        # Test with colors disabled
        config.enable_colors = False
        reporter = TextReporter(config)
        
        uncolored_text = reporter.colorize("test", "red")
        assert uncolored_text == "test"
        assert "\033[" not in uncolored_text
    
    def test_json_reporter_generate_report(self):
        """Test JSON reporter report generation"""
        reporter = JsonReporter(self.config)
        report = reporter.generate_report(self.metrics, self.analysis)
        
        assert isinstance(report, str)
        
        # Parse JSON to validate structure
        data = json.loads(report)
        assert 'metrics' in data
        assert 'analysis' in data
        
        assert data['metrics']['timestamp'] == self.metrics.timestamp
        assert data['metrics']['load']['load1'] == 8.5
        assert data['metrics']['cpu']['avg_usage'] == 85.75
        
        assert data['analysis']['load_status'] == 'high'
        assert len(data['analysis']['primary_issues']) == 2
        assert len(data['analysis']['secondary_issues']) == 2
    
    def test_csv_reporter_generate_report(self):
        """Test CSV reporter report generation"""
        reporter = CsvReporter(self.config)
        report = reporter.generate_report(self.metrics, self.analysis)
        
        assert isinstance(report, str)
        
        lines = report.strip().split('\n')
        assert len(lines) == 2  # Header + data row
        
        header = lines[0]
        data_row = lines[1]
        
        assert 'timestamp' in header
        assert 'load_status' in header
        assert 'cpu_avg' in header
        assert 'memory_percent' in header
        
        assert '2025-07-11T10:30:00.123456' in data_row
        assert 'high' in data_row
        assert '85.75' in data_row
        assert '82.5' in data_row
    
    def test_html_reporter_generate_report(self):
        """Test HTML reporter report generation"""
        reporter = HtmlReporter(self.config)
        report = reporter.generate_report(self.metrics, self.analysis)
        
        assert isinstance(report, str)
        assert "<!DOCTYPE html>" in report
        assert "<title>System Load Analysis Report</title>" in report
        assert "Load Status:" in report
        assert "HIGH" in report
        assert "high_cpu_proc" in report
        assert "<table>" in report
        assert "Recommendations" in report
    
    def test_text_reporter_format_bytes(self):
        """Test byte formatting in text reporter"""
        reporter = TextReporter(self.config)
        
        assert reporter._format_bytes(512) == "512.0 B"
        assert reporter._format_bytes(1536) == "1.5 KB"
        assert reporter._format_bytes(1048576) == "1.0 MB"
        assert reporter._format_bytes(1073741824) == "1.0 GB"
        assert reporter._format_bytes(1099511627776) == "1.0 TB"
    
    def test_text_reporter_get_threshold_color(self):
        """Test threshold color determination"""
        config = Config()
        config.enable_colors = True
        reporter = TextReporter(config)
        
        # Value below threshold should be green
        assert reporter._get_threshold_color(70.0, 80.0) == 'green'
        
        # Value above threshold but below 1.2x should be yellow
        assert reporter._get_threshold_color(85.0, 80.0) == 'yellow'
        
        # Value above 1.2x threshold should be red
        assert reporter._get_threshold_color(100.0, 80.0) == 'red'
    
    def test_text_reporter_get_status_color(self):
        """Test status color determination"""
        config = Config()
        config.enable_colors = True
        reporter = TextReporter(config)
        
        assert reporter._get_status_color('normal') == 'green'
        assert reporter._get_status_color('elevated') == 'yellow'
        assert reporter._get_status_color('high') == 'yellow'
        assert reporter._get_status_color('critical') == 'red'
        assert reporter._get_status_color('unknown') == 'white'
    
    def test_reporter_save_report(self):
        """Test saving report to file"""
        import tempfile
        import os
        
        reporter = Reporter(self.config)
        report_content = "Test report content"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Save report
            reporter.save_report(report_content, temp_filename)
            
            # Read back and verify
            with open(temp_filename, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert saved_content == report_content
            
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


if __name__ == '__main__':
    # Simple test runner
    import unittest
    
    class TestReporterUnittest(unittest.TestCase, TestReporter):
        pass
    
    unittest.main()
