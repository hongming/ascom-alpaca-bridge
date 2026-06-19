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
- 本地轻量 Web 状态页：`http://127.0.0.1:11111/`
- ASCOM 原生 Telescope Chooser
- 基础日志
- 普通命令行运行

### 第一版不包含

- Camera、Focuser、FilterWheel、Dome、Rotator、Switch 等其他设备
- 完整 Web 配置页面
- 用户身份验证
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

### `ascom_alpaca_bridge/web_routes.py`

职责：

- 提供无需身份验证的本地轻量 Web 页面：`/`
- 从已有 `/management/v1/configureddevices` 和设备 Alpaca endpoint 读取状态
- 展示 Telescope、Dome、Focuser 的设备编号、名称、连接状态和常用状态值
- 提供基础控制按钮：
  - 通用：Connect / Disconnect
  - Dome：SlewToAzimuth / OpenShutter / CloseShutter / AbortSlew
  - Focuser：Move / Halt / TempComp On / TempComp Off
- 当前目标是调试和现场确认设备状态，不替代 Alpaca Management API，也不承担公网安全管理职责

Web 页设计备忘：

- 暂时不加入用户身份验证，默认仅建议在可信本机或局域网使用。
- 若后续开放到不可信网络，需要补身份验证、访问控制和 HTTPS/反向代理部署说明。
- 页面保持零构建、零前端依赖，避免把轻量 bridge 变成复杂 Web 应用。

## GUI 产品边界和下一阶段剪裁计划

当前判断：

- 本项目的 GUI 应定位为 bridge 的本地启动、选驱动、连接和状态入口，不发展成完整拍摄软件。
- GUI 当前已加入 Telescope、Dome、Focuser、Camera 的关键控制按钮，适合测试期快速验证四类设备链路。
- `run_bridge_simple_gui.py` 作为推荐的简化 GUI：只保留 Choose、Start/Stop Bridge、Connect All、Disconnect All、Open Web、基础状态和驱动名称。
- `run_bridge_gui.py` 保留为调试期完整控制台，方便现场验证具体 endpoint。
- 先保留现状使用一段时间，基于真实使用频率再剪裁，而不是提前猜测哪些按钮有用。
- Web 页面继续作为详细状态、诊断和轻量控制兜底；默认用户可以不主动打开 Web。
- 外部拍摄软件继续负责真正观测流程，例如拍摄序列、保存目录、冷却计划、图像处理、完整 FITS 元数据等。

下一阶段 GUI 剪裁方向：

- 必留：Chooser、Start/Stop Bridge、Connect/Disconnect、基础连接状态。
- 可留：Open Web、Copy URL、少量高频且安全的现场按钮。
- 倾向移到 Web：slew、move、exposure、cooler、shutter、参数设置、图像下载。
- 不在 GUI 做：拍摄序列、复杂状态表、图像预览、设备高级参数配置。

目标：

- GUI 最终成为“设备接入和 bridge 运行入口”。
- Web 成为“诊断和控制兜底”。
- Alpaca HTTP 接口和外部天文拍摄软件负责主要业务工作流。

## Camera 分阶段实现计划

本地参考文件：

- `Camera Class — Alpyca_ API Library for ASCOM Alpaca 3.1.2 documentation.mhtml`

Camera 是当前设备类型里复杂度最高的一类，不能按 Telescope/Dome/Focuser 的方式一次性全量接入。主要风险来自：

- 曝光流程是异步状态机，需要通过 `CameraState`、`ImageReady`、`PercentCompleted` 轮询。
- 图像下载涉及 `ImageArray`、`ImageArrayRaw`、`ImageArrayInfo`，会遇到 COM 数组、像素类型、二维/三维维度、JSON 体积和客户端兼容性问题。
- 制冷和参数设置会直接影响硬件状态，需要在真实相机上谨慎回归。

### Phase C1：连接和状态读取

目标：让 Alpaca 客户端能发现 Camera、连接 Camera，并读取基础状态，用于真实硬件连通性测试。

范围：

- 配置段：`camera`
- ASCOM Camera Chooser：`--choose-camera` / `--choose-camera-only`
- Management configured devices 中上报 `DeviceType = Camera`
- `/status` 中上报 Camera 连接状态
- Web 首页显示 Camera 卡片
- HTTP endpoint：`/api/v1/camera/0/...`
- 支持连接：
  - `GET /connected`
  - `PUT /connected`
  - `PUT /connect`
  - `PUT /disconnect`
- 支持只读状态和能力：
  - 基础信息：`name`、`description`、`driverinfo`、`driverversion`、`interfaceversion`、`supportedactions`
  - 连接状态：`connected`、`connecting`、`devicestate`
  - 相机状态：`camerastate`、`imageready`、`percentcompleted`
  - 传感器信息：`cameraxsize`、`cameraysize`、`sensortype`、`sensorname`、`pixelsizex`、`pixelsizey`
  - 制冷/温度只读：`ccdtemperature`、`cooleron`、`coolerpower`、`heatsinktemperature`
  - 曝光能力：`exposuremin`、`exposuremax`、`exposureresolution`、`canabortexposure`、`canstopexposure`
  - 参数范围和当前值：`binx`、`biny`、`maxbinx`、`maxbiny`、`startx`、`starty`、`numx`、`numy`、`gain`、`gainmin`、`gainmax`、`gains`、`offset`、`offsetmin`、`offsetmax`、`offsets`、`readoutmode`、`readoutmodes`

明确不做：

- `ImageArray`
- `ImageArrayRaw`
- `ImageArrayInfo`
- FITS 保存或预览

### Phase C2：参数设置

状态：已实现基础 HTTP 写入，等待真实硬件回归。

范围：

- `BinX` / `BinY`
- `StartX` / `StartY`
- `NumX` / `NumY`
- `Gain`
- `Offset`
- `ReadoutMode`
- `FastReadout`
- `CoolerOn`
- `SetCCDTemperature`
- `SubExposureDuration`

验证重点：

- 不同相机驱动对 `Gain`/`Offset` 是数值模式还是名称列表索引模式。
- `CanFastReadout = False` 时写 `FastReadout` 的错误映射是否合理。
- `CanSetCCDTemperature = False` 或无制冷相机写 `SetCCDTemperature`/`CoolerOn` 的错误映射是否合理。
- ROI 设置顺序是否需要客户端先设 `StartX/StartY` 再设 `NumX/NumY`，或反过来。

### Phase C3：曝光控制

状态：已实现基础曝光控制，等待真实硬件回归；暂不返回图像数组。

- `PUT /startexposure`
- `PUT /stopexposure`
- `PUT /abortexposure`
- 通过 `CameraState`、`ImageReady`、`PercentCompleted` 验证状态变化

验证重点：

- `StartExposure(Duration, Light)` 是否立即返回，且 `ImageReady` 先变为 false。
- 曝光过程中 `CameraState` / `PercentCompleted` 是否符合驱动行为。
- `StopExposure` 和 `AbortExposure` 在不支持时的错误映射是否合理。
- Dark/Light 参数在真实驱动上是否被正确接收。

### Phase C4：图像下载

状态：已实现基础 JSON 图像下载，等待真实硬件小 ROI 回归。

- `GET /imagearray`
- `GET /imagearrayinfo`
- `GET /imagearrayraw`

重点验证：

- COM SAFEARRAY 到 JSON 的转换
- 单色与彩色相机维度差异
- 大图像响应时间和内存占用
- 主流客户端是否接受返回格式
- `ImageArrayRaw` 在传统 ASCOM COM 驱动上可能不存在；当前实现会退回 `ImageArray`。
- `ImageArrayInfo` 在传统 ASCOM COM 驱动上可能不存在；当前实现会在首次成功下载图像后，根据返回数组推导并缓存元数据。在下载图像前返回 `Value = null`。
- `ImageArray` 只有在曝光完成且 `ImageReady = true` 后才有效；否则真实驱动可能返回 “There is no image available”。
- 真实硬件首次测试建议使用短曝光、小 ROI 或高 binning，避免一次性返回大图导致 HTTP 响应和内存压力过大。

### Phase C4.5：保存测试图像

状态：已实现桥接器辅助 PNG 预览/下载，等待真实相机回归。

- `GET /imagearray.png`
- Web 管理页 Camera 卡片加入 `Preview PNG` 和 `Download PNG`
- PNG 使用最新可用 `ImageArray`，转换为 8-bit 灰度并自动拉伸
- 当前使用 1% / 99% 百分位做自动拉伸，减少热像素或极端值对预览的影响

验证重点：

- 曝光完成且 `ImageReady = true` 后，Web 预览能显示 PNG。
- Windows 浏览器下载文件名是否正常，图像方向是否符合相机/驱动预期。
- 大图下载时页面是否卡顿；真实硬件首次测试仍建议小 ROI 或高 binning。
- 该接口是本桥接器的轻量测试辅助接口，不属于官方 Alpaca Camera 标准成员。

### Phase C5：Web 页增强

- Camera 卡片显示曝光状态、温度、制冷、ImageReady：已实现
- 加入短曝光测试按钮：已实现
- 加入 PNG 预览和下载按钮：已实现

### Phase C5.5：一键曝光并自动预览

状态：已实现 Web 端轻量流程编排，等待真实相机回归。

- Camera 卡片加入 `Expose + Preview`
- 浏览器端顺序执行：
  - `PUT /startexposure`
  - 轮询 `GET /imageready`
  - 同步读取 `GET /percentcompleted` 和 `GET /camerastate` 显示进度
  - 曝光完成后刷新状态并加载 `GET /imagearray.png`
- 当前超时时间为 120 秒，适合短曝光测试；长曝光后续可再做可配置项。
- 该阶段不新增官方 Alpaca 标准接口，只是 Web 管理页辅助测试流程。

验证重点：

- ASCOM Simulator 和真实相机在 `ImageReady` 变为 true 后，`imagearray.png` 是否立即可取。
- 曝光过程中 `PercentCompleted` 是否可读；不可读时页面应继续等待而不是失败。
- 长曝光或驱动卡住时，120 秒超时提示是否清晰。

### Phase C6：FITS 测试下载

状态：已实现桥接器辅助 FITS 下载，等待真实相机回归。

- `GET /imagearray.fits`
- Web 管理页 Camera 卡片加入 `Download FITS`
- FITS 保存未拉伸的线性像素值；PNG 仍用于自动拉伸预览
- 当前轻量实现生成 FITS Primary HDU，不引入 Astropy 等额外依赖
- 0-65535 像素使用 `BITPIX = 16` + `BZERO = 32768` 的 unsigned 16-bit FITS 约定
- 彩色或多通道像素当前先转为亮度平面保存；后续可扩展为多平面 FITS

验证重点：

- 真实相机完成曝光后，`Download FITS` 能生成可被常见 FITS 查看器打开的文件。
- 像素方向、宽高是否符合预期。
- 16-bit 相机的黑场、亮场数值范围是否合理，没有被 PNG 自动拉伸逻辑影响。
- 大图 FITS 下载时 HTTP 响应时间和内存占用是否可接受。
- 该接口是本桥接器的轻量测试辅助接口，不属于官方 Alpaca Camera 标准成员。

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

## 当前 GUI / Bridge 工作流备忘

- Bridge 启动只应该启动 HTTP/Alpaca 服务和 discovery，不应该因为 GUI 状态轮询而加载或连接 ASCOM 设备。
- 设备连接应由用户显式触发；配置里的 `auto_connect` 默认为 `false`，只有用户明确打开时才在服务启动时自动连接。
- `/status` 用于轻量级健康检查和 GUI 状态显示。未初始化的 ASCOM driver 应显示为 `Disconnected`，不能为了读取 `Connected` 而创建 COM driver。
- Simple GUI 不再推荐一键连接全部设备。真实设备里 Camera、Mount、Dome 等初始化耗时差异很大，应提供每个设备独立的 `Connect` / `Disconnect`，避免一个慢设备拖住整个工作流。
- `Start Bridge` 慢时优先排查：是否执行了 `auto_connect`、是否状态轮询触发了 COM 初始化、是否端口上已有旧 bridge、是否 Windows ASCOM driver 自身在初始化时弹窗或等待硬件。
- Web UI 的按钮操作也应遵循“局部操作、局部刷新”。点击某个设备的 Connect/Disconnect 或参数按钮后，只刷新当前设备卡片，不全量读取所有设备，避免一个设备的慢响应或异常影响其他设备。
- Camera `StartExposure` 可能在部分 ASCOM 驱动里同步阻塞；Bridge 应将其作为长操作处理，HTTP 立即返回，曝光完成由 `ImageReady`/`CameraState` 轮询判断。
- ASCOM COM 对象有线程亲和性。每个设备 driver 必须在自己的固定 worker 线程里创建并调用；后台任务只能把请求投递给该 worker，不能直接在临时线程里调用 COM 方法。
- Camera `ImageArray` / PNG / FITS 下载可能耗时很久。相关 route 不能在 FastAPI event loop 中同步执行，应作为同步 route 交给线程池，保证 GUI 的 `/status` 心跳继续响应。
- Web 预览图片时只能请求一次 PNG。不要先 `fetch` 校验再把 `<img src>` 指向同一 URL，否则会触发两次耗时的 `ImageArray` 读取。应使用 fetched blob 的 object URL 显示图片。
- GUI 心跳应容忍短暂 `/status` 超时。图像下载或厂商驱动忙碌时，不能因一次状态请求失败就把所有设备清成 `Unknown` 或把 Bridge 判为 `Starting`。
- PNG 预览可裁掉纯黑/空白边框，改善部分相机/模拟器返回“全幅黑画布 + 左上角有效图像”的显示效果；原始 `ImageArray` 和 FITS 不应因此被裁剪。
- SharpCap 等客户端不接受 `ImageArrayInfo.ImageElementType = Unknown(0)`。Bridge 不能原样透传底层 ASCOM driver 的 Unknown 类型，应从最近图像推导，或用 `Int32` 作为兼容兜底，并补齐有效维度。
- SharpCap/ASCOM Remote 类客户端可能优先请求 `Accept: application/imagebytes`。Bridge 应在 `/imagearray` 支持 `application/imagebytes` 二进制响应，避免客户端被迫走更挑剔、更慢的 JSON 图像数组路径。
- SharpCap 不支持 imagebytes 中 `ImageElementType=Int16` 且 `TransmissionElementType=Int32` 这种组合。Bridge 的 imagebytes 响应应让输出类型和传输类型一致：整数统一 `Int32/Int32`，浮点统一 `Double/Double`，并按该类型实际打包 payload。
- Web PNG 预览可以裁剪黑边，但 SharpCap imagebytes 不能裁剪到任意尺寸。SharpCap 会按 `CameraXSize/CameraYSize`、`NumX/NumY` 或 ROI 属性预分配帧缓冲。Bridge 应尽量让这些属性和实际 `ImageArray` / `ImageArrayInfo` 尺寸一致，而不是硬缩放图像去迎合错误的声明尺寸。
- ASCOM COM/RPC 掉线类错误，例如 `RPC 服务器不可用` / `0x800706BA`，应显示为设备不可用或未连接，不应在 Web UI 中反复展示大段原始 COM 异常。
