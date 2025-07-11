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
    DiskIOMetrics, NetworkMetrics, ProcessInfo,
    InterruptMetrics, InterruptInfo, SoftIRQInfo, ContextSwitchInfo
)


class DataCollector:
    """Enhanced data collector for system metrics"""
    
    def __init__(self, config: Config):
        self.config = config
        self.previous_cpu_times = None
        self.previous_disk_io = None
        self.previous_net_io = None
        self.previous_interrupts = None
        self.previous_context_switches = None
        self.previous_proc_context_switches = {}
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
            },
            interrupts=self.get_interrupt_metrics()
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
    
    def get_interrupt_metrics(self) -> InterruptMetrics:
        """收集中断相关指标"""
        current_time = time.time()
        time_delta = current_time - self.start_time if hasattr(self, 'previous_interrupts') and self.previous_interrupts else 1.0
        
        # 1. 收集硬中断信息
        interrupts_data = self._parse_proc_interrupts()
        total_interrupts = sum(sum(cpu_counts) for cpu_counts in interrupts_data.values())
        
        # 计算中断率
        interrupt_rate = None
        if self.previous_interrupts is not None:
            interrupt_delta = total_interrupts - self.previous_interrupts
            interrupt_rate = interrupt_delta / time_delta if time_delta > 0 else 0
        
        # 2. 收集网卡中断信息
        network_interrupts = self._get_network_interrupts(interrupts_data, time_delta)
        
        # 3. 计算CPU中断分布
        cpu_interrupt_distribution = self._get_cpu_interrupt_distribution(interrupts_data)
        hottest_cpu = cpu_interrupt_distribution.index(max(cpu_interrupt_distribution)) if cpu_interrupt_distribution else None
        
        # 4. 收集ksoftirqd进程信息
        ksoftirqd_processes = self._get_ksoftirqd_processes()
        
        # 5. 收集上下文切换信息
        system_context_switches, context_switch_rate = self._get_context_switches(time_delta)
        high_switch_processes = self._get_high_context_switch_processes(time_delta)
        
        # 更新历史数据
        self.previous_interrupts = total_interrupts
        self.start_time = current_time
        
        return InterruptMetrics(
            total_interrupts=total_interrupts,
            system_context_switches=system_context_switches,
            interrupt_rate=interrupt_rate,
            context_switch_rate=context_switch_rate,
            hottest_cpu=hottest_cpu,
            network_interrupts=network_interrupts,
            cpu_interrupt_distribution=cpu_interrupt_distribution,
            ksoftirqd_processes=ksoftirqd_processes,
            high_switch_processes=high_switch_processes
        )
    
    def _parse_proc_interrupts(self) -> Dict[str, List[int]]:
        """解析/proc/interrupts文件"""
        interrupts_data = {}
        try:
            with open('/proc/interrupts', 'r') as f:
                lines = f.readlines()
                
            for line in lines[1:]:  # 跳过标题行
                parts = line.strip().split()
                if not parts:
                    continue
                    
                irq_name = parts[0].rstrip(':')
                if not irq_name.isdigit():
                    continue
                
                # 提取每个CPU的中断次数
                cpu_counts = []
                for i in range(1, len(parts)):
                    if parts[i].isdigit():
                        cpu_counts.append(int(parts[i]))
                    else:
                        break
                
                interrupts_data[irq_name] = cpu_counts
                
        except (FileNotFoundError, PermissionError):
            pass
            
        return interrupts_data
    
    def _get_network_interrupts(self, interrupts_data: Dict[str, List[int]], time_delta: float) -> List[InterruptInfo]:
        """获取网卡相关的中断信息"""
        network_interrupts = []
        
        try:
            with open('/proc/interrupts', 'r') as f:
                lines = f.readlines()
                
            for line in lines[1:]:
                parts = line.strip().split()
                if not parts or not parts[0].rstrip(':').isdigit():
                    continue
                    
                irq_number = int(parts[0].rstrip(':'))
                
                # 检查是否为网络设备中断
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['eth', 'ens', 'enp', 'wlan', 'wifi']):
                    # 提取设备名称
                    device_name = "unknown"
                    for part in parts:
                        if any(keyword in part.lower() for keyword in ['eth', 'ens', 'enp', 'wlan']):
                            device_name = part
                            break
                    
                    if str(irq_number) in interrupts_data:
                        cpu_distribution = interrupts_data[str(irq_number)]
                        interrupt_count = sum(cpu_distribution)
                        
                        # 计算中断率
                        rate = None
                        if hasattr(self, 'previous_net_interrupts') and str(irq_number) in self.previous_net_interrupts:
                            prev_count = self.previous_net_interrupts[str(irq_number)]
                            rate = (interrupt_count - prev_count) / time_delta if time_delta > 0 else 0
                        
                        network_interrupts.append(InterruptInfo(
                            irq_number=irq_number,
                            device_name=device_name,
                            interrupt_count=interrupt_count,
                            cpu_distribution=cpu_distribution,
                            rate=rate
                        ))
                        
        except (FileNotFoundError, PermissionError):
            pass
            
        # 保存当前中断计数供下次使用
        if not hasattr(self, 'previous_net_interrupts'):
            self.previous_net_interrupts = {}
        for ni in network_interrupts:
            self.previous_net_interrupts[str(ni.irq_number)] = ni.interrupt_count
            
        return network_interrupts
    
    def _get_cpu_interrupt_distribution(self, interrupts_data: Dict[str, List[int]]) -> List[int]:
        """计算每个CPU核心的总中断数"""
        if not interrupts_data:
            return []
            
        # 确定CPU核心数
        max_cpus = max(len(counts) for counts in interrupts_data.values()) if interrupts_data else 0
        cpu_totals = [0] * max_cpus
        
        for cpu_counts in interrupts_data.values():
            for i, count in enumerate(cpu_counts):
                if i < len(cpu_totals):
                    cpu_totals[i] += count
                    
        return cpu_totals
    
    def _get_ksoftirqd_processes(self) -> List[SoftIRQInfo]:
        """获取ksoftirqd进程信息"""
        ksoftirqd_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if 'ksoftirqd' in proc.info['name']:
                        # 提取CPU ID（从进程名如 ksoftirqd/0 中提取）
                        cpu_id = 0
                        if '/' in proc.info['name']:
                            try:
                                cpu_id = int(proc.info['name'].split('/')[-1])
                            except ValueError:
                                pass
                        
                        # 获取软中断统计（从/proc/softirqs）
                        net_rx, net_tx, total_softirq = self._get_softirq_stats(cpu_id)
                        
                        ksoftirqd_processes.append(SoftIRQInfo(
                            cpu_id=cpu_id,
                            ksoftirqd_pid=proc.info['pid'],
                            ksoftirqd_name=proc.info['name'],
                            cpu_percent=proc.info['cpu_percent'] or 0.0,
                            net_rx=net_rx,
                            net_tx=net_tx,
                            total_softirq=total_softirq
                        ))
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception:
            pass
            
        return ksoftirqd_processes
    
    def _get_softirq_stats(self, cpu_id: int) -> tuple:
        """从/proc/softirqs获取软中断统计"""
        net_rx = net_tx = total_softirq = 0
        
        try:
            with open('/proc/softirqs', 'r') as f:
                lines = f.readlines()
                
            for line in lines[1:]:  # 跳过标题行
                parts = line.strip().split()
                if not parts:
                    continue
                    
                softirq_name = parts[0].rstrip(':')
                if cpu_id + 1 < len(parts) and parts[cpu_id + 1].isdigit():
                    count = int(parts[cpu_id + 1])
                    total_softirq += count
                    
                    if 'NET_RX' in softirq_name:
                        net_rx = count
                    elif 'NET_TX' in softirq_name:
                        net_tx = count
                        
        except (FileNotFoundError, PermissionError):
            pass
            
        return net_rx, net_tx, total_softirq
    
    def _get_context_switches(self, time_delta: float) -> tuple:
        """获取系统级上下文切换信息"""
        system_context_switches = 0
        context_switch_rate = None
        
        try:
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('ctxt'):
                        system_context_switches = int(line.split()[1])
                        break
                        
            # 计算上下文切换率
            if self.previous_context_switches is not None:
                switch_delta = system_context_switches - self.previous_context_switches
                context_switch_rate = switch_delta / time_delta if time_delta > 0 else 0
                
            self.previous_context_switches = system_context_switches
            
        except (FileNotFoundError, PermissionError):
            pass
            
        return system_context_switches, context_switch_rate
    
    def _get_high_context_switch_processes(self, time_delta: float) -> List[ContextSwitchInfo]:
        """获取高上下文切换的进程"""
        high_switch_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 读取进程的上下文切换信息
                    with open(f'/proc/{proc.info["pid"]}/status', 'r') as f:
                        voluntary_switches = nonvoluntary_switches = 0
                        
                        for line in f:
                            if line.startswith('voluntary_ctxt_switches:'):
                                voluntary_switches = int(line.split()[1])
                            elif line.startswith('nonvoluntary_ctxt_switches:'):
                                nonvoluntary_switches = int(line.split()[1])
                    
                    total_switches = voluntary_switches + nonvoluntary_switches
                    
                    # 计算切换率
                    switch_rate = None
                    pid_str = str(proc.info['pid'])
                    if pid_str in self.previous_proc_context_switches:
                        prev_total = self.previous_proc_context_switches[pid_str]
                        switch_rate = (total_switches - prev_total) / time_delta if time_delta > 0 else 0
                    
                    # 只记录高切换率的进程（阈值可配置）
                    threshold = getattr(self.config, 'high_context_switch_threshold', 1000)
                    if switch_rate is None or switch_rate > threshold / time_delta:
                        high_switch_processes.append(ContextSwitchInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            voluntary_switches=voluntary_switches,
                            nonvoluntary_switches=nonvoluntary_switches,
                            total_switches=total_switches,
                            switch_rate=switch_rate
                        ))
                    
                    # 保存当前值供下次使用
                    self.previous_proc_context_switches[pid_str] = total_switches
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, FileNotFoundError, PermissionError):
                    continue
                    
        except Exception:
            pass
            
        # 按切换率排序，返回top N
        high_switch_processes.sort(key=lambda x: x.switch_rate or 0, reverse=True)
        return high_switch_processes[:10]  # 返回前10个高切换进程
