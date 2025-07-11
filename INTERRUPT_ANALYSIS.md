# 中断与上下文切换分析模块

本文档描述了新增的中断与上下文切换分析功能。

## 功能概述

中断分析模块提供了深度的系统中断与上下文切换分析，帮助识别系统性能瓶颈和优化机会。

### 主要功能

1. **硬中断分析**
   - 收集系统总中断数和中断率
   - 分析CPU核心间中断分布不均
   - 识别中断负载最高的CPU核心

2. **网卡中断分析**
   - 识别网络设备相关的中断
   - 计算每个网卡的中断率
   - 分析网卡中断的CPU分布

3. **软中断分析**
   - 监控ksoftirqd进程的CPU占用
   - 分析NET_RX/NET_TX软中断统计
   - 识别软中断负载过高的CPU核心

4. **上下文切换分析**
   - 收集系统级上下文切换统计
   - 识别高上下文切换的进程
   - 区分自愿和非自愿上下文切换

## 配置选项

在配置文件中添加以下选项来控制中断分析：

```yaml
# 中断分析配置
enable_interrupt_analysis: true       # 启用中断分析
high_context_switch_threshold: 1000   # 高上下文切换进程阈值
max_interrupt_rate: 10000            # 最大中断率每秒
max_context_switch_rate: 20000       # 最大上下文切换率每秒
ksoftirqd_cpu_threshold: 10.0        # ksoftirqd CPU使用阈值(%)
network_interrupt_threshold: 1000    # 网络中断率阈值
```

## 数据收集

### 数据源

- `/proc/interrupts` - 硬中断统计
- `/proc/softirqs` - 软中断统计  
- `/proc/stat` - 系统级上下文切换
- `/proc/[pid]/status` - 进程级上下文切换
- `psutil.process_iter()` - ksoftirqd进程信息

### 收集的指标

```python
InterruptMetrics(
    total_interrupts: int,                    # 总中断数
    system_context_switches: int,            # 系统上下文切换数
    interrupt_rate: float,                    # 中断率(/秒)
    context_switch_rate: float,               # 上下文切换率(/秒)
    hottest_cpu: int,                         # 最热CPU核心
    network_interrupts: List[InterruptInfo], # 网卡中断信息
    cpu_interrupt_distribution: List[int],   # CPU中断分布
    ksoftirqd_processes: List[SoftIRQInfo],  # 软中断进程
    high_switch_processes: List[ContextSwitchInfo] # 高切换进程
)
```

## 分析算法

### 中断负载不均检测

```python
cpu_avg = sum(cpu_interrupt_distribution) / len(cpu_interrupt_distribution)
max_cpu_interrupts = max(cpu_interrupt_distribution)
if max_cpu_interrupts > cpu_avg * 3:
    # 检测到中断负载不均
```

### 高中断率检测

```python
if interrupt_rate > max_interrupt_rate:
    # 中断率过高告警
```

### 软中断负载检测

```python
if ksoftirqd_cpu_percent > ksoftirqd_cpu_threshold:
    # ksoftirqd CPU占用过高
```

### 高上下文切换检测

```python
if context_switch_rate > max_context_switch_rate:
    # 系统级上下文切换过高

if process_switch_rate > high_context_switch_threshold:
    # 进程级上下文切换过高
```

## 报告输出

### 文本报告示例

```
INTERRUPT & CONTEXT SWITCH ANALYSIS
  Total Interrupts: 1,234,567
  Interrupt Rate: 5,432/sec
  Hottest CPU: Core 2
  CPU Interrupt Distribution:
    → Core  0: 123,456
      Core  1: 234,567
    → Core  2: 456,789  
      Core  3: 234,567

  Network Interrupts:
    IRQ  24 - eth0: 456,789 (2,345/sec)
      Distribution: CPU0:100000, CPU1:200000, CPU2:156789

  Software Interrupt Processes:
    ksoftirqd/0 (PID 12): 5.2% CPU
      NET_RX: 123,456, NET_TX: 67,890
    ksoftirqd/2 (PID 25): 15.3% CPU
      NET_RX: 456,789, NET_TX: 234,567

  Context Switches: 9,876,543
  Context Switch Rate: 12,345/sec

  High Context Switch Processes:
    PID 1234 - nginx: 5,432 switches (543/sec)
      Voluntary: 4,321, Non-voluntary: 1,111
```

## 优化建议

系统会根据分析结果自动生成优化建议：

### 中断优化建议

1. **中断负载不均衡**
   ```bash
   # 启用irqbalance服务
   systemctl enable irqbalance
   systemctl start irqbalance
   
   # 手动绑定中断到多核
   echo <CPU-mask> > /proc/irq/<IRQ-number>/smp_affinity
   ```

2. **网卡中断优化**
   ```bash
   # 调整网卡中断合并参数
   ethtool -C eth0 rx-usecs 50 rx-frames 32
   
   # 启用RSS (Receive Side Scaling)
   ethtool -X eth0 equal 4
   ```

3. **软中断优化**
   ```bash
   # 调整网络设备NAPI权重
   echo 64 > /sys/class/net/eth0/queues/rx-0/rps_flow_cnt
   
   # 设置RPS CPU掩码
   echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus
   ```

### 上下文切换优化建议

1. **进程绑定**
   ```bash
   # 使用taskset绑定高切换进程到特定CPU
   taskset -cp 2-3 <PID>
   ```

2. **程序优化**
   - 减少线程创建/销毁
   - 使用进程/线程池
   - 优化I/O操作，减少阻塞
   - 使用异步I/O

## API接口

### DataCollector

```python
def get_interrupt_metrics(self) -> InterruptMetrics:
    """收集中断相关指标"""
```

### Analyzer

```python
def _analyze_interrupts(self, metrics: MetricsData, result: AnalysisResult) -> None:
    """分析中断和上下文切换"""
```

### Reporter

```python
def _generate_interrupt_report(self, interrupts) -> List[str]:
    """生成中断分析报告"""
```

## 测试

使用测试脚本验证功能：

```bash
python test_interrupt_analysis.py
```

测试会执行以下操作：
1. 收集系统中断和上下文切换数据
2. 执行分析算法
3. 生成详细报告
4. 验证数据完整性

## 性能影响

中断分析模块的性能影响：

- **CPU开销**: 增加约2-5%的CPU使用（主要来自/proc文件系统读取）
- **内存开销**: 增加约5-10MB内存使用
- **磁盘I/O**: 每次分析读取约10-20个/proc文件
- **网络影响**: 无直接网络影响

## 故障排除

### 常见问题

1. **权限不足**
   ```
   Error: Permission denied reading /proc/interrupts
   ```
   解决方案：确保程序有读取/proc文件系统的权限

2. **数据不完整**
   ```
   Warning: No interrupt data collected!
   ```
   解决方案：检查系统是否支持/proc/interrupts和/proc/softirqs

3. **性能影响**
   - 在高负载系统上，可以调整采样间隔
   - 使用配置选项禁用不需要的分析

### 调试选项

启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展开发

### 添加新的中断类型分析

1. 扩展`InterruptInfo`数据结构
2. 在`_parse_proc_interrupts()`中添加解析逻辑
3. 在`_analyze_interrupts()`中添加分析规则
4. 更新报告模板

### 添加新的优化建议

1. 在`_add_interrupt_recommendations()`中添加新的建议逻辑
2. 根据分析结果添加条件判断
3. 提供具体的命令行示例

## 相关文档

- [系统性能分析指南](performance-analysis.md)
- [配置文件说明](configuration.md)
- [API参考手册](api-reference.md)
- [故障排除指南](troubleshooting.md)
