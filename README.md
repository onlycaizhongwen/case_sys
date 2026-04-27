# case_sys

币安合约多周期推荐系统，支持：

- 看涨 / 看跌 双方向推荐
- 长线 `1d` / 中期 `4h` / 短期 `1h` 三套策略
- 每小时自动执行一次分析
- 本地 Web 仪表盘展示最新推荐结果

## 目录说明

- `binance_day_contract_realtime_v5.py`
  主分析脚本，负责拉取行情、识别 MA7/MA10 交叉、生成推荐结果。
- `coin_recommendation_dashboard.py`
  仪表盘服务，负责定时调度分析并提供前端页面和接口。
- `web/`
  仪表盘前端页面。
- `docs/codex/v1/`
  项目需求、设计、计划等过程文档。

## 输出隔离规则

为避免测试结果覆盖正式页面，当前已经拆分为三套独立输出：

- `outputs/dashboard`
  正式仪表盘输出目录，8011 页面只读取这里。
- `outputs/sandbox`
  临时验证输出目录，适合快速排查和试跑。
- `outputs/manual`
  手工直接运行主脚本时的默认输出目录。

## 配置文件

- `dashboard_runtime_config.json`
  正式仪表盘配置，默认 `candidate_limit=200`
- `sandbox_runtime_config.json`
  临时验证配置，默认 `candidate_limit=20`
- `coin_recommendation_config.example.json`
  手工运行示例配置

## 常用命令

### 1. 启动正式仪表盘

```powershell
powershell -ExecutionPolicy Bypass -File .\start_dashboard.ps1
```

访问地址：

```text
http://127.0.0.1:8011/
```

### 2. 运行一版临时验证

```powershell
powershell -ExecutionPolicy Bypass -File .\run_analysis_sandbox.ps1
```

输出目录：

```text
outputs/sandbox
```

### 3. 手工完整运行主脚本

```powershell
powershell -ExecutionPolicy Bypass -File .\run_analysis_manual.ps1
```

输出目录：

```text
outputs/manual
```

## Git 使用

首次推送后，后续常用命令如下：

```bash
git status
git add .
git commit -m "your message"
git push
```

## 说明

- 仪表盘默认每 `3600` 秒自动执行一次分析。
- 页面会持续展示 `outputs/dashboard` 中最新一次正式结果。
- 临时验证和手工运行不会再覆盖正式仪表盘数据。
