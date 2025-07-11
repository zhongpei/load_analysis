#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base reporter interface and factory
"""
import json
import csv
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, OutputFormat
from collector.models import MetricsData
from analyzer.models import AnalysisResult


class BaseReporter(ABC):
    """Base class for all reporters"""
    
    def __init__(self, config: Config):
        self.config = config
    
    @abstractmethod
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate report string"""
        pass


class Reporter:
    """Reporter factory and manager"""
    
    def __init__(self, config: Config):
        self.config = config
        self._reporter = self._create_reporter()
    
    def _create_reporter(self) -> BaseReporter:
        """Create appropriate reporter based on config"""
        if self.config.output_format == OutputFormat.JSON:
            return JsonReporter(self.config)
        elif self.config.output_format == OutputFormat.CSV:
            return CsvReporter(self.config)
        elif self.config.output_format == OutputFormat.HTML:
            return HtmlReporter(self.config)
        elif self.config.output_format == OutputFormat.MARKDOWN:
            return MarkdownReporter(self.config)
        else:
            return TextReporter(self.config)
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate report using configured reporter"""
        return self._reporter.generate_report(metrics, analysis)
    
    def save_report(self, report: str, filename: str) -> None:
        """Save report to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)


class TextReporter(BaseReporter):
    """Text format reporter with ANSI colors"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.colors = {
            'red': '\033[91m',
            'yellow': '\033[93m', 
            'green': '\033[92m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'bold': '\033[1m',
            'end': '\033[0m'
        } if config.enable_colors else {key: '' for key in ['red', 'yellow', 'green', 'blue', 'magenta', 'cyan', 'white', 'bold', 'end']}
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text"""
        return f"{self.colors.get(color, '')}{text}{self.colors.get('end', '')}"
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate text report"""
        lines = []
        
        # Header
        lines.append(self.colorize("=" * 60, "blue"))
        lines.append(self.colorize("         SYSTEM LOAD ANALYSIS REPORT", "bold"))
        lines.append(self.colorize("=" * 60, "blue"))
        lines.append(f"Timestamp: {metrics.timestamp}")
        lines.append("")
        
        # Status overview
        status_color = self._get_status_color(analysis.load_status.value)
        lines.append(self.colorize(f"Load Status: {analysis.load_status.value.upper()}", status_color))
        lines.append("")
        
        # System overview
        lines.append(self.colorize("SYSTEM OVERVIEW", "bold"))
        lines.append(f"  CPU Cores: {metrics.load.cpu_count}")
        lines.append(f"  Load Averages: {metrics.load.load1:.2f} / {metrics.load.load5:.2f} / {metrics.load.load15:.2f}")
        lines.append(f"  CPU Usage: {self.colorize(f'{metrics.cpu.avg_usage:.1f}%', self._get_threshold_color(metrics.cpu.avg_usage, self.config.cpu_threshold))}")
        lines.append(f"  Memory Usage: {self.colorize(f'{metrics.memory.used_percent:.1f}%', self._get_threshold_color(metrics.memory.used_percent, self.config.memory_threshold))}")
        lines.append(f"  I/O Wait: {self.colorize(f'{metrics.cpu.iowait_percent:.1f}%', self._get_threshold_color(metrics.cpu.iowait_percent, self.config.iowait_threshold))}")
        lines.append("")
        
        # Critical and High Issues
        if analysis.get_critical_issues():
            lines.append(self.colorize("🚨 CRITICAL ISSUES", "red"))
            for issue in analysis.get_critical_issues():
                lines.append(f"  • {self.colorize(issue.message, 'red')}")
                if issue.related_processes:
                    lines.append(f"    Top processes: {', '.join([f'{p.name}({p.pid})' for p in issue.related_processes[:3]])}")
            lines.append("")
        
        if analysis.get_high_issues():
            lines.append(self.colorize("⚠️  HIGH PRIORITY ISSUES", "yellow"))
            for issue in analysis.get_high_issues():
                lines.append(f"  • {self.colorize(issue.message, 'yellow')}")
                if issue.related_processes:
                    lines.append(f"    Top processes: {', '.join([f'{p.name}({p.pid})' for p in issue.related_processes[:3]])}")
            lines.append("")
        
        # All other issues
        other_issues = [i for i in analysis.get_all_issues() 
                       if i.severity.value not in ['critical', 'high']]
        if other_issues:
            lines.append(self.colorize("📋 OTHER ISSUES", "cyan"))
            for issue in other_issues:
                lines.append(f"  • {issue.message}")
            lines.append("")
        
        # CPU Details
        lines.append(self.colorize("CPU ANALYSIS", "blue"))
        lines.append(f"  Average Usage: {metrics.cpu.avg_usage:.1f}%")
        lines.append(f"  I/O Wait: {metrics.cpu.iowait_percent:.1f}%")
        lines.append(f"  Context Switches: {metrics.cpu.context_switches:,}")
        lines.append(f"  Interrupts: {metrics.cpu.interrupts:,}")
        lines.append("  Per-Core Usage:")
        for idx, usage in enumerate(metrics.cpu.usage_per_core):
            color = self._get_threshold_color(usage, self.config.cpu_threshold)
            lines.append(f"    Core {idx:2d}: {self.colorize(f'{usage:5.1f}%', color)}")
        lines.append("")
        
        # Memory Details
        lines.append(self.colorize("MEMORY ANALYSIS", "blue"))
        lines.append(f"  Total: {metrics.memory.total_gb:.2f} GB")
        lines.append(f"  Used: {self.colorize(f'{metrics.memory.used_percent:.1f}%', self._get_threshold_color(metrics.memory.used_percent, self.config.memory_threshold))}")
        lines.append(f"  Available: {metrics.memory.available_gb:.2f} GB")
        lines.append(f"  Buffers: {metrics.memory.buffers_gb:.2f} GB")
        lines.append(f"  Cached: {metrics.memory.cached_gb:.2f} GB")
        lines.append(f"  Swap: {self.colorize(f'{metrics.memory.swap_percent:.1f}%', self._get_threshold_color(metrics.memory.swap_percent, self.config.swap_threshold))} of {metrics.memory.swap_total_gb:.2f} GB")
        lines.append("")
        
        # Disk I/O
        lines.append(self.colorize("DISK I/O ANALYSIS", "blue"))
        lines.append(f"  Read: {metrics.disk_io.read_count:,} ops, {self._format_bytes(metrics.disk_io.read_bytes)}")
        lines.append(f"  Write: {metrics.disk_io.write_count:,} ops, {self._format_bytes(metrics.disk_io.write_bytes)}")
        if metrics.disk_io.read_rate:
            lines.append(f"  Read Rate: {self._format_bytes(metrics.disk_io.read_rate)}/s")
        if metrics.disk_io.write_rate:
            lines.append(f"  Write Rate: {self._format_bytes(metrics.disk_io.write_rate)}/s")
        lines.append("")
        
        # Network
        lines.append(self.colorize("NETWORK ANALYSIS", "blue"))
        lines.append(f"  Total Connections: {self.colorize(str(metrics.network.total_connections), self._get_threshold_color(metrics.network.total_connections, self.config.tcp_connections_threshold))}")
        lines.append(f"  Bytes Sent: {self._format_bytes(metrics.network.bytes_sent)}")
        lines.append(f"  Bytes Received: {self._format_bytes(metrics.network.bytes_recv)}")
        
        if isinstance(metrics.network.tcp_connections, dict):
            lines.append("  TCP Connection States:")
            for state, count in sorted(metrics.network.tcp_connections.items()):
                lines.append(f"    {state}: {count}")
        lines.append("")
        
        # Top Processes
        lines.append(self.colorize("TOP PROCESSES", "blue"))
        
        # Top CPU processes
        lines.append(self.colorize("  By CPU Usage:", "cyan"))
        for proc in metrics.top_processes.get('by_cpu', [])[:5]:
            lines.append(f"    PID {proc.pid:5d} - {proc.name:15s}: CPU {proc.cpu_percent:5.1f}%, MEM {proc.memory_percent:5.1f}%")
            lines.append(f"      Command: {proc.cmdline[:60]}{'...' if len(proc.cmdline) > 60 else ''}")
        
        lines.append(self.colorize("  By Memory Usage:", "cyan"))
        for proc in metrics.top_processes.get('by_memory', [])[:5]:
            lines.append(f"    PID {proc.pid:5d} - {proc.name:15s}: CPU {proc.cpu_percent:5.1f}%, MEM {proc.memory_percent:5.1f}%")
            lines.append(f"      Command: {proc.cmdline[:60]}{'...' if len(proc.cmdline) > 60 else ''}")
        
        if metrics.top_processes.get('by_io'):
            lines.append(self.colorize("  By I/O Activity:", "cyan"))
            for proc in metrics.top_processes.get('by_io', [])[:5]:
                io_info = proc.io_counters
                if io_info:
                    total_io = self._format_bytes(io_info.get('total_bytes', 0))
                    lines.append(f"    PID {proc.pid:5d} - {proc.name:15s}: Total I/O {total_io}")
        
        lines.append("")
        
        # Recommendations
        if analysis.recommendations:
            lines.append(self.colorize("RECOMMENDATIONS", "green"))
            for i, rec in enumerate(analysis.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")
        
        # Summary
        lines.append(self.colorize("SUMMARY", "bold"))
        lines.append(f"  Total Issues: {analysis.summary.get('total_issues', 0)}")
        lines.append(f"  Critical Issues: {analysis.summary.get('critical_issues', 0)}")
        lines.append(f"  High Issues: {analysis.summary.get('high_issues', 0)}")
        lines.append(f"  Load Ratio: {analysis.summary.get('load_ratio', 0):.2f}")
        
        return "\n".join(lines)
    
    def _get_status_color(self, status: str) -> str:
        """Get color for load status"""
        status_colors = {
            'normal': 'green',
            'elevated': 'yellow',
            'high': 'yellow',
            'critical': 'red'
        }
        return status_colors.get(status.lower(), 'white')
    
    def _get_threshold_color(self, value: float, threshold: float) -> str:
        """Get color based on threshold"""
        if value > threshold * 1.2:
            return 'red'
        elif value > threshold:
            return 'yellow'
        else:
            return 'green'
    
    def _format_bytes(self, bytes_value: float) -> str:
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"


class JsonReporter(BaseReporter):
    """JSON format reporter"""
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate JSON report"""
        report_data = {
            'metrics': metrics.to_dict(),
            'analysis': analysis.to_dict()
        }
        return json.dumps(report_data, indent=2, ensure_ascii=False)


class CsvReporter(BaseReporter):
    """CSV format reporter"""
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate CSV report"""
        import io
        output = io.StringIO()
        
        # Write header
        fieldnames = [
            'timestamp', 'load_status', 'load1', 'load5', 'load15', 'cpu_avg',
            'memory_percent', 'swap_percent', 'iowait_percent', 'tcp_connections',
            'total_issues', 'critical_issues', 'high_issues',
            'top_cpu_process', 'top_memory_process'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write data row
        row = {
            'timestamp': metrics.timestamp,
            'load_status': analysis.load_status.value,
            'load1': metrics.load.load1,
            'load5': metrics.load.load5,
            'load15': metrics.load.load15,
            'cpu_avg': metrics.cpu.avg_usage,
            'memory_percent': metrics.memory.used_percent,
            'swap_percent': metrics.memory.swap_percent,
            'iowait_percent': metrics.cpu.iowait_percent,
            'tcp_connections': metrics.network.total_connections,
            'total_issues': analysis.summary.get('total_issues', 0),
            'critical_issues': analysis.summary.get('critical_issues', 0),
            'high_issues': analysis.summary.get('high_issues', 0),
            'top_cpu_process': analysis.summary.get('top_cpu_process', ''),
            'top_memory_process': analysis.summary.get('top_memory_process', '')
        }
        
        writer.writerow(row)
        return output.getvalue()


class HtmlReporter(BaseReporter):
    """HTML format reporter"""
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate HTML report"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>System Load Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; }}
        .status-normal {{ color: #27ae60; }}
        .status-elevated {{ color: #f39c12; }}
        .status-high {{ color: #e67e22; }}
        .status-critical {{ color: #e74c3c; }}
        .issue-critical {{ background-color: #ffebee; border-left: 4px solid #e74c3c; padding: 10px; }}
        .issue-high {{ background-color: #fff8e1; border-left: 4px solid #ff9800; padding: 10px; }}
        .issue-medium {{ background-color: #f3e5f5; border-left: 4px solid #9c27b0; padding: 10px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1 class="header">System Load Analysis Report</h1>
    <p><strong>Timestamp:</strong> {metrics.timestamp}</p>
    <p><strong>Load Status:</strong> <span class="status-{analysis.load_status.value}">{analysis.load_status.value.upper()}</span></p>
    
    <h2>System Overview</h2>
    <div class="metric">
        <strong>CPU Cores:</strong> {metrics.load.cpu_count}
    </div>
    <div class="metric">
        <strong>Load Averages:</strong> {metrics.load.load1:.2f} / {metrics.load.load5:.2f} / {metrics.load.load15:.2f}
    </div>
    <div class="metric">
        <strong>CPU Usage:</strong> {metrics.cpu.avg_usage:.1f}%
    </div>
    <div class="metric">
        <strong>Memory Usage:</strong> {metrics.memory.used_percent:.1f}%
    </div>
    <div class="metric">
        <strong>I/O Wait:</strong> {metrics.cpu.iowait_percent:.1f}%
    </div>
    
    <h2>Issues</h2>
"""
        
        # Add issues
        for issue in analysis.get_all_issues():
            severity_class = f"issue-{issue.severity.value}"
            html += f'<div class="{severity_class}"><strong>{issue.severity.value.upper()}:</strong> {issue.message}</div>\n'
        
        # Add top processes table
        html += """
    <h2>Top Processes by CPU</h2>
    <table>
        <tr><th>PID</th><th>Name</th><th>CPU %</th><th>Memory %</th><th>Command</th></tr>
"""
        
        for proc in metrics.top_processes.get('by_cpu', [])[:10]:
            html += f"<tr><td>{proc.pid}</td><td>{proc.name}</td><td>{proc.cpu_percent:.1f}%</td><td>{proc.memory_percent:.1f}%</td><td>{proc.cmdline[:50]}...</td></tr>\n"
        
        html += """
    </table>
    
    <h2>Recommendations</h2>
    <ul>
"""
        
        for rec in analysis.recommendations:
            html += f"<li>{rec}</li>\n"
        
        html += """
    </ul>
</body>
</html>
"""
        return html


class MarkdownReporter(BaseReporter):
    """Markdown format reporter"""
    
    def generate_report(self, metrics: MetricsData, analysis: AnalysisResult) -> str:
        """Generate Markdown report"""
        md = f"""# System Load Analysis Report

**Timestamp:** {metrics.timestamp}  
**Load Status:** {analysis.load_status.value.upper()}

## System Overview

| Metric | Value |
|--------|-------|
| CPU Cores | {metrics.load.cpu_count} |
| Load Averages | {metrics.load.load1:.2f} / {metrics.load.load5:.2f} / {metrics.load.load15:.2f} |
| CPU Usage | {metrics.cpu.avg_usage:.1f}% |
| Memory Usage | {metrics.memory.used_percent:.1f}% |
| I/O Wait | {metrics.cpu.iowait_percent:.1f}% |

## Issues

"""
        
        # Add issues
        if analysis.get_critical_issues():
            md += "### 🚨 Critical Issues\n\n"
            for issue in analysis.get_critical_issues():
                md += f"- **{issue.message}**\n"
        
        if analysis.get_high_issues():
            md += "### ⚠️ High Priority Issues\n\n"
            for issue in analysis.get_high_issues():
                md += f"- **{issue.message}**\n"
        
        other_issues = [i for i in analysis.get_all_issues() if i.severity.value not in ['critical', 'high']]
        if other_issues:
            md += "### Other Issues\n\n"
            for issue in other_issues:
                md += f"- {issue.message}\n"
        
        # Add top processes
        md += "\n## Top Processes by CPU\n\n"
        md += "| PID | Name | CPU % | Memory % | Command |\n"
        md += "|-----|------|-------|----------|----------|\n"
        
        for proc in metrics.top_processes.get('by_cpu', [])[:10]:
            cmd = proc.cmdline[:50] + "..." if len(proc.cmdline) > 50 else proc.cmdline
            md += f"| {proc.pid} | {proc.name} | {proc.cpu_percent:.1f}% | {proc.memory_percent:.1f}% | {cmd} |\n"
        
        # Add recommendations
        if analysis.recommendations:
            md += "\n## Recommendations\n\n"
            for i, rec in enumerate(analysis.recommendations, 1):
                md += f"{i}. {rec}\n"
        
        return md
