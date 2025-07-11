# Load Analyzer

一个增强的Linux系统负载分析工具，用于诊断系统性能问题。

## 功能特性

- **全面的系统指标采集**：CPU、内存、磁盘I/O、网络连接等
- **智能分析**：自动识别性能瓶颈和异常
- **多格式输出**：文本、JSON、CSV、HTML、Markdown
- **实时监控**：支持连续监控模式
- **可配置阈值**：支持自定义告警阈值
- **进程级分析**：识别高资源消耗的进程
- **彩色输出**：易于阅读的终端输出

## 安装

### 系统要求

- Python 3.8+
- Linux系统
- psutil库

### 安装方法

```bash
# 从源码安装
git clone <repository-url>
cd load_analyzer
pip install -e .

# 或者直接安装依赖
pip install psutil PyYAML rich
```

## 使用方法

### 基本用法

```bash
# 单次分析
load-analyzer

# 多次采样
load-analyzer -n 5 -i 2  # 5次采样，间隔2秒

# 指定输出格式
load-analyzer -f json -o report.json
load-analyzer -f html -o report.html

# 连续监控模式
load-analyzer --monitor
```

### 高级用法

```bash
# 使用配置文件
load-analyzer -c config.yaml

# 覆盖阈值设置
load-analyzer --cpu-threshold 90 --memory-threshold 85

# 创建默认配置文件
load-analyzer --create-config my_config.yaml

# 安静模式（仅显示问题）
load-analyzer --quiet

# 详细模式
load-analyzer --verbose
```

### 配置文件

创建配置文件以自定义分析参数：

```yaml
# 采样配置
sample_interval: 1
sample_count: 1
output_format: "text"
enable_colors: true

# 阈值设置
load_threshold_multiplier: 1.5
cpu_threshold: 80.0
memory_threshold: 80.0
swap_threshold: 50.0
iowait_threshold: 30.0
tcp_connections_threshold: 1000

# 进程分析
top_processes_count: 10

# 高级阈值
context_switches_threshold: 10000
interrupts_threshold: 5000
disk_io_read_threshold: 104857600   # 100MB/s
disk_io_write_threshold: 104857600  # 100MB/s
```

## 输出示例

### 文本输出

```
============================================================
         SYSTEM LOAD ANALYSIS REPORT
============================================================
Timestamp: 2025-07-11T10:30:00.123456

Load Status: HIGH

SYSTEM OVERVIEW
  CPU Cores: 8
  Load Averages: 12.50 / 8.30 / 6.20
  CPU Usage: 85.2%
  Memory Usage: 78.5%
  I/O Wait: 15.3%

🚨 CRITICAL ISSUES
  • High load average: 12.50 (threshold: 12.00)

⚠️  HIGH PRIORITY ISSUES
  • High CPU usage: 85.2% (threshold: 80.0%)

RECOMMENDATIONS
  1. Consider CPU scaling or process optimization
  2. Investigate CPU, I/O, or process issues
```

### JSON输出

```json
{
  "metrics": {
    "timestamp": "2025-07-11T10:30:00.123456",
    "load": {
      "load1": 12.5,
      "load5": 8.3,
      "load15": 6.2,
      "cpu_count": 8
    },
    "cpu": {
      "avg_usage": 85.2,
      "iowait_percent": 15.3
    }
  },
  "analysis": {
    "load_status": "high",
    "primary_issues": [
      {
        "type": "cpu",
        "severity": "high",
        "message": "High CPU usage: 85.2%",
        "recommendation": "Consider CPU scaling"
      }
    ]
  }
}
```

## 项目结构

```
load_analyzer/
├── __init__.py
├── cli.py                 # 命令行接口
├── config/                # 配置管理
│   ├── __init__.py
│   ├── manager.py
│   └── default.yaml
├── collector/             # 数据采集
│   ├── __init__.py
│   ├── data_collector.py
│   └── models.py
├── analyzer/              # 分析逻辑
│   ├── __init__.py
│   ├── analyzer.py
│   └── models.py
├── reporter/              # 报告生成
│   ├── __init__.py
│   └── reporters.py
└── tests/                 # 测试文件
    ├── __init__.py
    ├── test_collector.py
    ├── test_analyzer.py
    └── test_reporter.py
```

## API参考

### DataCollector

负责收集系统指标：

```python
from load_analyzer.collector import DataCollector
from load_analyzer.config import Config

config = Config()
collector = DataCollector(config)
metrics = collector.collect_all_metrics()
```

### Analyzer

分析系统指标：

```python
from load_analyzer.analyzer import Analyzer

analyzer = Analyzer(config)
analysis = analyzer.analyze(metrics)
```

### Reporter

生成报告：

```python
from load_analyzer.reporter import Reporter

reporter = Reporter(config)
report = reporter.generate_report(metrics, analysis)
```

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest

# 运行测试并查看覆盖率
pytest --cov=load_analyzer
```

### 代码格式化

```bash
# 格式化代码
black load_analyzer/

# 检查代码风格
flake8 load_analyzer/

# 类型检查
mypy load_analyzer/
```

## 故障排除

### 权限问题

某些系统指标需要特殊权限：

```bash
# 以root身份运行以获取完整信息
sudo load-analyzer

# 或者将用户添加到相关组
sudo usermod -a -G proc $USER
```

### 性能问题

如果分析工具本身影响系统性能：

```bash
# 使用更长的采样间隔
load-analyzer -i 5

# 减少采样次数
load-analyzer -n 1

# 使用安静模式
load-analyzer --quiet
```

## 许可证

MIT License

## 贡献

欢迎提交问题报告和功能请求！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 更新日志

### v1.0.0 (2025-07-11)

- 初始版本发布
- 完整的系统指标采集
- 智能分析和建议
- 多格式输出支持
- 命令行界面
