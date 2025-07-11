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
        
        # Analyze interrupts and context switches if available
        if metrics.interrupts and self.config.enable_interrupt_analysis:
            self._analyze_interrupts(metrics, result)
        
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
    
    def _analyze_interrupts(self, metrics: MetricsData, result: AnalysisResult) -> None:
        """分析中断和上下文切换"""
        if not metrics.interrupts:
            return
            
        interrupts = metrics.interrupts
        
        # 1. 分析硬中断负载
        if interrupts.interrupt_rate and interrupts.interrupt_rate > self.config.max_interrupt_rate:
            result.add_issue(Issue(
                type=IssueType.CPU,
                severity=IssueSeverity.HIGH,
                message=f"高中断率: {interrupts.interrupt_rate:.0f} 中断/秒 (阈值: {self.config.max_interrupt_rate})",
                value=interrupts.interrupt_rate,
                threshold=self.config.max_interrupt_rate,
                recommendation="考虑优化中断处理或使用中断合并技术",
                additional_data={
                    "total_interrupts": interrupts.total_interrupts,
                    "hottest_cpu": interrupts.hottest_cpu,
                    "cpu_distribution": interrupts.cpu_interrupt_distribution
                }
            ))
        
        # 2. 分析CPU中断分布不均
        if interrupts.cpu_interrupt_distribution:
            cpu_avg = sum(interrupts.cpu_interrupt_distribution) / len(interrupts.cpu_interrupt_distribution)
            max_cpu_interrupts = max(interrupts.cpu_interrupt_distribution)
            if cpu_avg > 0 and max_cpu_interrupts > cpu_avg * 3:  # 某个CPU的中断数是平均值的3倍以上
                result.add_issue(Issue(
                    type=IssueType.CPU,
                    severity=IssueSeverity.MEDIUM,
                    message=f"CPU{interrupts.hottest_cpu} 中断负载过高: {max_cpu_interrupts} 中断 (平均: {cpu_avg:.0f})",
                    value=max_cpu_interrupts,
                    threshold=cpu_avg * 2,
                    recommendation="建议使用irqbalance或手动调整中断亲和性",
                    additional_data={
                        "hottest_cpu": interrupts.hottest_cpu,
                        "imbalance_ratio": max_cpu_interrupts / cpu_avg if cpu_avg > 0 else 0
                    }
                ))
        
        # 3. 分析网卡中断热点
        for net_int in interrupts.network_interrupts:
            if net_int.rate and net_int.rate > self.config.network_interrupt_threshold:
                result.add_issue(Issue(
                    type=IssueType.NETWORK,
                    severity=IssueSeverity.MEDIUM,
                    message=f"网卡 {net_int.device_name} 中断率过高: {net_int.rate:.0f} 中断/秒",
                    value=net_int.rate,
                    threshold=self.config.network_interrupt_threshold,
                    recommendation="建议调整网卡中断合并参数或使用RSS分散负载",
                    additional_data={
                        "device": net_int.device_name,
                        "irq_number": net_int.irq_number,
                        "total_count": net_int.interrupt_count,
                        "cpu_distribution": net_int.cpu_distribution
                    }
                ))
        
        # 4. 分析ksoftirqd进程CPU占用
        for softirq in interrupts.ksoftirqd_processes:
            if softirq.cpu_percent > self.config.ksoftirqd_cpu_threshold:
                result.add_issue(Issue(
                    type=IssueType.CPU,
                    severity=IssueSeverity.MEDIUM,
                    message=f"CPU{softirq.cpu_id} 软中断处理占用过高: {softirq.cpu_percent:.1f}% (ksoftirqd/{softirq.cpu_id})",
                    value=softirq.cpu_percent,
                    threshold=self.config.ksoftirqd_cpu_threshold,
                    recommendation="建议检查网络流量或调整NAPI权重",
                    additional_data={
                        "cpu_id": softirq.cpu_id,
                        "pid": softirq.ksoftirqd_pid,
                        "net_rx": softirq.net_rx,
                        "net_tx": softirq.net_tx,
                        "total_softirq": softirq.total_softirq
                    }
                ))
        
        # 5. 分析系统级上下文切换
        if interrupts.context_switch_rate and interrupts.context_switch_rate > self.config.max_context_switch_rate:
            result.add_issue(Issue(
                type=IssueType.CPU,
                severity=IssueSeverity.HIGH,
                message=f"高上下文切换率: {interrupts.context_switch_rate:.0f} 切换/秒 (阈值: {self.config.max_context_switch_rate})",
                value=interrupts.context_switch_rate,
                threshold=self.config.max_context_switch_rate,
                recommendation="建议检查是否有大量短时间运行的进程或优化线程调度",
                additional_data={
                    "total_switches": interrupts.system_context_switches
                }
            ))
        
        # 6. 分析高上下文切换进程
        for proc_cs in interrupts.high_switch_processes:
            if proc_cs.switch_rate and proc_cs.switch_rate > self.config.high_context_switch_threshold:
                result.add_issue(Issue(
                    type=IssueType.PROCESS,
                    severity=IssueSeverity.MEDIUM,
                    message=f"进程 {proc_cs.name} (PID:{proc_cs.pid}) 上下文切换频繁: {proc_cs.switch_rate:.0f} 切换/秒",
                    value=proc_cs.switch_rate,
                    threshold=self.config.high_context_switch_threshold,
                    recommendation="建议使用taskset绑定CPU或优化程序逻辑减少阻塞操作",
                    additional_data={
                        "pid": proc_cs.pid,
                        "voluntary": proc_cs.voluntary_switches,
                        "nonvoluntary": proc_cs.nonvoluntary_switches,
                        "total": proc_cs.total_switches
                    }
                ))
        
        # 7. 添加优化建议
        self._add_interrupt_recommendations(result, interrupts)
    
    def _add_interrupt_recommendations(self, result: AnalysisResult, interrupts) -> None:
        """添加中断优化建议"""
        recommendations = set(result.recommendations or [])
        
        # 中断不均衡建议
        if interrupts.cpu_interrupt_distribution:
            cpu_avg = sum(interrupts.cpu_interrupt_distribution) / len(interrupts.cpu_interrupt_distribution)
            max_cpu_interrupts = max(interrupts.cpu_interrupt_distribution)
            if cpu_avg > 0 and max_cpu_interrupts > cpu_avg * 2:
                recommendations.add("检测到中断负载不均衡，建议启用 irqbalance 服务或手动绑定中断到多核")
                recommendations.add(f"可以使用: echo <CPU-mask> > /proc/irq/<IRQ-number>/smp_affinity 调整中断亲和性")
        
        # 网卡中断优化建议
        high_net_interrupts = [ni for ni in interrupts.network_interrupts 
                              if ni.rate and ni.rate > self.config.network_interrupt_threshold]
        if high_net_interrupts:
            recommendations.add("网卡中断率较高，考虑以下优化:")
            recommendations.add("1. 调整网卡中断合并参数 (ethtool -C)")
            recommendations.add("2. 使用RSS (Receive Side Scaling) 分散网络负载")
            recommendations.add("3. 考虑将网卡中断绑定到专用CPU核心")
        
        # ksoftirqd优化建议
        high_softirq = [si for si in interrupts.ksoftirqd_processes 
                       if si.cpu_percent > self.config.ksoftirqd_cpu_threshold]
        if high_softirq:
            recommendations.add("软中断处理负载过高，建议:")
            recommendations.add("1. 检查网络流量是否过大")
            recommendations.add("2. 调整网络设备的NAPI权重")
            recommendations.add("3. 考虑使用用户态网络栈 (如DPDK)")
        
        # 高上下文切换建议
        if interrupts.context_switch_rate and interrupts.context_switch_rate > self.config.max_context_switch_rate:
            recommendations.add("系统上下文切换过于频繁，建议:")
            recommendations.add("1. 检查是否有大量短时间运行的进程")
            recommendations.add("2. 优化应用程序减少线程创建/销毁")
            recommendations.add("3. 使用进程/线程池减少调度开销")
        
        # 高切换进程建议
        high_switch_procs = [p for p in interrupts.high_switch_processes 
                           if p.switch_rate and p.switch_rate > self.config.high_context_switch_threshold]
        if high_switch_procs:
            proc_names = [p.name for p in high_switch_procs[:3]]
            recommendations.add(f"进程 {', '.join(proc_names)} 等上下文切换频繁，建议:")
            recommendations.add("1. 使用 taskset 将高切换进程绑定到特定CPU核心")
            recommendations.add("2. 检查进程是否频繁进行I/O或IPC操作")
            recommendations.add("3. 优化程序逻辑减少阻塞操作")
        
        result.recommendations = list(recommendations)
    
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
    
    def _get_severity_by_ratio(self, value: float, threshold: float, high_threshold: Optional[float] = None, critical_threshold: Optional[float] = None) -> IssueSeverity:
        """根据值和阈值确定问题严重程度"""
        if high_threshold is None:
            high_threshold = threshold * 1.2
        if critical_threshold is None:
            critical_threshold = threshold * 1.5
            
        ratio = value / threshold if threshold > 0 else 0
        
        if value >= critical_threshold:
            return IssueSeverity.CRITICAL
        elif value >= high_threshold:
            return IssueSeverity.HIGH
        elif value >= threshold:
            return IssueSeverity.MEDIUM
        else:
            return IssueSeverity.LOW
