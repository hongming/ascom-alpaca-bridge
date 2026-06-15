# Python ASCOM Telescope 转 Alpaca Bridge 计划

## 目标

构建一个轻量级、仅 Windows 可用的 Python 服务，将本机的一个 ASCOM Telescope 驱动暴露为 ASCOM Alpaca Telescope 设备，供其他软件通过 HTTP 访问。

这个项目的目标不是完整复刻 ASCOM Remote Server，而是在只需要 Telescope 的场景下，用一个更小、更容易控制的脚本替代它。

仍然需要依赖：

- Windows
- ASCOM Platform
- 望远镜厂商驱动或 ASCOM Telescope Simulator
- Python 依赖，例如 `pywin32`

## 可行性结论

只做 Telescope 是可行的，难度明显低于完整 ASCOM Remote。

原因：

1. Telescope 的 Alpaca API 主要是属性读取、属性设置和少量动作方法。
2. 不需要处理 Camera 图像数组、大文件传输、位深、格式转换和内存压力。
3. 不需要多设备管理和复杂 Web 配置页面。
4. Python 可以通过 COM 直接调用 ASCOM Telescope 驱动。
5. FastAPI 可以很容易暴露 Alpaca 风格的 HTTP API。

主要复杂点不是调用 ASCOM 本身，而是 Alpaca 兼容性：

- 标准响应 envelope
- `ClientTransactionID` / `ServerTransactionID`
- Alpaca discovery
- 错误码和异常映射
- 不同客户端对 Telescope endpoint 的覆盖程度
- ASCOM COM 线程和并发访问

## 推荐范围

### 第一版包含

- 单个 Telescope 设备
- 可配置 ASCOM ProgID，例如 `ASCOM.Simulator.Telescope`
- Alpaca HTTP API：`/api/v1/telescope/0/...`
- Alpaca management endpoints
- Alpaca UDP discovery
- ASCOM 原生 Telescope Chooser
- 基础日志
- 普通命令行运行

### 第一版不包含

- Camera、Focuser、FilterWheel、Dome、Rotator、Switch 等其他设备
- Web 配置页面
- 多设备托管
- 完整 ASCOM Remote feature parity
- HTTPS
- Windows Service

## 技术选型

- Python 3.11+
- `pywin32`：调用 ASCOM COM 驱动
- `FastAPI`：HTTP API
- `uvicorn`：HTTP server
- `PyYAML`：读取配置
- `threading.RLock`：保护 COM 调用
- `socket` / `threading`：Alpaca UDP discovery

## 配置示例

```yaml
server:
  host: "0.0.0.0"
  port: 11111
  discovery_port: 32227
  server_name: "Python ASCOM Telescope Bridge"
  manufacturer: "Local Python Bridge"
  manufacturer_version: "0.1.0"
  location: "Local Windows host"

telescope:
  device_number: 0
  prog_id: "ASCOM.Simulator.Telescope"
  display_name: "ASCOM Telescope"
  unique_id: "python-ascom-telescope-0"
  auto_connect: false
```

## 架构

```text
Alpaca Client
    |
    | HTTP / UDP discovery
    v
Python Bridge
    |
    | pywin32 COM
    v
ASCOM Telescope Driver
    |
    v
赤道仪 / 望远镜 / ASCOM Simulator
```

## 核心模块

### `ascom_alpaca_bridge/ascom_driver.py`

职责：

- 根据 ProgID 创建 COM driver
- 持有单个 Telescope COM 对象
- 用锁保护 COM 调用
- 将 COM 异常转换成 bridge 内部异常
- 提供属性读写和方法调用辅助函数

### `ascom_alpaca_bridge/alpaca_response.py`

职责：

- 生成 Alpaca 标准 JSON 响应
- 回传 `ClientTransactionID`
- 递增 `ServerTransactionID`
- 统一返回 `ErrorNumber` 和 `ErrorMessage`

### `ascom_alpaca_bridge/telescope_routes.py`

职责：

- 实现 Telescope HTTP endpoints
- 将 GET endpoint 映射到 ASCOM 属性
- 将 PUT endpoint 映射到 ASCOM 属性设置或方法调用
- 做参数解析和基本校验

### `ascom_alpaca_bridge/discovery.py`

职责：

- 监听 Alpaca discovery UDP 端口，默认 `32227`
- 收到 discovery 请求后返回当前 HTTP 服务端口

### `ascom_alpaca_bridge/management_routes.py`

职责：

- 实现常用 Alpaca management endpoints：
  - `/management/apiversions`
  - `/management/v1/description`
  - `/management/v1/configureddevices`

## 最小 Telescope API

第一版优先实现常见客户端最可能调用的 Telescope endpoint。

## 官方 Telescope API 覆盖计划

目标是逐步覆盖 ASCOM Alpaca 官方 Telescope 章节中会用到的 endpoint。当前策略是先保证真实客户端与硬件链路稳定，再按官方 API 逐项补齐和回归。

官方文档入口：

- https://ascom-standards.org/alpyca/alpaca.telescope.html

本地参考文件：

- `Telescope Class — Alpyca_ API Library for ASCOM Alpaca 3.1.2 documentation.mhtml`

从本地 MHTML 提取到官方 Telescope 成员共 80 个。当前实现已补齐基础路由覆盖，后续重点转为逐项语义核对、参数格式核对和真实硬件回归。

### 官方成员覆盖快照

已覆盖基础路由的成员：

- `AbortSlew`
- `Action`
- `AlignmentMode`
- `Altitude`
- `ApertureArea`
- `ApertureDiameter`
- `AtHome`
- `AtPark`
- `AxisRates`
- `Azimuth`
- `CanFindHome`
- `CanMoveAxis`
- `CanPark`
- `CanPulseGuide`
- `CanSetDeclinationRate`
- `CanSetGuideRates`
- `CanSetPark`
- `CanSetPierSide`
- `CanSetRightAscensionRate`
- `CanSetTracking`
- `CanSlew`
- `CanSlewAltAz`
- `CanSlewAltAzAsync`
- `CanSlewAsync`
- `CanSync`
- `CanSyncAltAz`
- `CanUnpark`
- `CommandBlind`
- `CommandBool`
- `CommandString`
- `Connect`
- `Connected`
- `Connecting`
- `Declination`
- `DeclinationRate`
- `Description`
- `DestinationSideOfPier`
- `DeviceState`
- `Disconnect`
- `DoesRefraction`
- `DriverInfo`
- `DriverVersion`
- `EquatorialSystem`
- `FindHome`
- `FocalLength`
- `GuideRateDeclination`
- `GuideRateRightAscension`
- `InterfaceVersion`
- `IsPulseGuiding`
- `MoveAxis`
- `Name`
- `Park`
- `PulseGuide`
- `RightAscension`
- `RightAscensionRate`
- `SetPark`
- `SideOfPier`
- `SiderealTime`
- `SiteElevation`
- `SiteLatitude`
- `SiteLongitude`
- `SlewSettleTime`
- `SlewToAltAz`
- `SlewToAltAzAsync`
- `SlewToCoordinates`
- `SlewToCoordinatesAsync`
- `SlewToTarget`
- `SlewToTargetAsync`
- `Slewing`
- `SupportedActions`
- `SyncToAltAz`
- `SyncToCoordinates`
- `SyncToTarget`
- `TargetDeclination`
- `TargetRightAscension`
- `Tracking`
- `TrackingRate`
- `TrackingRates`
- `UTCDate`
- `Unpark`

需要重点核对的兼容点：

- `Connect` / `Disconnect`：当前映射到 `Connected = true/false`，后续确认目标客户端是否期望 Platform 7 异步连接语义。
- `Connecting`：传统 ASCOM COM 驱动可能没有该属性，当前 fallback 为 `false`。
- `DeviceState`：不同 ASCOM 驱动支持程度不一，后续需要在真实驱动上确认返回结构能否 JSON 化。
- `AxisRates` / `TrackingRates`：COM collection 的结构在不同驱动上可能不同，需要真实驱动回归。
- `SlewToTarget*` / `SyncToTarget`：依赖 `TargetRightAscension` 和 `TargetDeclination` 先被客户端正确设置。

### 验证分层

补齐官方 Telescope endpoint 后，验证分三层进行：

1. 路由层验证：所有官方成员都有 HTTP route，返回 Alpaca envelope，不出现 404。
2. 驱动层验证：通过 ASCOM COM 调用真实驱动，确认该驱动对成员的支持情况。
3. 硬件层验证：对会移动设备或改变状态的 endpoint 做安全环境下的真实动作测试。

从理论上，官方 Telescope 文档列出的成员都可以通过 HTTP/curl 访问本 bridge。但实际返回是否 `ErrorNumber = 0`，取决于：

- ASCOM driver 是否实现对应属性或方法。
- Telescope 是否已经连接。
- 当前状态是否允许该动作，例如 park/unpark/slew。
- 硬件是否支持该能力，例如 `CanFindHome`、`CanPulseGuide`、`CanMoveAxis`。
- 对 collection 型返回值的 JSON 化是否适配该驱动，例如 `AxisRates`、`TrackingRates`、`DeviceState`。

安全验证工具：

- `scripts/probe_telescope_endpoints.py`：默认只探测安全 GET endpoint。
- `--include-axis`：额外探测 `CanMoveAxis` 和 `AxisRates`。
- `--include-actions`：探测部分动作类 endpoint，仅能在模拟器或确认安全的硬件环境中使用。
- `--include-park-actions`：单独探测 `Park` / `Unpark`，这些动作可能长时间阻塞或移动设备，建议配合较长 `--timeout`。

### P0：硬件联调优先 endpoint

以下 endpoint 是近期优先项。当前代码已经有基础实现，但需要继续做官方语义核对、真实硬件回归和异常场景处理。

- `GET /api/v1/telescope/0/tracking`
- `PUT /api/v1/telescope/0/tracking`
- `GET /api/v1/telescope/0/slewing`
- `PUT /api/v1/telescope/0/park`
- `PUT /api/v1/telescope/0/unpark`
- `PUT /api/v1/telescope/0/slewtocoordinatesasync`
- `PUT /api/v1/telescope/0/findhome`

验收重点：

- `tracking`：读写都能正确映射 ASCOM `Tracking`，不支持时返回 Alpaca 错误而不是 500。
- `slewing`：异步 slew 后能被客户端轮询到状态变化。
- `park` / `unpark`：驱动支持时能正确执行；驱动不支持或已在目标状态时错误信息清晰。
- `slewtocoordinatesasync`：参数 `RightAscension` / `Declination` 解析正确，调用后立即返回，后续由 `slewing` 轮询状态。
- `findhome`：驱动支持时正确执行；不支持时依赖 `CanFindHome` 和 Alpaca 错误反馈。

### P1：继续补齐的官方 Telescope endpoint

- `AbortSlew`
- `SlewToCoordinates`
- `SlewToAltAz`
- `SlewToAltAzAsync`
- `SyncToCoordinates`
- `SyncToAltAz`
- `MoveAxis`
- `PulseGuide`
- `SetPark`
- `DestinationSideOfPier`
- `AxisRates`
- `CanMoveAxis`
- `Action`
- `CommandBlind`
- `CommandBool`
- `CommandString`

### P2：完整性和兼容性

- 官方 Telescope 所有只读属性逐项核对。
- 官方 Telescope 所有可写属性逐项核对。
- 参数大小写兼容。
- Form body 与 query 参数兼容策略。
- Alpaca 错误码映射进一步收敛。
- 针对不同 ASCOM driver 的 unsupported / not implemented 行为做兼容。

### 基础信息

- `GET /api/v1/telescope/0/name`
- `GET /api/v1/telescope/0/description`
- `GET /api/v1/telescope/0/driverinfo`
- `GET /api/v1/telescope/0/driverversion`
- `GET /api/v1/telescope/0/interfaceversion`
- `GET /api/v1/telescope/0/supportedactions`

### 连接

- `GET /api/v1/telescope/0/connected`
- `PUT /api/v1/telescope/0/connected`

### 坐标和状态

- `GET /api/v1/telescope/0/rightascension`
- `GET /api/v1/telescope/0/declination`
- `GET /api/v1/telescope/0/altitude`
- `GET /api/v1/telescope/0/azimuth`
- `GET /api/v1/telescope/0/siderealtime`
- `GET /api/v1/telescope/0/tracking`
- `PUT /api/v1/telescope/0/tracking`
- `GET /api/v1/telescope/0/slewing`
- `GET /api/v1/telescope/0/atpark`
- `GET /api/v1/telescope/0/athome`

### 能力查询

- `GET /api/v1/telescope/0/canfindhome`
- `GET /api/v1/telescope/0/canpark`
- `GET /api/v1/telescope/0/canpulseguide`
- `GET /api/v1/telescope/0/cansetdeclinationrate`
- `GET /api/v1/telescope/0/cansetguiderates`
- `GET /api/v1/telescope/0/cansetpark`
- `GET /api/v1/telescope/0/cansetpierside`
- `GET /api/v1/telescope/0/cansetrightascensionrate`
- `GET /api/v1/telescope/0/cansettracking`
- `GET /api/v1/telescope/0/canslew`
- `GET /api/v1/telescope/0/canslewaltaz`
- `GET /api/v1/telescope/0/canslewaltazasync`
- `GET /api/v1/telescope/0/canslewasync`
- `GET /api/v1/telescope/0/cansync`
- `GET /api/v1/telescope/0/cansyncaltaz`
- `GET /api/v1/telescope/0/canunpark`
- `GET /api/v1/telescope/0/canmoveaxis?Axis=0`
- `GET /api/v1/telescope/0/axisrates?Axis=0`

### 控制动作

- `PUT /api/v1/telescope/0/slewtocoordinates`
- `PUT /api/v1/telescope/0/slewtocoordinatesasync`
- `PUT /api/v1/telescope/0/slewtoaltaz`
- `PUT /api/v1/telescope/0/slewtoaltazasync`
- `PUT /api/v1/telescope/0/abortslew`
- `PUT /api/v1/telescope/0/synctocoordinates`
- `PUT /api/v1/telescope/0/synctoaltaz`
- `PUT /api/v1/telescope/0/park`
- `PUT /api/v1/telescope/0/unpark`
- `PUT /api/v1/telescope/0/findhome`
- `PUT /api/v1/telescope/0/moveaxis`
- `PUT /api/v1/telescope/0/pulseguide`
- `PUT /api/v1/telescope/0/setpark`
- `PUT /api/v1/telescope/0/destinationsideofpier`

## 后续可补充 API

等真实客户端联调后，再按需要继续补充：

- EquatorialSystem
- 更完整的 `Action` / `Command*` 兼容
- 更完整的错误码映射

## 实施阶段

### Phase 1：ASCOM COM PoC

- 用 Python 创建 `ASCOM.Simulator.Telescope`
- 读取 `Connected`、`Name`、`RightAscension`、`Declination`
- 设置 `Connected`
- 调用 `ASCOM.Utilities.Chooser` 弹出原生 Telescope Chooser
- 将用户选择的 ProgID 写入 `config.yaml`
- 在目标 Windows 机器上确认 COM 调用正常

验收标准：

- 可以连接 ASCOM Telescope Simulator 或真实赤道仪驱动
- 可以通过原生 Chooser 选择 Telescope
- 基础属性读取稳定
- 没有明显 COM 线程错误

### Phase 2：最小 Alpaca HTTP 服务

- 创建 FastAPI app
- 实现 Alpaca response envelope
- 实现 management endpoints
- 实现 `connected`、`name`、`rightascension`、`declination`、`tracking`、`slewing`

验收标准：

- 可以通过浏览器或 `curl` 调用 endpoint
- JSON 结构符合 Alpaca 常见客户端预期

### Phase 3：Alpaca Discovery

- 实现 UDP discovery listener
- 收到 discovery 请求后返回 HTTP 服务端口
- 用 discovery 工具或真实客户端验证设备可见

验收标准：

- 客户端可以发现 Python bridge

### Phase 4：核心 Telescope 控制

- 实现 `can*` 能力查询
- 实现 slew、sync、park、unpark、findhome、abortslew
- 加入参数校验和异常映射

验收标准：

- 目标软件可以连接 Telescope 设备
- 可以完成真实工作流所需的动作

### Phase 5：健壮性

- 加入结构化日志
- 加入配置文件读取
- 加入优雅退出
- 所有 COM 调用加锁
- 启动时检查 ASCOM Platform / ProgID 可用性
- 优化异常和错误码

验收标准：

- 可以支撑一次完整观测会话
- 异常时日志足够定位问题

### Phase 6：打包

- 添加 `requirements.txt` 或 `pyproject.toml`
- 添加 Windows 启动脚本
- 可选：用 PyInstaller 打包 exe
- 可选：增加 Windows Service 支持

验收标准：

- 非开发用户也可以在望远镜控制机上启动 bridge

## 风险评估

### 低风险

- 读取 Telescope 属性
- 设置 `Connected`
- 基础 HTTP route 映射
- Alpaca response envelope

### 中风险

- 不同客户端对 discovery 的兼容性
- ASCOM driver 的 COM 线程行为
- 长时间 slew 和客户端轮询
- 不支持能力的正确处理
- Alpaca 错误码兼容性

### 较高风险

- 个别厂商驱动和 Simulator 行为差异较大
- 客户端依赖冷门 Telescope endpoint
- 作为 Windows Service 运行时，驱动弹窗或桌面交互不可用

## 验证策略

1. 先用 ASCOM Telescope Simulator 测试。
2. 用浏览器或 `curl` 测试 HTTP endpoints。
3. 用 Alpaca discovery 工具测试发现能力。
4. 用目标客户端软件测试连接和控制。
5. 换成真实赤道仪 ASCOM driver 测试。
6. 做长时间空闲运行测试。
7. 做完整 connect、slew、sync、park、disconnect 流程测试。

## 建议的第一个里程碑

先做一个最小可运行 bridge，包含：

- Discovery
- Management endpoints
- `connected`
- `name`
- `description`
- `driverinfo`
- `interfaceversion`
- `rightascension`
- `declination`
- `altitude`
- `azimuth`
- `tracking`
- `slewing`
- `slewtocoordinatesasync`
- `abortslew`
- `park`
- `unpark`
- 常用 `can*` endpoints

这个里程碑的目的不是一次性覆盖完整 Telescope API，而是尽快验证目标软件是否能把 Python bridge 当成 Alpaca Telescope 使用。

## 最终建议

继续推进 Telescope-only Python bridge。

这个范围足够小，适合快速实现和联调。真正的不确定性不是 Python 能不能做 ASCOM 到 Alpaca 的转换，而是目标客户端具体会调用哪些 Alpaca Telescope endpoints。应尽快用 Simulator 跑通第一版，再立即接入真实客户端，避免实现不必要的接口。
