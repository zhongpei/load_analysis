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
class MetricsData:
    """Complete metrics data structure"""
    timestamp: str
    load: LoadMetrics
    cpu: CPUMetrics
    memory: MemoryMetrics
    disk_io: DiskIOMetrics
    network: NetworkMetrics
    top_processes: Dict[str, List[ProcessInfo]]
    
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
            }
        }
