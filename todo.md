
# TODO: 深度分析中断与上下文切换

## 1. 分析网卡中断与软中断（ksoftirqd）  
- [ ] 采集各网卡中断次数  
  - 读取 `/proc/interrupts` 中各网络接口（如 `eth0`、`ens33`）对应的 RX/TX 硬中断计数  
  - 定时采样并计算差分  
- [ ] 采集 CPU 级中断统计  
  - 从 `/proc/interrupts` 中各 CPU 栏位累加中断数  
  - 计算每核中断率并标记异常核  
- [ ] 采集 ksoftirqd 线程 CPU 占用  
  - 通过 `psutil.process_iter()` 或 `ps -C ksoftirqd* -o pid,pcpu` 获取所有 ksoftirqd 进程及其 CPU%  
  - 计算占用率并关联到对应的 CPU 核  
- [ ] 分析并报告  
  - 汇总最热网卡、最热 CPU 核及软中断线程  
  - 判断是否存在单点核心过载或软中断“风暴”  
- [ ] 建议与优化  
  - 如果某核负载过高，建议使用 `irqbalance` 或手动将中断绑定到多核：  
    ```bash
    echo <CPU-mask> > /proc/irq/<IRQ-number>/smp_affinity
    ```  
  - 对关键网卡中断可考虑专核处理，避免与用户态任务争抢  

## 2. 分析高频上下文切换  
- [x] 采集系统级上下文切换总量  
  - 读取 `/proc/stat` 中 `ctxt` 字段  
  - 计算单位时间（如 1s）内的上下文切换增量  
- [x] 判断超阈值  
  - 对比用户配置阈值（默认 10000 次/s），标记是否告警  
- [x] 识别高切换进程  
  - 遍历所有进程：  
    - 从 `/proc/[pid]/status` 或 `ps -p [pid] -o cstime` 读取进程上下文切换次数  
    - 计算差分，找出 Top N 增量最高进程  
- [x] 建议与优化  
  - 对高切换进程，分析是否因频繁 I/O、IPC 或线程调度导致  
  - 考虑：  
    - 合并或减少线程/定时器唤醒  
    - 将高切换进程绑定到特定 CPU 核（使用 `taskset`）  
    - 调整进程优先级或使用 `sched_setaffinity()` 在程序中设定亲和性  
    - 如果是网络/磁盘 I/O 频繁，优化工作队列或使用批量处理减少唤醒  

## 3. 集成到诊断脚本  
- [x] 在 `DataCollector` 增加中断与上下文切换采集接口  
- [x] 在 `Analyzer` 中增加：  
  - 中断与软中断热点判定  
  - 上下文切换主因进程定位  
- [x] 在 `Reporter` 中展示：  
  - 各网卡/CPU 软硬中断负载  
  - ksoftirqd CPU 使用详情  
  - 系统与进程级上下文切换统计与建议  
- [x] 编写单元与集成测试  
  - 模拟 `/proc/interrupts` 与 `/proc/stat` 数据  
  - 对比输出与预期优化建议  


