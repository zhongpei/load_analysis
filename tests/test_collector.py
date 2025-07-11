#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for data collector module
"""
import pytest
from unittest.mock import Mock, patch, mock_open
import psutil

from load_analyzer.config import Config
from load_analyzer.collector.data_collector import DataCollector
from load_analyzer.collector.models import (
    LoadMetrics, CPUMetrics, MemoryMetrics, DiskIOMetrics, NetworkMetrics
)


class TestDataCollector:
    """Test cases for DataCollector"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = Config()
        self.collector = DataCollector(self.config)
    
    def test_get_load_metrics(self):
        """Test load metrics collection"""
        with patch('os.getloadavg', return_value=(1.5, 2.0, 2.5)):
            with patch('psutil.cpu_count', return_value=4):
                metrics = self.collector.get_load_metrics()
                
                assert isinstance(metrics, LoadMetrics)
                assert metrics.load1 == 1.5
                assert metrics.load5 == 2.0
                assert metrics.load15 == 2.5
                assert metrics.cpu_count == 4
    
    def test_get_cpu_metrics(self):
        """Test CPU metrics collection"""
        mock_cpu_times = Mock()
        mock_cpu_times.user = 100.0
        mock_cpu_times.system = 50.0
        mock_cpu_times.idle = 800.0
        mock_cpu_times.iowait = 50.0
        mock_cpu_times.irq = 5.0
        mock_cpu_times.softirq = 5.0
        
        with patch('psutil.cpu_percent', return_value=[10.0, 20.0, 30.0, 40.0]):
            with patch('psutil.cpu_times', return_value=mock_cpu_times):
                with patch.object(self.collector, '_get_proc_stat_info', return_value=(1000, 500)):
                    metrics = self.collector.get_cpu_metrics()
                    
                    assert isinstance(metrics, CPUMetrics)
                    assert metrics.usage_per_core == [10.0, 20.0, 30.0, 40.0]
                    assert metrics.avg_usage == 25.0
                    assert metrics.context_switches == 1000
                    assert metrics.interrupts == 500
    
    def test_get_memory_metrics(self):
        """Test memory metrics collection"""
        mock_vm = Mock()
        mock_vm.total = 8 * 1024**3  # 8GB
        mock_vm.percent = 75.0
        mock_vm.available = 2 * 1024**3  # 2GB
        
        mock_swap = Mock()
        mock_swap.percent = 25.0
        mock_swap.total = 4 * 1024**3  # 4GB
        
        with patch('psutil.virtual_memory', return_value=mock_vm):
            with patch('psutil.swap_memory', return_value=mock_swap):
                with patch.object(self.collector, '_parse_meminfo', return_value={'Buffers': 1024**3, 'Cached': 2*1024**3}):
                    metrics = self.collector.get_memory_metrics()
                    
                    assert isinstance(metrics, MemoryMetrics)
                    assert metrics.total_gb == pytest.approx(8.0, rel=1e-1)
                    assert metrics.used_percent == 75.0
                    assert metrics.swap_percent == 25.0
    
    def test_get_disk_io_metrics(self):
        """Test disk I/O metrics collection"""
        mock_disk_io = Mock()
        mock_disk_io.read_count = 1000
        mock_disk_io.write_count = 500
        mock_disk_io.read_bytes = 1024**3  # 1GB
        mock_disk_io.write_bytes = 512*1024**2  # 512MB
        mock_disk_io.read_time = 1000
        mock_disk_io.write_time = 500
        
        with patch('psutil.disk_io_counters', return_value=mock_disk_io):
            metrics = self.collector.get_disk_io_metrics()
            
            assert isinstance(metrics, DiskIOMetrics)
            assert metrics.read_count == 1000
            assert metrics.write_count == 500
            assert metrics.read_bytes == 1024**3
            assert metrics.write_bytes == 512*1024**2
    
    def test_get_network_metrics(self):
        """Test network metrics collection"""
        mock_connection = Mock()
        mock_connection.status = 'ESTABLISHED'
        
        mock_net_io = Mock()
        mock_net_io.bytes_sent = 1024**2  # 1MB
        mock_net_io.bytes_recv = 2*1024**2  # 2MB
        mock_net_io.packets_sent = 1000
        mock_net_io.packets_recv = 2000
        
        with patch('psutil.net_connections', return_value=[mock_connection] * 5):
            with patch('psutil.net_io_counters', return_value=mock_net_io):
                with patch.object(self.collector, '_get_tcp_backlog', return_value={}):
                    metrics = self.collector.get_network_metrics()
                    
                    assert isinstance(metrics, NetworkMetrics)
                    assert metrics.total_connections == 5
                    assert metrics.tcp_connections['ESTABLISHED'] == 5
                    assert metrics.bytes_sent == 1024**2
                    assert metrics.bytes_recv == 2*1024**2
    
    def test_get_top_processes(self):
        """Test top processes collection"""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test_process',
            'cpu_percent': 50.0,
            'memory_percent': 25.0,
            'num_threads': 4
        }
        mock_proc.cmdline.return_value = ['test_process', '--arg1', '--arg2']
        mock_proc.connections.return_value = []
        mock_proc.io_counters.return_value = Mock(
            read_count=100, write_count=50,
            read_bytes=1024, write_bytes=512
        )
        
        with patch('psutil.process_iter', return_value=[mock_proc]):
            processes = self.collector.get_top_processes('cpu_percent')
            
            assert len(processes) > 0
            assert processes[0].pid == 1234
            assert processes[0].name == 'test_process'
            assert processes[0].cpu_percent == 50.0
    
    def test_parse_meminfo(self):
        """Test /proc/meminfo parsing"""
        meminfo_content = """MemTotal:        8192000 kB
MemFree:         2048000 kB
Buffers:         1024000 kB
Cached:          2048000 kB
"""
        
        with patch('builtins.open', mock_open(read_data=meminfo_content)):
            result = self.collector._parse_meminfo()
            
            assert result['MemTotal'] == 8192000 * 1024
            assert result['MemFree'] == 2048000 * 1024
            assert result['Buffers'] == 1024000 * 1024
            assert result['Cached'] == 2048000 * 1024
    
    def test_get_proc_stat_info(self):
        """Test /proc/stat parsing"""
        stat_content = """cpu  123456 0 234567 890123 45678 0 12345 0 0 0
cpu0 30000 0 50000 200000 10000 0 3000 0 0 0
ctxt 12345678
intr 9876543 0 0 0 0 0 0 0 0 0
"""
        
        with patch('builtins.open', mock_open(read_data=stat_content)):
            context_switches, interrupts = self.collector._get_proc_stat_info()
            
            assert context_switches == 12345678
            assert interrupts == 9876543
    
    def test_collect_all_metrics(self):
        """Test complete metrics collection"""
        # Mock all the individual metric collection methods
        with patch.object(self.collector, 'get_load_metrics') as mock_load:
            with patch.object(self.collector, 'get_cpu_metrics') as mock_cpu:
                with patch.object(self.collector, 'get_memory_metrics') as mock_memory:
                    with patch.object(self.collector, 'get_disk_io_metrics') as mock_disk:
                        with patch.object(self.collector, 'get_network_metrics') as mock_network:
                            with patch.object(self.collector, 'get_top_processes') as mock_processes:
                                with patch.object(self.collector, '_get_top_io_processes') as mock_io_processes:
                                    
                                    # Setup return values
                                    mock_load.return_value = LoadMetrics(1.0, 1.5, 2.0, 4)
                                    mock_cpu.return_value = CPUMetrics([10, 20, 30, 40], 25.0, {}, 5.0, 1000, 500)
                                    mock_memory.return_value = MemoryMetrics(8.0, 75.0, 2.0, 25.0, 4.0, 1.0, 2.0)
                                    mock_disk.return_value = DiskIOMetrics(1000, 500, 1024**3, 512*1024**2, 1000, 500)
                                    mock_network.return_value = NetworkMetrics({}, 0, 0, 0, 0, 0)
                                    mock_processes.return_value = []
                                    mock_io_processes.return_value = []
                                    
                                    metrics = self.collector.collect_all_metrics()
                                    
                                    assert metrics is not None
                                    assert metrics.timestamp is not None
                                    assert hasattr(metrics, 'load')
                                    assert hasattr(metrics, 'cpu')
                                    assert hasattr(metrics, 'memory')
                                    assert hasattr(metrics, 'disk_io')
                                    assert hasattr(metrics, 'network')
                                    assert hasattr(metrics, 'top_processes')


if __name__ == '__main__':
    pytest.main([__file__])
