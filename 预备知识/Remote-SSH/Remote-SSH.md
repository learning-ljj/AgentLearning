# 概述

## 参考资料

[概述](https://code.visualstudio.com/docs/remote/remote-overview)  
[VS Code 服务端深度解析](https://code.visualstudio.com/docs/remote/vscode-server)

**作用**：远程开发，保持每个人都在一致的环境中工作

## 工作原理

在远程系统上自动安装一个独立的 VS Code Server，让本地操作像在本地运行一样流畅

*   **代码隔离**：你的源代码、编译器和运行环境全部留在远程机器上，本地不需要下载任何源码，也不需要配置复杂的开发环境。
*   **指令透传**：你在本地按下的每一个快捷键、发起的每一个调试指令，都会通过安全隧道（如 SSH 或 Tunnels）发送给 **VS Code Server**。
*   **本地化体验**：远程服务端在目标机器上直接执行代码解析、搜索和调试，然后将结果传回本地。

### VS Code Server 的技术本质

VS Code Server 是独立于远程主机上已有 VS Code 安装的后端服务。即使远程机器没有安装 VS Code 桌面版，也能通过 SSH 或 Tunnels 自动下载并运行一个轻量级服务端。该服务包含：

- 完整的语言解析引擎和调试适配器
- 扩展宿主进程（Extension Host）
- 终端服务代理

本地 UI 与远程服务端之间通过 JSON-RPC 协议通信，所有敏感数据均加密传输。

## 核心架构：前后端分离

![architecture](./pics/architecture.png)

VS Code 将原本一体的编辑器拆分成了两个部分：客户端与服务端

*   **本地客户端 (VS Code Client)**：用户电脑上运行的界面。它只负责**显示 UI**（如菜单、侧边栏）和**接收你的输入**（敲代码、点按钮）。
*   **远程服务端 (VS Code Server)**：连接远程环境时，VS Code 会自动在目标机器（虚拟机、容器或 WSL）上安装这个轻量级的后端服务。

## 作用

*   **环境一致性**：开发环境与生产环境完全同步，避免了跨平台兼容性问题。
*   **性能释放**：本地轻量运行，重负载的编译和运算交给性能更强的远程服务器。
*   **即开即用**：新同事只需连接上远程环境即可开始开发，无需在自己机器上安装几十个依赖包。

## 统一入口：Remote Development 扩展包

VS Code 远程开发通过一个扩展包统一管理，包含四个扩展：

| 扩展 | 作用 | 适用场景 |
|:---|:---|:---|
| Remote - SSH | 通过 SSH 连接远程物理机或虚拟机 | 连接远程服务器、云主机 |
| Dev Containers | 在 Docker 容器内开发 | 隔离开发环境、统一团队配置 |
| WSL | 在 Windows 子系统上开发 | Windows 用户需要 Linux 工具链 |
| Remote - Tunnels | 通过安全隧道连接（无需 SSH） | 无法配置 SSH 或需要穿透防火墙 |

左下角状态栏图标显示当前连接状态（本地或远程），点击可快速切换。

# 连接流程

## SSH 连接

### 参考资料

[功能与配置指南](https://code.visualstudio.com/docs/remote/ssh)  
[实践教程](https://code.visualstudio.com/docs/remote/ssh-tutorial)

### SSH (Secure Shell) 的核心原理：加密的安全管道

**核心原理**：SSH 是一种在不安全网络上提供**安全远程登录**和**加密通信**的协议。

*   **非对称加密 (Keys)**：它使用“公钥+私钥”对。公钥像一把锁，留在服务器上；私钥像唯一能开锁的钥匙，留在你本地。
*   **身份验证**：连接时，服务器用“锁”发起挑战，只有持有“钥匙”的本地客户端能解开，从而证明你是合法用户。

**工作原理细节**：
- 系统生成一对数学相关的密钥：公钥和私钥。
- 公钥可以留在服务器上，即使泄露也无风险。
- 私钥严格保留在本地，不可公布。
- 用公钥加密的数据只能由对应私钥解密；反之亦然。
- 连接时，服务器用公钥发起挑战，只有持有私钥的本地客户端能解开，从而完成身份验证。

**常见配置**：在 `.ssh/config` 中定义主机别名、IP、用户及私钥路径。  
**常用操作**：**SSH 隧道/端口转发**。它能将远程服务器上原本不对外开放的端口（如 3000）“通过管道”映射到本地（localhost:3000），实现本地预览。

### 环境准备(Prerequisites)

1.  **本地**：安装支持 OpenSSH 的客户端。
2.  **远程主机**：
    *   内存建议 **2GB RAM** 及以上，至少 **1GB**。
    *   主流 Linux 发行版（Ubuntu 16.04+、CentOS 7+ 等）或 Windows 10/11（需开启 OpenSSH Server）。
3.  **插件安装**：在本地 VS Code 安装 `Remote - SSH` 扩展插件。

### 常见配置 (Key Configurations)

#### 快速连接与免密登录

*   **基本连接**：使用 `user@hostname` 格式，通过命令面板 (`F1`) 选择 `Remote-SSH: Connect to Host...`。
*   **推荐配置：SSH 密钥认证**
    *   在本地执行 `ssh-keygen -t ed25519 -C "your_email@example.com"` 生成密钥对。
    *   使用 `ssh-copy-id user@remote-host` 将公钥添加到服务器授权列表，或手动将公钥内容追加到远程服务器的 `~/.ssh/authorized_keys` 文件中，即可实现免密登录，避免反复输入密码。

#### SSH 配置文件管理 (SSH Config)

为了方便管理多个服务器，建议使用配置文件：
```ssh-config
Host my-server
    HostName 1.2.3.4
    User root
    IdentityFile ~/.ssh/id_ed25519

Host jump-host
    HostName 10.0.0.1
    User ubuntu

Host target-server
    HostName 172.16.0.50
    User admin
    ProxyJump jump-host
```

常用配置项说明：

| 配置项 | 含义 |
|:---|:---|
| `Host` | 自定义别名，连接时使用 `ssh my-server` |
| `HostName` | 实际 IP 地址或域名 |
| `User` | 登录用户名 |
| `Port` | SSH 端口（默认 22） |
| `IdentityFile` | 私钥文件路径 |
| `ProxyJump` | 通过跳板机连接目标主机 |

配置后，在 **Remote Explorer (远程资源管理器)** 侧边栏即可一键连接。

### 常见操作 (Core Operations)

#### 插件管理 (Extensions)

*   **分层安装**：主题类插件安装在本地；编程支持类（如 IntelliSense）需安装在**远程主机**上才能生效。
*   **自动同步**：你可以设置 `remote.SSH.defaultExtensions` 确保每次连接新服务器都自动装好必备工具。

#### 端口转发 (Port Forwarding)

*   **场景**：远程服务器跑了一个网页服务（如 localhost:3000），本地浏览器打不开。
*   **操作**：在 `Ports` 视图点击 `Forward a Port`，输入 3000。
*   **效果**：现在你在本地浏览器访问 `http://localhost:3000` 就能看到远程运行的网页。

#### 远程调试 (Debugging)

*   **无感体验**：直接在远程代码上点红点设置断点，按 `F5` 启动。
*   **功能全开**：支持查看变量、调用堆栈和单步执行，体验与本地完全一致。

#### 终端使用 (Terminal)

*   连接后，VS Code 的**集成终端**会自动切换到远程服务器的 Bash 或 PowerShell，你执行的所有命令都是直接作用于服务器的。

## WSL 连接

### 参考资料

[功能与配置指南](https://code.visualstudio.com/docs/remote/wsl)  
[实践教程](https://code.visualstudio.com/docs/remote/wsl-tutorial)

### WSL 核心原理：Windows 上的原生 Linux

WSL (Windows Subsystem for Linux) 允许 Windows 用户直接在 Windows 上运行一个真实的 Linux 内核环境。

**WSL 2 原理**：使用一个真正的 Linux 内核，运行在轻量级虚拟机中。与传统虚拟机不同，WSL 2 启动极快、资源占用低、动态分配内存，同时支持完整的 Linux 系统调用，兼容性远优于 WSL 1。

**WSL 1 vs WSL 2 对比**：

| 对比项 | WSL 1 | WSL 2 |
|:---|:---|:---|
| 内核 | 翻译层模拟 Linux 系统调用 | 真正的 Linux 内核运行在轻量级 VM 中 |
| 兼容性 | 部分 Linux 程序无法运行 | 接近完整的 Linux 兼容性 |
| 文件性能 | Windows 文件系统访问更快 | Linux 原生文件系统访问更快 |
| Docker 支持 | 需额外配置 | 原生支持 |

### 环境配置步骤

在开始之前，请确保完成以下基础设置：

*   **启用 WSL**：在 Windows 功能中勾选“适用于 Linux 的 Windows 子系统”或通过 PowerShell 命令 `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux` 启用，并重启电脑。
*   **安装 Linux 发行版**：从 Microsoft Store 下载并安装所需的 Distro（如 Ubuntu），并完成用户设置。
*   **安装软件与插件**：
    1.  在 **Windows 侧**安装 VS Code（安装时务必勾选 **“添加到 PATH”**）。
    2.  在 VS Code 中搜索并安装 **WSL 扩展**。
*   **检查状态**：安装后，VS Code 左下角会出现一个远程状态栏图标，点击即可查看 WSL 状态和相关命令。

### 常用操作指南

#### 快速启动与进入

*   **从终端进入**：在 WSL 终端中导航至项目目录，输入 `code .` 即可启动连接了该目录的 VS Code。
*   **从 VS Code 进入**：按 `F1` 调出命令面板，选择 **“WSL: Connect to WSL”**（连接默认分发版）或 **“WSL: Connect to WSL using Distro”**（选择特定版本）。

#### 插件管理

*   **安装位置**：插件分为两类。主题和代码片段等 UI 插件安装在本地；而编程语言支持（如 Python 插件）、调试工具等绝大多数开发插件，需要安装在 **WSL 侧** 才能生效。
*   **批量迁移**：可以通过扩展视图中的“Install Local Extensions in WSL”功能，快速将本地已有的插件同步到 WSL 环境。

#### 终端与调试

*   **集成终端**：连接 WSL 后，VS Code 内置的“新建终端”将自动启动 Linux Bash 运行环境。
*   **无缝调试**：你可以直接在代码中打断点并按 `F5` 运行。调试器会直接挂载到 WSL 中的进程，支持查看变量和堆栈，体验与本地开发一致。

### 进阶配置与注意事项

*   **远程专属设置**：你可以为 WSL 设置独立的配置。通过命令面板运行 **“Preferences: Open Remote Settings”**，这些设置会覆盖本地设置，仅在连接 WSL 时生效。
*   **Git 协作**：
    *   **换行符**：建议配置一致的换行符处理，避免跨平台协作冲突（推荐 `git config --global core.autocrlf input`）。
    *   **凭据共享**：可以配置 WSL 使用 Windows 的 Git 凭据管理器，避免反复输入密码。
*   **WSL 1 限制**：某些开发场景有已知限制，推荐升级到 WSL 2。
*   **Alpine Linux 注意**：因 `glibc` 依赖问题，某些 VS Code 扩展可能无法正常工作。

## 容器连接

### 参考资料

[功能与配置指南](https://code.visualstudio.com/docs/devcontainers/containers)  
[实践教程](https://code.visualstudio.com/docs/devcontainers/tutorial)

### Docker / Dev Containers核心原理：标准化的集装箱

**核心原理**：这是一种**操作系统层级的虚拟化**。它把代码运行所需的所有依赖（如特定版本的 Python、库文件）像货物一样打包进一个“集装箱”（容器）里。

*   **环境隔离**：容器与你的主机系统完全隔离，你在容器里把环境配乱了，也不会影响主机。
*   **一致性**：无论你在 Windows、Mac 还是云端，只要运行同一个容器镜像，开发环境就是 100% 相同的。

**常见配置**：通过 `devcontainer.json` 文件定义容器的镜像、安装的插件及运行权限。  
**常用操作**：**在 SSH 远程主机上运行容器**。VS Code 支持先连上 SSH 远程机，再在远程机里启动容器，实现“远程之上的隔离”。

#### Docker 三核心概念

| 概念 | 比喻 | 说明 |
|:---|:---|:---|
| **镜像 (Image)** | 食谱 / 模具 | 只读模板，包含运行应用所需的所有文件、依赖和配置 |
| **容器 (Container)** | 做好的菜 / 实例 | 镜像的运行实体，可启动、停止、删除，环境完全隔离 |
| **仓库 (Registry)** | 超市货架 | 存放和共享镜像的平台（如 Docker Hub） |

#### 为什么使用容器开发？

Dev Containers 的核心在于**环境隔离与一致性**。它不再直接在你的物理机（主机）上安装各种复杂的依赖，而是将整个开发环境“打包”进一个 Docker 容器中。

*   **客户端-服务器架构**：你的本地 VS Code 仅作为 UI 客户端，它会连接到运行在容器内部的 **VS Code Server**。
*   **工具与扩展本地化**：所有的编程语言工具（如 Node.js、Python）、库以及 VS Code 扩展（如代码补全、调试器）都直接安装并运行在容器内，拥有对容器文件系统的全权访问。
*   **源码挂载/克隆**：你可以将本地的文件夹“挂载”到容器中同步编辑，也可以直接将 GitHub 仓库克隆到独立的容器卷（Volume）中以获得更好的性能。

#### 源码挂载模式对比

| 模式 | 说明 | 适用场景 |
|:---|:---|:---|
| 挂载本地文件夹 | 直接挂载主机目录到容器 | 本地已有项目代码 |
| 克隆到容器卷 | 将仓库克隆到独立 Docker Volume | 大型项目，文件 I/O 性能最佳 |
| 克隆到容器内 | 直接在容器文件系统中克隆 | 完全隔离，不依赖主机文件 |

### 环境配置与准备

在使用之前，需要准备好以下“基础设施”：

*   **必备软件**：安装 Docker Desktop（确保它正在运行）和 VS Code。
*   **关键插件**：在 VS Code 中安装 **Dev Containers 扩展**。
*   **系统要求**：
    *   **Windows**：建议配合 **WSL 2** 后端使用以获得最佳性能。
    *   **资源**：远程主机建议至少拥有 2 GB RAM 和 2 核 CPU。

### 核心配置文件：`devcontainer.json`

这是远程开发的“说明书”，告诉 VS Code 如何构建和启动容器。它通常位于项目的 `.devcontainer/` 目录下。

**常见配置参数：**
*   **`image` / `dockerfile`**：指定基础镜像或 Dockerfile 路径（二选一）。
*   **`features`**：快速添加工具属性（如 Git、特定语言版本、Docker CLI）。
*   **`extensions`**：容器启动后自动安装的插件 ID 列表。
*   **`forwardPorts`**：将容器内的端口（如 Web 服务的 3000 端口）映射到本地，方便通过 `localhost` 访问。
*   **`postCreateCommand`**：容器创建后自动执行的命令（如 `npm install`）。
*   **`remoteSettings`**：仅在容器内生效的 VS Code 设置。
*   **`remoteUser`**：容器内使用的用户。

#### devcontainer.json 完整示例

```json
{
  "name": "Python Dev Environment",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:1": {}
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-azuretools.vscode-docker"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python"
      }
    }
  },
  "forwardPorts": [3000, 8080],
  "postCreateCommand": "pip install -r requirements.txt",
  "remoteUser": "vscode"
}
```

### 常见操作指南

*   **开启开发环境**：
    *   **已有项目**：使用命令 `Dev Containers: Open Folder in Container...`。
    *   **快速尝试**：使用 `Dev Containers: Try a Dev Container Sample...` 选择官方提供的代码示例（如 Node, Python）。
*   **终端与调试**：
    *   **集成终端**：点击“新建终端”，它会自动在容器环境下启动，无需额外配置。
    *   **调试**：按下 `F5` 即可在容器内启动调试，过程与本地开发完全一致。
*   **管理端口**：
    *   如果需要临时访问某个新端口，可在“远程资源管理器”或命令面板中使用 `Forward a Port` 命令。
*   **环境更新**：
    *   如果你修改了 `devcontainer.json`，需要执行 `Dev Containers: Rebuild Container` 重新构建容器以使配置生效。
*   **退出连接**：
    *   通过 `File > Close Remote Connection` 结束会话并回到本地开发模式。

### 注意事项与局限

*   **安全性**：VS Code 会要求你确认是否“信任”该工作区，以防止自动执行恶意代码。
*   **性能**：在 Windows/macOS 上，直接挂载本地文件可能会有性能损耗，建议对于大型项目使用“在卷中克隆仓库”模式。
*   **不支持的环境**：目前不支持 Windows 容器镜像，也不支持非官方的 Ubuntu Docker snap 包。

## 远程隧道连接

### 参考资料

[指南](https://code.visualstudio.com/docs/remote/tunnels)

### Tunnels (远程隧道)核心原理：穿透墙壁的桥梁

**核心原理**：这是一种**中继技术（Relay）**，主要解决“连不上”的问题。

*   **绕过限制**：传统的 SSH 需要远程机有公网 IP 且开启 22 端口。隧道技术则是由远程机**主动向外**连接到微软的云服务（中继站） [Source 1]。
*   **反向代理**：你连接中继站，中继站再把流量转给远程机。这样即使远程机躲在公司防火墙后面或没有公网 IP，你也能连上 [Source 1, 10]。

**常见配置**：使用 GitHub 或微软账号进行统一身份验证，无需记忆复杂的 IP 地址 [Source 1, 3]。  
**高复用操作**：**临时开发连接**。当你在咖啡厅想连家里的电脑，又不想配置复杂的路由器映射时，开启隧道是最快的方案。

Remote Tunnels 允许你通过安全隧道连接远程机器（如办公室电脑或虚拟机），而**无需配置 SSH 或修改防火墙设置**。

*   **架构设计**：采用“客户端-服务器”模式。VS Code 会在远程机器上安装 **VS Code Server**，所有的代码逻辑、插件运行和调试都在远程端完成，本地仅负责界面渲染。
*   **隧道技术**：数据通过微软的 **dev tunnels** 服务加密传输，提供端到端的 AES 256 加密。
*   **核心优势**：只要远程机器能联网，你就可以在任何地方通过 `vscode.dev`（网页版）或本地 VS Code 访问它，体验与本地开发无异。

#### 如何配置开启远程访问
你可以选择通过命令行或图形界面两种方式在**远程机器**上开启隧道：

*   **方式一：使用 `code` 命令行 (CLI)**
    1.  在远程机器下载并安装 `code` CLI。
    2.  运行命令：`code tunnel`。
    3.  按照提示登录 GitHub 或微软账号进行身份验证。
    4.  终端会输出一个类似 `https://vscode.dev/tunnel/<machine_name>` 的链接，直接打开即可开始工作。

    下载安装 CLI 的示例命令：
    ```bash
    curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' --output vscode_cli.tar.gz
    tar -xf vscode_cli.tar.gz
    ./code tunnel
    ```

*   **方式二：使用 VS Code 桌面版界面**
    1.  打开远程机器上的 VS Code。
    2.  点击左下角“账户”图标，选择 **“Turn on Remote Tunnel Access”**。
    3.  同样通过 GitHub/微软账号登录，随后即可通过生成的链接远程访问。

### 常见操作与进阶指南

*   **连接到现有隧道**：
    *   **网页端**：直接访问开启隧道时生成的 `vscode.dev` 链接。
    *   **客户端**：在本地安装 **Remote - Tunnels** 扩展，运行 `Remote Tunnels: Connect to Tunnel` 命令即可发现并连接已开启的机器。
*   **管理与清理**：
    *   **停止隧道**：在 CLI 中按 `Ctrl + C`，或在 UI 中选择 `Turn off Remote Tunnel Access`。
    *   **注销机器**：运行 `code tunnel unregister` 或在远程资源管理器中右键点击机器选择 **unregister**。
*   **保持连接不中断**：
    *   **设为系统服务**：运行 `code tunnel service install` 使其在后台持续运行。
    *   **防休眠**：使用 `code tunnel --no-sleep` 防止远程机器进入睡眠模式。
*   **组合技**：你可以通过隧道连接后，进一步结合 **Dev Containers** 或 **WSL** 扩展，在远程机器的容器或 Linux 子系统中进行开发。

### 使用限制与安全

*   **并发限制**：每个实例设计为仅供一名用户访问。
*   **数量限制**：每个账户目前最多支持注册 **10 个** 活动隧道。
*   **安全保障**：两端必须登录同一个账号才能建立连接，且 VS Code 不会开启任何网络监听端口，安全性极高。

## 技术特性对比

| 技术 | 解决的问题 | 核心内核 |
| :--- | :--- | :--- |
| **SSH** | 怎么**安全**地连过去？ | 加密通道 + 密钥认证 |
| **Docker** | 怎么保证**环境**不乱？ | 进程隔离 + 镜像打包 |
| **Tunnels** | 没公网 IP 怎么**穿透**？ | 云端中继 + 反向连接 |
| **WSL** | 如何在 Windows 上**原生运行 Linux**？ | 轻量级虚拟机 + 真正 Linux 内核 |

### 详细特性对比

| 对比项 | SSH | WSL | Dev Containers | Tunnels |
|:---|:---|:---|:---|:---|
| 连接前提 | 公网 IP / 端口开放 | 仅限 Windows | Docker 运行环境 | 仅需联网 |
| 环境隔离性 | 直接操作主机 | 子系统隔离 | 容器级别隔离 | 直接操作主机 |
| 环境一致性 | 依赖主机配置 | 依赖分发版 | 镜像保证完全一致 | 依赖主机配置 |
| 适用场景 | 云服务器、远程主机 | Windows 本地开发 | 团队协作、标准化 | 穿透内网、临时访问 |

# 补充资料

[实践：以 Azure 虚拟机为例](https://code.visualstudio.com/docs/remote/ssh-tutorial)

## 常用命令速查表

| 操作 | 命令 / 快捷方式 |
|:---|:---|
| 打开命令面板 | `F1` 或 `Ctrl+Shift+P` |
| 连接 SSH 主机 | `Remote-SSH: Connect to Host...` |
| 连接 WSL | `WSL: Connect to WSL` |
| 在容器中打开文件夹 | `Dev Containers: Open Folder in Container...` |
| 尝试容器示例 | `Dev Containers: Try a Dev Container Sample...` |
| 重建容器 | `Dev Containers: Rebuild Container` |
| 连接隧道 | `Remote Tunnels: Connect to Tunnel` |
| 打开远程设置 | `Preferences: Open Remote Settings (JSON)` |
| 关闭远程连接 | `File > Close Remote Connection` |

## 组合技：多重嵌套开发场景

VS Code 远程开发支持多种技术的组合使用，可以应对复杂的网络拓扑和隔离需求：

- **SSH + Dev Containers**：先通过 SSH 连接远程服务器，再在远程服务器上启动开发容器，实现“远程之上的隔离”。
- **Tunnels + Dev Containers**：通过隧道连接远程机后，进一步在远程机的容器中进行开发。
- **Tunnels + WSL**：通过隧道连接 Windows 机器后，进入其 WSL 环境开发。
- **SSH + WSL**：通过 SSH 连接 Windows 主机后，再进入该主机的 WSL 分发版进行开发。