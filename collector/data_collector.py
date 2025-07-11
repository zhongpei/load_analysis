#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced data collector for system metrics
"""
import os
import time
import subprocess
import psutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from collector.models import (
    MetricsData, LoadMetrics, CPUMetrics, MemoryMetrics, 
    DiskIOMetrics, NetworkMetrics, ProcessInfo
)


class DataCollector:
    """Enhanced data collector for system metrics"""
    
    def __init__(self, config: Config):
        self.config = config
        self.previous_cpu_times = None
        self.previous_disk_io = None
        self.previous_net_io = None
        self.start_time = time.time()
    
    def get_load_metrics(self) -> LoadMetrics:
        """Collect load average metrics"""
        load1, load5, load15 = os.getloadavg()
        cpu_count = psutil.cpu_count(logical=True) or 1  # Default to 1 if None
        
        return LoadMetrics(
            load1=load1,
            load5=load5,
            load15=load15,
            cpu_count=cpu_count
        )
    
    def get_cpu_metrics(self) -> CPUMetrics:
        """Collect CPU metrics"""
        # CPU usage per core
        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)
        avg_usage = sum(cpu_usage) / len(cpu_usage)
        
        # CPU times
        cpu_times = psutil.cpu_times()
        times_dict = {
            'user': cpu_times.user,
            'system': cpu_times.system,
            'idle': cpu_times.idle,
            'iowait': getattr(cpu_times, 'iowait', 0),
            'interrupt': getattr(cpu_times, 'irq', 0) + getattr(cpu_times, 'softirq', 0)
        }
        
        # Calculate iowait percentage
        total_cpu_time = sum(times_dict.values())
        iowait_percent = (times_dict['iowait'] / total_cpu_time) * 100 if total_cpu_time > 0 else 0
        
        # Get context switches and interrupts from /proc/stat
        context_switches, interrupts = self._get_proc_stat_info()
        
        return CPUMetrics(
            usage_per_core=cpu_usage,
            avg_usage=avg_usage,
            times=times_dict,
            iowait_percent=iowait_percent,
            context_switches=context_switches,
            interrupts=interrupts
        )
    
    def get_memory_metrics(self) -> MemoryMetrics:
        """Collect memory metrics"""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Parse /proc/meminfo for additional details
        meminfo = self._parse_meminfo()
        
        return MemoryMetrics(
            total_gb=vm.total / (1024**3),
            used_percent=vm.percent,
            available_gb=vm.available / (1024**3),
            swap_percent=swap.percent,
            swap_total_gb=swap.total / (1024**3),
            buffers_gb=meminfo.get('Buffers', 0) / (1024**3),
            cached_gb=meminfo.get('Cached', 0) / (1024**3)
        )
    
    def get_disk_io_metrics(self) -> DiskIOMetrics:
        """Collect disk I/O metrics"""
        disk_io = psutil.disk_io_counters()
        if not disk_io:
            return DiskIOMetrics(0, 0, 0, 0, 0, 0)
        
        metrics = DiskIOMetrics(
            read_count=disk_io.read_count,
            write_count=disk_io.write_count,
            read_bytes=disk_io.read_bytes,
            write_bytes=disk_io.write_bytes,
            read_time=disk_io.read_time,
            write_time=disk_io.write_time
        )
        
        # Calculate rates if we have previous data
        current_time = time.time()
        if self.previous_disk_io:
            time_diff = current_time - self.previous_disk_io['timestamp']
            if time_diff > 0:
                metrics.read_rate = (metrics.read_bytes - self.previous_disk_io['read_bytes']) / time_diff
                metrics.write_rate = (metrics.write_bytes - self.previous_disk_io['write_bytes']) / time_diff
        
        # Store current data for next calculation
        self.previous_disk_io = {
            'read_bytes': metrics.read_bytes,
            'write_bytes': metrics.write_bytes,
            'timestamp': current_time
        }
        
        return metrics
    
    def get_network_metrics(self) -> NetworkMetrics:
        """Collect network metrics"""
        try:
            # Get all connections
            connections = psutil.net_connections(kind='tcp')
            tcp_states = {}
            total_connections = len(connections)
            
            for conn in connections:
                state = conn.status
                tcp_states[state] = tcp_states.get(state, 0) + 1
            
            # Get network I/O stats
            net_io = psutil.net_io_counters()
            
            # Get TCP backlog information
            tcp_backlog = self._get_tcp_backlog()
            
            return NetworkMetrics(
                tcp_connections=tcp_states,
                total_connections=total_connections,
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                tcp_backlog=tcp_backlog
            )
        except Exception as e:
            # Fallback for limited permissions
            return NetworkMetrics(
                tcp_connections={},  # Empty dict instead of error dict
                total_connections=0,
                bytes_sent=0,
                bytes_recv=0,
                packets_sent=0,
                packets_recv=0
            )
    
    def get_top_processes(self, sort_by: str = 'cpu_percent') -> List[ProcessInfo]:
        """Get top processes by specified metric"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'num_threads']):
            try:
                info = proc.info
                
                # Get command line
                try:
                    cmdline = ' '.join(proc.cmdline()[:3])  # First 3 args
                    if not cmdline:
                        cmdline = info['name']
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    cmdline = info['name']
                
                # Get connections count
                try:
                    connections_count = len(proc.connections())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    connections_count = 0
                
                # Get I/O counters
                try:
                    io_counters = proc.io_counters()
                    io_dict = {
                        'read_count': io_counters.read_count,
                        'write_count': io_counters.write_count,
                        'read_bytes': io_counters.read_bytes,
                        'write_bytes': io_counters.write_bytes
                    }
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    io_dict = None
                
                process_info = ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_percent=info['memory_percent'] or 0.0,
                    num_threads=info['num_threads'] or 0,
                    cmdline=cmdline,
                    connections=connections_count,
                    io_counters=io_dict
                )
                
                processes.append(process_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort processes
        processes.sort(key=lambda x: getattr(x, sort_by, 0), reverse=True)
        return processes[:self.config.top_processes_count]
    
    def collect_all_metrics(self) -> MetricsData:
        """Collect all system metrics"""
        return MetricsData(
            timestamp=MetricsData.create_timestamp(),
            load=self.get_load_metrics(),
            cpu=self.get_cpu_metrics(),
            memory=self.get_memory_metrics(),
            disk_io=self.get_disk_io_metrics(),
            network=self.get_network_metrics(),
            top_processes={
                'by_cpu': self.get_top_processes('cpu_percent'),
                'by_memory': self.get_top_processes('memory_percent'),
                'by_io': self._get_top_io_processes()
            }
        )
    
    def _get_proc_stat_info(self) -> Tuple[int, int]:
        """Get context switches and interrupts from /proc/stat"""
        try:
            with open('/proc/stat', 'r') as f:
                lines = f.readlines()
            
            context_switches = 0
            interrupts = 0
            
            for line in lines:
                if line.startswith('ctxt '):
                    context_switches = int(line.split()[1])
                elif line.startswith('intr '):
                    interrupts = int(line.split()[1])
            
            return context_switches, interrupts
        except (IOError, ValueError):
            return 0, 0
    
    def _parse_meminfo(self) -> Dict[str, int]:
        """Parse /proc/meminfo for additional memory details"""
        meminfo = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        value = value.strip()
                        if value.endswith(' kB'):
                            value = int(value[:-3]) * 1024  # Convert to bytes
                        else:
                            value = int(value.split()[0]) if value.split() else 0
                        meminfo[key] = value
        except (IOError, ValueError):
            pass
        
        return meminfo
    
    def _get_tcp_backlog(self) -> Dict[str, int]:
        """Get TCP backlog information using ss command"""
        try:
            # Use ss command to get socket statistics
            result = subprocess.run(['ss', '-s'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return self._parse_ss_output(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return {}
    
    def _parse_ss_output(self, output: str) -> Dict[str, int]:
        """Parse ss command output for backlog information"""
        backlog_info = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if 'TCP:' in line:
                # Parse TCP statistics
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        # This is a simplified parser - in reality you'd need more sophisticated parsing
                        backlog_info['active'] = int(part)
                        break
        
        return backlog_info
    
    def _get_top_io_processes(self) -> List[ProcessInfo]:
        """Get top processes by I/O activity"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'num_threads']):
            try:
                info = proc.info
                
                # Get I/O counters
                try:
                    io_counters = proc.io_counters()
                    total_io = io_counters.read_bytes + io_counters.write_bytes
                    
                    cmdline = ' '.join(proc.cmdline()[:3]) if proc.cmdline() else info['name']
                    
                    process_info = ProcessInfo(
                        pid=info['pid'],
                        name=info['name'],
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_percent=info['memory_percent'] or 0.0,
                        num_threads=info['num_threads'] or 0,
                        cmdline=cmdline,
                        connections=0,  # Not needed for I/O sorting
                        io_counters={
                            'read_count': io_counters.read_count,
                            'write_count': io_counters.write_count,
                            'read_bytes': io_counters.read_bytes,
                            'write_bytes': io_counters.write_bytes,
                            'total_bytes': total_io
                        }
                    )
                    
                    processes.append(process_info)
                    
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by total I/O bytes
        processes.sort(key=lambda x: x.io_counters.get('total_bytes', 0) if x.io_counters else 0, reverse=True)
        return processes[:self.config.top_processes_count]
