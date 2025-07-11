#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data structures for metrics collection
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional


@dataclass
class LoadMetrics:
    """Load average metrics"""
    load1: float
    load5: float
    load15: float
    cpu_count: int


@dataclass
class CPUMetrics:
    """CPU usage metrics"""
    usage_per_core: List[float]
    avg_usage: float
    times: Dict[str, float]
    iowait_percent: float
    context_switches: int
    interrupts: int


@dataclass
class MemoryMetrics:
    """Memory usage metrics"""
    total_gb: float
    used_percent: float
    available_gb: float
    swap_percent: float
    swap_total_gb: float
    buffers_gb: float
    cached_gb: float


@dataclass
class DiskIOMetrics:
    """Disk I/O metrics"""
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    read_time: int
    write_time: int
    read_rate: Optional[float] = None
    write_rate: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'read_count': self.read_count,
            'write_count': self.write_count,
            'read_bytes': self.read_bytes,
            'write_bytes': self.write_bytes,
            'read_time': self.read_time,
            'write_time': self.write_time,
            'read_rate': self.read_rate,
            'write_rate': self.write_rate
        }


@dataclass
class NetworkMetrics:
    """Network metrics"""
    tcp_connections: Dict[str, int]
    total_connections: int
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    tcp_backlog: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    num_threads: int
    cmdline: str
    connections: int
    io_counters: Optional[Dict[str, int]] = None


@dataclass
class InterruptInfo:
    """网卡中断信息"""
    irq_number: int
    device_name: str
    interrupt_count: int
    cpu_distribution: List[int]  # 每个CPU核心的中断次数
    rate: Optional[float] = None  # 中断率（次/秒）


@dataclass
class SoftIRQInfo:
    """软中断信息"""
    cpu_id: int
    ksoftirqd_pid: int
    ksoftirqd_name: str
    cpu_percent: float
    net_rx: int
    net_tx: int
    total_softirq: int


@dataclass
class ContextSwitchInfo:
    """上下文切换信息"""
    pid: int
    name: str
    voluntary_switches: int
    nonvoluntary_switches: int
    total_switches: int
    switch_rate: Optional[float] = None  # 切换率（次/秒）


@dataclass
class InterruptMetrics:
    """中断相关指标"""
    # 硬中断统计
    total_interrupts: int
    system_context_switches: int
    interrupt_rate: Optional[float] = None
    context_switch_rate: Optional[float] = None
    hottest_cpu: Optional[int] = None  # 中断负载最高的CPU核心
    network_interrupts: List[InterruptInfo] = field(default_factory=list)
    cpu_interrupt_distribution: List[int] = field(default_factory=list)  # 每个CPU的总中断数
    ksoftirqd_processes: List[SoftIRQInfo] = field(default_factory=list)
    high_switch_processes: List[ContextSwitchInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_interrupts': self.total_interrupts,
            'interrupt_rate': self.interrupt_rate,
            'network_interrupts': [
                {
                    'irq_number': ni.irq_number,
                    'device_name': ni.device_name,
                    'interrupt_count': ni.interrupt_count,
                    'cpu_distribution': ni.cpu_distribution,
                    'rate': ni.rate
                }
                for ni in self.network_interrupts
            ],
            'cpu_interrupt_distribution': self.cpu_interrupt_distribution,
            'ksoftirqd_processes': [
                {
                    'cpu_id': si.cpu_id,
                    'ksoftirqd_pid': si.ksoftirqd_pid,
                    'ksoftirqd_name': si.ksoftirqd_name,
                    'cpu_percent': si.cpu_percent,
                    'net_rx': si.net_rx,
                    'net_tx': si.net_tx,
                    'total_softirq': si.total_softirq
                }
                for si in self.ksoftirqd_processes
            ],
            'hottest_cpu': self.hottest_cpu,
            'system_context_switches': self.system_context_switches,
            'context_switch_rate': self.context_switch_rate,
            'high_switch_processes': [
                {
                    'pid': cs.pid,
                    'name': cs.name,
                    'voluntary_switches': cs.voluntary_switches,
                    'nonvoluntary_switches': cs.nonvoluntary_switches,
                    'total_switches': cs.total_switches,
                    'switch_rate': cs.switch_rate
                }
                for cs in self.high_switch_processes
            ]
        }


@dataclass
class MetricsData:
    """Complete metrics data structure"""
    timestamp: str
    load: LoadMetrics
    cpu: CPUMetrics
    memory: MemoryMetrics
    disk_io: DiskIOMetrics
    network: NetworkMetrics
    top_processes: Dict[str, List[ProcessInfo]]
    interrupts: Optional[InterruptMetrics] = None
    
    @classmethod
    def create_timestamp(cls) -> str:
        """Create current timestamp"""
        return datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'load': {
                'load1': self.load.load1,
                'load5': self.load.load5,
                'load15': self.load.load15,
                'cpu_count': self.load.cpu_count
            },
            'cpu': {
                'usage_per_core': self.cpu.usage_per_core,
                'avg_usage': self.cpu.avg_usage,
                'times': self.cpu.times,
                'iowait_percent': self.cpu.iowait_percent,
                'context_switches': self.cpu.context_switches,
                'interrupts': self.cpu.interrupts
            },
            'memory': {
                'total_gb': self.memory.total_gb,
                'used_percent': self.memory.used_percent,
                'available_gb': self.memory.available_gb,
                'swap_percent': self.memory.swap_percent,
                'swap_total_gb': self.memory.swap_total_gb,
                'buffers_gb': self.memory.buffers_gb,
                'cached_gb': self.memory.cached_gb
            },
            'disk_io': {
                'read_count': self.disk_io.read_count,
                'write_count': self.disk_io.write_count,
                'read_bytes': self.disk_io.read_bytes,
                'write_bytes': self.disk_io.write_bytes,
                'read_time': self.disk_io.read_time,
                'write_time': self.disk_io.write_time,
                'read_rate': self.disk_io.read_rate,
                'write_rate': self.disk_io.write_rate
            },
            'network': {
                'tcp_connections': self.network.tcp_connections,
                'total_connections': self.network.total_connections,
                'bytes_sent': self.network.bytes_sent,
                'bytes_recv': self.network.bytes_recv,
                'packets_sent': self.network.packets_sent,
                'packets_recv': self.network.packets_recv,
                'tcp_backlog': self.network.tcp_backlog
            },
            'top_processes': {
                key: [
                    {
                        'pid': proc.pid,
                        'name': proc.name,
                        'cpu_percent': proc.cpu_percent,
                        'memory_percent': proc.memory_percent,
                        'num_threads': proc.num_threads,
                        'cmdline': proc.cmdline,
                        'connections': proc.connections,
                        'io_counters': proc.io_counters
                    }
                    for proc in processes
                ]
                for key, processes in self.top_processes.items()
            },
            'interrupts': self.interrupts.to_dict() if self.interrupts else None
        }
