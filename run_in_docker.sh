#!/bin/bash

# run_in_docker.sh - 在Docker容器中运行负载分析器
# 此脚本将主机权限映射到容器中，并挂载必要的目录

set -e

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="load-analyzer"
IMAGE_NAME="load-analyzer:latest"
CONTAINER_NAME="load-analyzer-$(date +%s)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "无法连接到Docker守护进程，请检查Docker是否运行"
        exit 1
    fi
}

# 构建Docker镜像
build_image() {
    log_info "构建Docker镜像..."
    cd "$SCRIPT_DIR"
    
    if docker build -t "$IMAGE_NAME" .; then
        log_info "Docker镜像构建成功"
    else
        log_error "Docker镜像构建失败"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
使用方法: $0 [选项] [负载分析器参数]

选项:
  -h, --help          显示此帮助信息
  -b, --build         强制重新构建Docker镜像
  -o, --output DIR    指定输出目录 (默认: ./output)
  --privileged        以特权模式运行容器
  --no-remove         运行后不删除容器

示例:
  $0                                    # 运行默认分析
  $0 -n 5 -i 2                        # 5次采样，间隔2秒
  $0 -f json -o /output/report.json    # JSON格式输出
  $0 --build -n 10                     # 重新构建镜像并运行
  $0 -o ./reports --no-remove          # 输出到./reports目录且不删除容器

更多负载分析器参数请参考: load-analyzer --help
EOF
}

# 解析命令行参数
parse_args() {
    BUILD_IMAGE=false
    OUTPUT_DIR="$SCRIPT_DIR/output"
    PRIVILEGED=false
    REMOVE_CONTAINER=true
    ANALYZER_ARGS=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -b|--build)
                BUILD_IMAGE=true
                shift
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --privileged)
                PRIVILEGED=true
                shift
                ;;
            --no-remove)
                REMOVE_CONTAINER=false
                shift
                ;;
            *)
                ANALYZER_ARGS+=("$1")
                shift
                ;;
        esac
    done
    
    # 确保输出目录是绝对路径
    OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"
}

# 创建输出目录
setup_output_dir() {
    if [[ ! -d "$OUTPUT_DIR" ]]; then
        log_info "创建输出目录: $OUTPUT_DIR"
        mkdir -p "$OUTPUT_DIR"
    fi
    
    # 设置权限以便容器可以写入
    chmod 755 "$OUTPUT_DIR"
}

# 运行容器
run_container() {
    log_info "启动负载分析器容器..."
    
    # 构建Docker运行参数
    DOCKER_ARGS=(
        "run"
        "--rm=$REMOVE_CONTAINER"
        "--name" "$CONTAINER_NAME"
        "--hostname" "load-analyzer"
        
        # 网络和进程命名空间 - 使用主机的以获取真实信息
        "--network" "host"
        "--pid" "host"
        
        # 挂载点
        "--volume" "/proc:/host/proc:ro"          # 进程信息
        "--volume" "/sys:/host/sys:ro"            # 系统信息
        "--volume" "/:/host/root:ro"              # 主机根目录（只读）
        "--volume" "$OUTPUT_DIR:/output:rw"       # 输出目录
        
        # 环境变量
        "--env" "HOST_PROC=/host/proc"
        "--env" "HOST_SYS=/host/sys"
        "--env" "HOST_ROOT=/host/root"
        
        # 安全配置
        "--cap-add" "SYS_PTRACE"     # 允许追踪进程
        "--cap-add" "SYS_ADMIN"      # 允许系统管理操作
        "--cap-add" "NET_ADMIN"      # 允许网络管理
        "--security-opt" "apparmor:unconfined"  # 禁用AppArmor限制
    )
    
    # 如果指定了特权模式
    if [[ "$PRIVILEGED" == true ]]; then
        log_warn "以特权模式运行容器"
        DOCKER_ARGS+=("--privileged")
    fi
    
    # 添加镜像名称
    DOCKER_ARGS+=("$IMAGE_NAME")
    
    # 添加负载分析器参数
    if [[ ${#ANALYZER_ARGS[@]} -gt 0 ]]; then
        DOCKER_ARGS+=("${ANALYZER_ARGS[@]}")
    fi
    
    log_info "运行命令: docker ${DOCKER_ARGS[*]}"
    
    # 执行Docker容器
    if docker "${DOCKER_ARGS[@]}"; then
        log_info "负载分析完成"
        if [[ -d "$OUTPUT_DIR" ]] && [[ -n "$(ls -A "$OUTPUT_DIR" 2>/dev/null)" ]]; then
            log_info "输出文件保存在: $OUTPUT_DIR"
        fi
    else
        log_error "容器运行失败"
        exit 1
    fi
}

# 清理函数
cleanup() {
    local exit_code=$?
    if [[ "$REMOVE_CONTAINER" == false ]] && docker ps -a --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
        log_info "容器 $CONTAINER_NAME 保留，可使用以下命令查看："
        echo "  docker logs $CONTAINER_NAME"
        echo "  docker exec -it $CONTAINER_NAME /bin/bash"
        echo "  docker rm $CONTAINER_NAME  # 删除容器"
    fi
    exit $exit_code
}

# 主函数
main() {
    # 设置错误处理
    trap cleanup EXIT
    
    # 解析参数
    parse_args "$@"
    
    # 检查Docker
    check_docker
    
    # 检查是否需要构建镜像
    if [[ "$BUILD_IMAGE" == true ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
        build_image
    fi
    
    # 设置输出目录
    setup_output_dir
    
    # 运行容器
    run_container
}

# 执行主函数
main "$@"
