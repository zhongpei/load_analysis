# Docker 部署说明

本文档说明如何使用Docker运行负载分析器。

## 文件说明

- `Dockerfile`: Docker镜像构建文件
- `run_in_docker.sh`: 完整的Docker运行脚本（推荐使用）
- `docker-compose.yml`: Docker Compose配置文件
- `.dockerignore`: Docker构建忽略文件

## 快速开始

### 方法1: 使用运行脚本（推荐）

```bash
# 基本使用
./run_in_docker.sh

# 查看帮助
./run_in_docker.sh --help

# 重新构建镜像并运行
./run_in_docker.sh --build

# 多次采样
./run_in_docker.sh -n 5 -i 2

# JSON格式输出
./run_in_docker.sh -f json -o /output/report.json

# 指定输出目录
./run_in_docker.sh -o ./reports

# 特权模式运行（获取更多系统权限）
./run_in_docker.sh --privileged

# 保留容器不删除（用于调试）
./run_in_docker.sh --no-remove
```

### 方法2: 使用Docker Compose

```bash
# 构建镜像
docker-compose build

# 运行默认命令
docker-compose run --rm load-analyzer

# 运行特定命令
docker-compose run --rm load-analyzer -n 5 -i 2 -f json

# 交互式运行
docker-compose run --rm load-analyzer-interactive
```

### 方法3: 直接使用Docker

```bash
# 构建镜像
docker build -t load-analyzer:latest .

# 运行容器
docker run --rm \
  --name load-analyzer \
  --network host \
  --pid host \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /:/host/root:ro \
  -v $(pwd)/output:/output:rw \
  --cap-add SYS_PTRACE \
  --cap-add SYS_ADMIN \
  --cap-add NET_ADMIN \
  --security-opt apparmor:unconfined \
  -e HOST_PROC=/host/proc \
  -e HOST_SYS=/host/sys \
  -e HOST_ROOT=/host/root \
  load-analyzer:latest
```

## 权限说明

容器需要以下权限来正确分析主机系统：

### 网络和进程命名空间
- `--network host`: 使用主机网络命名空间，获取真实网络信息
- `--pid host`: 使用主机进程命名空间，查看所有进程

### 卷挂载
- `/proc:/host/proc:ro`: 挂载主机proc文件系统（只读）
- `/sys:/host/sys:ro`: 挂载主机sys文件系统（只读）
- `/:/host/root:ro`: 挂载主机根目录（只读）
- `./output:/output:rw`: 输出目录（读写）

### 安全权限
- `SYS_PTRACE`: 允许追踪进程
- `SYS_ADMIN`: 允许系统管理操作
- `NET_ADMIN`: 允许网络管理
- `apparmor:unconfined`: 禁用AppArmor限制

## 输出目录

默认情况下，输出文件将保存在 `./output` 目录中。你可以通过以下方式自定义：

```bash
# 使用运行脚本指定输出目录
./run_in_docker.sh -o /path/to/output

# 修改docker-compose.yml中的卷挂载
volumes:
  - /custom/output:/output:rw
```

## 故障排除

### 权限问题
如果遇到权限问题，可以尝试：
```bash
# 使用特权模式
./run_in_docker.sh --privileged

# 或者手动添加更多权限
docker run --privileged ...
```

### 查看容器日志
```bash
# 保留容器并查看日志
./run_in_docker.sh --no-remove
docker logs load-analyzer-<timestamp>
```

### 进入容器调试
```bash
# 使用交互式模式
docker-compose run --rm load-analyzer-interactive

# 或者进入运行中的容器
docker exec -it <container_name> /bin/bash
```

## 安全注意事项

1. **权限控制**: 容器获得了较高的系统权限，请在可信环境中使用
2. **网络隔离**: 使用了主机网络，容器可以访问主机的所有网络接口
3. **文件系统访问**: 容器可以读取主机的文件系统（只读模式）
4. **进程可见性**: 容器可以看到主机上的所有进程

## 性能考虑

1. **资源限制**: Docker Compose中设置了内存限制，可根据需要调整
2. **I/O性能**: 大量的系统指标采集可能对性能有轻微影响
3. **存储空间**: 确保输出目录有足够的存储空间

## 自定义配置

可以通过以下方式自定义配置：

1. **修改配置文件**: 将自定义配置放在 `./config` 目录中
2. **环境变量**: 在docker-compose.yml中添加环境变量
3. **命令行参数**: 通过运行脚本传递参数给负载分析器
