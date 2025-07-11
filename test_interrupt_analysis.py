#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test interrupt analysis functionality
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, ConfigManager, OutputFormat
from collector import DataCollector
from analyzer import Analyzer
from reporter import Reporter


def test_interrupt_analysis():
    """测试中断分析功能"""
    print("Testing interrupt analysis functionality...")
    
    # 1. 创建配置
    config = Config(
        enable_interrupt_analysis=True,
        enable_colors=True,
        output_format=OutputFormat.TEXT
    )
    
    # 2. 创建数据收集器并收集指标
    collector = DataCollector(config)
    print("Collecting system metrics...")
    metrics = collector.collect_all_metrics()
    
    # 3. 创建分析器并分析数据
    analyzer = Analyzer(config)
    print("Analyzing system metrics...")
    analysis = analyzer.analyze(metrics)
    
    # 4. 创建报告器并生成报告
    reporter = Reporter(config)
    print("Generating report...")
    report = reporter.generate_report(metrics, analysis)
    
    print("\n" + "="*60)
    print("INTERRUPT ANALYSIS TEST RESULTS")
    print("="*60)
    print(report)
    
    # 5. 验证中断数据是否被收集
    if metrics.interrupts:
        print("\n" + "="*40)
        print("INTERRUPT DATA SUMMARY")
        print("="*40)
        print(f"Total Interrupts: {metrics.interrupts.total_interrupts:,}")
        print(f"Context Switches: {metrics.interrupts.system_context_switches:,}")
        print(f"Network Interrupts: {len(metrics.interrupts.network_interrupts)}")
        print(f"ksoftirqd Processes: {len(metrics.interrupts.ksoftirqd_processes)}")
        print(f"High Switch Processes: {len(metrics.interrupts.high_switch_processes)}")
        
        if metrics.interrupts.interrupt_rate:
            print(f"Interrupt Rate: {metrics.interrupts.interrupt_rate:.0f}/sec")
        if metrics.interrupts.context_switch_rate:
            print(f"Context Switch Rate: {metrics.interrupts.context_switch_rate:.0f}/sec")
    else:
        print("\nWarning: No interrupt data collected!")
    
    print("\n" + "="*40)
    print("ANALYSIS SUMMARY")
    print("="*40)
    print(f"Total Issues: {len(analysis.get_all_issues())}")
    print(f"Critical Issues: {len(analysis.get_critical_issues())}")
    print(f"High Issues: {len(analysis.get_high_issues())}")
    print(f"Recommendations: {len(analysis.recommendations)}")
    
    if analysis.recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(analysis.recommendations[:5], 1):
            print(f"  {i}. {rec}")


if __name__ == "__main__":
    try:
        test_interrupt_analysis()
        print("\n✅ Interrupt analysis test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
