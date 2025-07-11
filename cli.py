#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command line interface for load analyzer
"""
import sys
import time
import argparse
from pathlib import Path
from typing import List, Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, ConfigManager, OutputFormat
from collector import DataCollector
from analyzer import Analyzer
from reporter import Reporter


class LoadAnalyzerCLI:
    """Command line interface for load analyzer"""
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.collector: Optional[DataCollector] = None
        self.analyzer: Optional[Analyzer] = None
        self.reporter: Optional[Reporter] = None
    
    def setup_parser(self) -> argparse.ArgumentParser:
        """Setup argument parser"""
        parser = argparse.ArgumentParser(
            description='Enhanced Linux system load analyzer',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s                           # Single analysis with default settings
  %(prog)s -n 5 -i 2                # 5 samples with 2 second intervals
  %(prog)s -f json -o report.json   # JSON output to file
  %(prog)s -c config.yaml           # Use custom config file
  %(prog)s --create-config          # Create default config file
            """
        )
        
        # Sampling options
        parser.add_argument(
            '-i', '--interval', 
            type=int, 
            default=1,
            help='Sampling interval in seconds (default: 1)'
        )
        
        parser.add_argument(
            '-n', '--count', 
            type=int, 
            default=1,
            help='Number of samples to collect (default: 1)'
        )
        
        # Output options
        parser.add_argument(
            '-f', '--format',
            choices=['text', 'json', 'csv', 'html', 'markdown'],
            default='text',
            help='Output format (default: text)'
        )
        
        parser.add_argument(
            '-o', '--output',
            help='Output file path (default: stdout)'
        )
        
        parser.add_argument(
            '--no-colors',
            action='store_true',
            help='Disable colored output'
        )
        
        # Configuration
        parser.add_argument(
            '-c', '--config',
            help='Configuration file path'
        )
        
        parser.add_argument(
            '--create-config',
            metavar='FILE',
            help='Create default configuration file and exit'
        )
        
        # Thresholds (override config)
        threshold_group = parser.add_argument_group('threshold overrides')
        threshold_group.add_argument(
            '--load-threshold',
            type=float,
            help='Load threshold multiplier'
        )
        
        threshold_group.add_argument(
            '--cpu-threshold',
            type=float,
            help='CPU usage threshold (%%)'
        )
        
        threshold_group.add_argument(
            '--memory-threshold',
            type=float,
            help='Memory usage threshold (%%)'
        )
        
        threshold_group.add_argument(
            '--iowait-threshold',
            type=float,
            help='I/O wait threshold (%%)'
        )
        
        # Advanced options
        advanced_group = parser.add_argument_group('advanced options')
        advanced_group.add_argument(
            '--top-processes',
            type=int,
            help='Number of top processes to show'
        )
        
        advanced_group.add_argument(
            '--enable-prometheus',
            action='store_true',
            help='Enable Prometheus exporter'
        )
        
        advanced_group.add_argument(
            '--prometheus-port',
            type=int,
            default=8000,
            help='Prometheus exporter port (default: 8000)'
        )
        
        # Monitoring mode
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Continuous monitoring mode (use Ctrl+C to stop)'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Quiet mode - only show issues'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose mode - show additional details'
        )
        
        parser.add_argument(
            '--version',
            action='version',
            version='Load Analyzer 1.0.0'
        )
        
        return parser
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command line arguments"""
        parser = self.setup_parser()
        return parser.parse_args(args)
    
    def load_config(self, args: argparse.Namespace) -> Config:
        """Load and configure settings"""
        # Load base configuration
        config = ConfigManager.load_config(args.config)
        
        # Override with command line arguments
        if args.interval:
            config.sample_interval = args.interval
        
        if args.count:
            config.sample_count = args.count
        
        if args.format:
            config.output_format = OutputFormat(args.format)
        
        if args.output:
            config.output_file = args.output
        
        if args.no_colors:
            config.enable_colors = False
        
        # Threshold overrides
        if args.load_threshold is not None:
            config.load_threshold_multiplier = args.load_threshold
        
        if args.cpu_threshold is not None:
            config.cpu_threshold = args.cpu_threshold
        
        if args.memory_threshold is not None:
            config.memory_threshold = args.memory_threshold
        
        if args.iowait_threshold is not None:
            config.iowait_threshold = args.iowait_threshold
        
        if args.top_processes is not None:
            config.top_processes_count = args.top_processes
        
        if args.enable_prometheus:
            config.enable_prometheus = True
        
        if args.prometheus_port:
            config.prometheus_port = args.prometheus_port
        
        return config
    
    def initialize_components(self, config: Config) -> None:
        """Initialize analyzer components"""
        self.config = config
        self.collector = DataCollector(config)
        self.analyzer = Analyzer(config)
        self.reporter = Reporter(config)
    
    def run_single_analysis(self) -> None:
        """Run single analysis"""
        try:
            # Collect metrics
            metrics = self.collector.collect_all_metrics()
            
            # Analyze
            analysis = self.analyzer.analyze(metrics)
            
            # Generate report
            report = self.reporter.generate_report(metrics, analysis)
            
            # Output report
            if self.config.output_file:
                with open(self.config.output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"Report saved to {self.config.output_file}")
            else:
                print(report)
                
        except Exception as e:
            print(f"Error during analysis: {e}", file=sys.stderr)
            sys.exit(1)
    
    def run_multiple_analysis(self) -> None:
        """Run multiple analyses"""
        try:
            all_samples = []
            
            for i in range(self.config.sample_count):
                if i > 0:
                    time.sleep(self.config.sample_interval)
                
                # Collect metrics
                metrics = self.collector.collect_all_metrics()
                
                # Analyze
                analysis = self.analyzer.analyze(metrics)
                
                all_samples.append({'metrics': metrics, 'analysis': analysis})
                
                # Show progress for text output
                if self.config.output_format == OutputFormat.TEXT and not self.config.output_file:
                    print(f"\n{'='*20} Sample {i+1}/{self.config.sample_count} {'='*20}")
                    report = self.reporter.generate_report(metrics, analysis)
                    print(report)
            
            # Save all samples if output file specified
            if self.config.output_file:
                self._save_multiple_samples(all_samples)
                print(f"All samples saved to {self.config.output_file}")
                
        except KeyboardInterrupt:
            print("\nAnalysis interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"Error during analysis: {e}", file=sys.stderr)
            sys.exit(1)
    
    def run_monitoring_mode(self) -> None:
        """Run continuous monitoring mode"""
        print("Starting continuous monitoring mode (Press Ctrl+C to stop)")
        
        try:
            sample_count = 0
            while True:
                sample_count += 1
                
                # Collect metrics
                metrics = self.collector.collect_all_metrics()
                
                # Analyze
                analysis = self.analyzer.analyze(metrics)
                
                # Show timestamp and basic info
                print(f"\n[{metrics.timestamp}] Sample #{sample_count}")
                print(f"Load: {metrics.load.load1:.2f} | CPU: {metrics.cpu.avg_usage:.1f}% | Memory: {metrics.memory.used_percent:.1f}%")
                
                # Show only issues in monitoring mode
                if analysis.get_critical_issues():
                    print("🚨 CRITICAL ISSUES:")
                    for issue in analysis.get_critical_issues():
                        print(f"  • {issue.message}")
                
                if analysis.get_high_issues():
                    print("⚠️  HIGH ISSUES:")
                    for issue in analysis.get_high_issues():
                        print(f"  • {issue.message}")
                
                if not analysis.get_all_issues():
                    print("✅ No issues detected")
                
                time.sleep(self.config.sample_interval)
                
        except KeyboardInterrupt:
            print(f"\nMonitoring stopped after {sample_count} samples")
            sys.exit(0)
        except Exception as e:
            print(f"Error during monitoring: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _save_multiple_samples(self, samples: List[dict]) -> None:
        """Save multiple samples to file"""
        if self.config.output_format == OutputFormat.JSON:
            import json
            with open(self.config.output_file, 'w', encoding='utf-8') as f:
                json.dump(samples, f, indent=2, default=str)
        else:
            with open(self.config.output_file, 'w', encoding='utf-8') as f:
                for i, sample in enumerate(samples):
                    f.write(f"\n{'='*20} Sample {i+1} {'='*20}\n")
                    report = self.reporter.generate_report(sample['metrics'], sample['analysis'])
                    f.write(report)
                    f.write("\n")
    
    def run(self, args: Optional[List[str]] = None) -> None:
        """Main entry point"""
        # Parse arguments
        parsed_args = self.parse_args(args)
        
        # Handle special commands
        if parsed_args.create_config:
            ConfigManager.create_default_config(parsed_args.create_config)
            return
        
        # Load configuration
        config = self.load_config(parsed_args)
        
        # Initialize components
        self.initialize_components(config)
        
        # Run analysis
        if parsed_args.monitor:
            self.run_monitoring_mode()
        elif config.sample_count == 1:
            self.run_single_analysis()
        else:
            self.run_multiple_analysis()


def main() -> None:
    """Main function for CLI entry point"""
    cli = LoadAnalyzerCLI()
    cli.run()


if __name__ == '__main__':
    main()
