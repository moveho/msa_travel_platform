# 📖 Wanderlust Cloud Native Project: Tech Stack & Chapter Map

이 문서는 프로젝트 **"Wanderlust"**와 관련 **"클라우드 네이티브 북-시나리오"** 전반에 걸쳐 사용되는 기술 스택을 정리한 표입니다.
각 기술이 어느 챕터에서 다루어지는지 참조(Reference)가 포함되어 있어, 전체 커리큘럼의 기술 분포를 한눈에 파악할 수 있습니다.

---

## 🏗️ Technology Stack Table

| **대분류 (Category)** | **기술 스택 (Tech Stack)** | **관련 챕터 (Reference)** | **역할 및 설명 (Role & Description)** |
| :--- | :--- | :--- | :--- |
| **Code**<br>*(App Development)* | **Python, FastAPI** | 1.3.1.2 | 마이크로서비스 애플리케이션 백엔드 개발 |
| | **HTML / JavaScript** | 1.3.1.2 | 프론트엔드 UI 개발 (Vanilla JS, ES6+) |
| | **Nginx** | 1.3.1.3 | API 게이트웨이, 정적 리소스 서빙, 리버스 프록시 |
| | **VS Code** | 1.3.1.2 | 통합 개발 환경 (IDE) |
| **Infrastructure**<br>*(Platform Environment)* | **Ubuntu 24.04** | 2.2.1 | 실습 베이스 운영체제 (Linux) |
| | **Docker (CE)** | 1.2.2, 2.2.1 | 컨테이너 런타임 및 이미지 관리 |
| | **WSL2** | 2.3.2 | Windows 환경에서의 리눅스 커널 서브시스템 |
| | **Amazon EKS** | 9.2 | AWS 매니지드 쿠버네티스 서비스 |
| **Orchestration**<br>*(Deployment)* | **Kubernetes (K8s)** | 2.3 | 컨테이너 오케스트레이션 및 클러스터 관리 |
| | **Kubespray** | 2.3.1 | 프로덕션 레벨 쿠버네티스 클러스터 자동 구축 |
| | **Kind** | 2.3.2 | 로컬 학습용 경량 쿠버네티스 클러스터 (Docker-in-Docker) |
| | **Karpenter** | 9.7.2 | AWS EKS를 위한 고성능 노드 오토스케일러 |
| **Networking**<br>*(Traffic & Mesh)* | **MetalLB** | 5.6.3 | 온프레미스/VM 환경을 위한 로드밸런서 구현체 |
| | **Traefik** | 5.6.4 | 쿠버네티스 인그레스(Ingress) 컨트롤러 |
| | **Istio** | 7.1, 9.4.2 | 엔터프라이즈급 서비스 메시 (트래픽 제어, 보안, 가시성) |
| | **Linkerd** | 7.1, 9.4.1 | 경량화된 초고속 서비스 메시 |
| **CI/CD**<br>*(Build & Release)* | **Git / GitHub** | 8.1 | 소스 코드 버전 관리 및 협업 저장소 |
| | **GitHub Actions** | 8.1 | 클라우드 기반 CI 자동화 (Docker 이미지 빌드/푸시) |
| | **Harbor** | 3.2.2 | 사설(Private) 컨테이너 이미지 레지스트리 |
| | **ArgoCD** | 8.2 ~ 8.4 | GitOps 방식의 쿠버네티스 지속적 배포(CD) 도구 |
| | **Jenkins** | 8.3, 9.5 | 파이프라인 기반의 전통적 CI/CD 자동화 서버 |
| | **GitLab** | 8.4 | 통합 DevOps 플랫폼 (저장소 + CI/CD) |
| | **SonarQube** | 8.5, 9.5 | 정적 코드 분석 및 품질/보안 취약점 점검 |
| **Data & Messaging**<br>*(Persistence)* | **MongoDB** | 1.3.1 | 스키마리스 여행 데이터를 위한 NoSQL 데이터베이스 |
| | **Apache Kafka** | 1.3.1 | 마이크로서비스 간 비동기 이벤트 스트리밍 |
| | **etcd** | 4.1.3 | 쿠버네티스 클러스터 상태 저장소 (Key-Value 스토어) |
| | **Amazon ECR** | 9.3 | AWS 관리형 컨테이너 레지스트리 |
| **Observability**<br>*(Monitoring & Logging)* | **Prometheus** | 7.2.1 | 시계열 데이터(메트릭) 수집 및 모니터링 시스템 |
| | **Grafana** | 7.2.1 | 메트릭 및 로그 데이터 시각화 대시보드 |
| | **EFK Stack** | 7.4 | 로그 수집/검색 (Elasticsearch + Fluentd + Kibana) |
| | **LGTM Stack** | 7.2.2 | 차세대 모니터링 (Loki + Grafana + Tempo + Mimir) |
| | **OpenTelemetry** | 7.2.3 | 벤더 중립적인 관측 가능성(Trace, Metric, Log) 표준 |
| | **Kubecost** | 9.8 | 쿠버네티스 리소스 비용 모니터링 및 최적화 (FinOps) |
| **Reliability**<br>*(Testing & Scaling)* | **nGrinder** | 7.3, 9.7 | 엔터프라이즈급 성능 부하 테스트 도구 (Java) |
| | **k6** | 7.3, 9.7 | 개발자 친화적인 성능 부하 테스트 도구 (Go/JS) |
| | **Chaos Engineering** | 9.7 | 시스템 복원력 테스트 (장애 주입 시뮬레이션) |
| | **KEDA** | 7.5, 9.7.3 | 쿠버네티스 이벤트 기반 오토스케일러 (Event-Driven Scaling) |
| **Management**<br>*(Tools)* | **K8s Dashboard** | 2.4.1 | 쿠버네티스 공식 웹 사용자 인터페이스 |
| | **Portainer** | 2.4.2 | 도커 및 쿠버네티스 관리를 위한 경량 관리 UI |
| | **k9s** | 2.4.2 | 터미널(CLI) 환경의 쿠버네티스 관리 도구 |
| | **Helm** | 2.4.1 | 쿠버네티스 애플리케이션 패키지 매니저 (차트) |
| **Security** | **Sealed-Secrets** | 5.5.2 | Git에 안전하게 커밋 가능한 암호화된 시크릿 관리 |

---
*Created automatically based on Book Scenario TOC v1.*
