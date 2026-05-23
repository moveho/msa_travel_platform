#!/bin/bash
# ==============================================================
# MSA Travel Platform - k3s 설치 및 배포 스크립트 (WSL2용)
# ==============================================================
set -e

K8S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(dirname "$K8S_DIR")/docker-compose"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --------------------------------------------------------------
# STEP 1: k3s 설치
# --------------------------------------------------------------
install_k3s() {
  info "=== STEP 1: k3s 설치 ==="

  if command -v k3s &>/dev/null; then
    success "k3s 이미 설치됨: $(k3s --version | head -1)"
    return
  fi

  info "k3s 설치 중 (Traefik 비활성화 - Nginx로 대체)..."
  curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --disable traefik" sh -

  # kubeconfig 설정
  mkdir -p ~/.kube
  sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
  sudo chown "$USER":"$USER" ~/.kube/config
  chmod 600 ~/.kube/config

  success "k3s 설치 완료"
}

# --------------------------------------------------------------
# STEP 2: k3s 실행 확인
# --------------------------------------------------------------
wait_k3s_ready() {
  info "=== STEP 2: k3s 클러스터 준비 대기 ==="

  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

  local retries=30
  for i in $(seq 1 $retries); do
    if sudo k3s kubectl get nodes 2>/dev/null | grep -q "Ready"; then
      success "k3s 클러스터 준비 완료"
      sudo k3s kubectl get nodes
      return
    fi
    warn "노드 준비 대기 중... ($i/$retries)"
    sleep 5
  done
  error "k3s 클러스터가 준비되지 않았습니다. 'sudo systemctl status k3s' 확인"
}

# --------------------------------------------------------------
# STEP 3: Docker 이미지 빌드 → k3s containerd import
# --------------------------------------------------------------
build_and_import_images() {
  info "=== STEP 3: Docker 이미지 빌드 및 k3s import ==="

  if ! command -v docker &>/dev/null; then
    error "Docker가 설치되지 않았습니다."
  fi

  declare -A SERVICES=(
    ["user-service"]="msa-user-service:latest"
    ["auth-service"]="msa-auth-service:latest"
    ["travel-service"]="msa-travel-service:latest"
    ["schedule-service"]="msa-schedule-service:latest"
    ["crawler-service"]="msa-crawler-service:latest"
    ["frontend"]="msa-frontend:latest"
  )

  for svc in "${!SERVICES[@]}"; do
    tag="${SERVICES[$svc]}"
    src_dir="$COMPOSE_DIR/$svc"

    if [ ! -d "$src_dir" ]; then
      warn "$src_dir 디렉토리 없음. 건너뜀."
      continue
    fi

    info "빌드 중: $tag (from $src_dir)"
    docker build -t "$tag" "$src_dir"

    info "k3s containerd로 import 중: $tag"
    docker save "$tag" | sudo k3s ctr images import -

    success "$tag 완료"
  done

  # recommendation-service는 이미지 파일 포함을 위해 k8s/ 를 빌드 컨텍스트로 사용
  info "빌드 중: msa-recommendation-service:latest (from $K8S_DIR)"
  docker build -t "msa-recommendation-service:latest" \
    -f "$K8S_DIR/recommendation-service/Dockerfile" \
    "$K8S_DIR"

  info "k3s containerd로 import 중: msa-recommendation-service:latest"
  docker save "msa-recommendation-service:latest" | sudo k3s ctr images import -
  success "msa-recommendation-service:latest 완료"
}

# --------------------------------------------------------------
# STEP 4: 매니페스트 순서대로 적용
# --------------------------------------------------------------
deploy_manifests() {
  info "=== STEP 4: Kubernetes 매니페스트 배포 ==="

  local KUBECTL="sudo k3s kubectl"

  MANIFESTS=(
    "01-config.yaml"
    "02-mongodb.yaml"
    "03-zookeeper.yaml"
    "04-kafka.yaml"
    "05-user-service.yaml"
    "06-auth-service.yaml"
    "07-travel-service.yaml"
    "08-schedule-service.yaml"
    "09-recommendation-service.yaml"
    "10-crawler-service.yaml"
    "11-frontend.yaml"
  )

  for manifest in "${MANIFESTS[@]}"; do
    filepath="$K8S_DIR/$manifest"
    if [ -f "$filepath" ]; then
      info "적용 중: $manifest"
      $KUBECTL apply -f "$filepath"
    else
      warn "$manifest 파일 없음. 건너뜀."
    fi
  done

  success "모든 매니페스트 적용 완료"
}

# --------------------------------------------------------------
# STEP 5: 배포 상태 확인
# --------------------------------------------------------------
check_status() {
  info "=== STEP 5: 배포 상태 확인 ==="
  local KUBECTL="sudo k3s kubectl"

  info "Pod 상태 대기 중 (최대 3분)..."
  $KUBECTL wait --for=condition=available --timeout=180s \
    deployment/mongodb deployment/zookeeper deployment/kafka 2>/dev/null || true

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  📦 Pod 목록"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  $KUBECTL get pods -o wide

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  🌐 Service 목록"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  $KUBECTL get services

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  💾 PersistentVolumeClaim"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  $KUBECTL get pvc

  # WSL IP 얻기
  WSL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' 2>/dev/null || hostname -I | awk '{print $1}')

  echo ""
  success "==================================================="
  success " 🚀 배포 완료!"
  success " 프론트엔드 접속: http://${WSL_IP}:30080"
  success "   또는: http://localhost:30080"
  success "==================================================="
}

# --------------------------------------------------------------
# MAIN
# --------------------------------------------------------------
main() {
  echo ""
  echo "████████████████████████████████████████████████"
  echo "  MSA Travel Platform - k3s 배포 스크립트"
  echo "  WSL2 (Ubuntu) + k3s 전용"
  echo "████████████████████████████████████████████████"
  echo ""

  case "${1:-all}" in
    install)  install_k3s ;;
    build)    build_and_import_images ;;
    deploy)   deploy_manifests; check_status ;;
    status)   check_status ;;
    all)
      install_k3s
      wait_k3s_ready
      build_and_import_images
      deploy_manifests
      check_status
      ;;
    *)
      echo "사용법: $0 [all|install|build|deploy|status]"
      echo "  all     - 전체 설치 및 배포 (기본값)"
      echo "  install - k3s 설치만"
      echo "  build   - Docker 이미지 빌드 및 import만"
      echo "  deploy  - 매니페스트 배포만"
      echo "  status  - 현재 상태 확인"
      exit 1
      ;;
  esac
}

main "$@"
