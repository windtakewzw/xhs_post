# 素材配置

向 Claude 说"按 docs/install/02-materials.md 配置素材"。

素材存储在阿里云 OSS，通过 Rclone + Winfsp 挂载到本地。本项目只读取，不写入。

## 步骤 1：下载并安装 Rclone

```bash
# 下载 winfsp（Rclone 依赖）
curl -L -o "$TEMP/winfsp.msi" https://github.com/winfsp/winfsp/releases/download/v1.12.22339/winfsp-1.12.22339.msi
msiexec /i "$TEMP/winfsp.msi" /quiet

# 下载 Rclone
curl -L -o "$TEMP/rclone.zip" https://downloads.rclone.org/v1.60.1/rclone-v1.60.1-windows-amd64.zip
unzip "$TEMP/rclone.zip" -d "$TEMP/rclone_tmp"
mkdir -p "$USERPROFILE/tools/rclone"
cp -r "$TEMP/rclone_tmp"/*/* "$USERPROFILE/tools/rclone/"
```

## 步骤 2：添加 Rclone 到 PATH

```powershell
[Environment]::SetEnvironmentVariable("Path", "$env:Path;$env:USERPROFILE\tools\rclone", "User")
```

当前终端 Session 需重启窗口才能识别新的 PATH。验证是否生效：

```bash
rclone --version
# 如果找不到 rclone，用绝对路径：%USERPROFILE%\tools\rclone\rclone.exe
```

## 步骤 3：配置 OSS 连接

向用户确认以下信息：
- OSS Bucket 名称
- AccessKey ID
- AccessKey Secret
- Endpoint（如 `oss-cn-hangzhou.aliyuncs.com`）

然后执行：

```bash
rclone config create oss-xhs s3 \
  provider=Alibaba \
  env_auth=false \
  access_key_id={填入 AccessKey ID} \
  secret_access_key={填入 AccessKey Secret} \
  endpoint={填入 Endpoint} \
  acl=private
```

## 步骤 4：挂载 OSS

如果之前有残留挂载，先清理：

```bash
taskkill /F /IM rclone.exe 2>/dev/null
rm -rf materials
```

然后挂载（Windows 不支持 `--daemon`，以后台进程方式运行）：

```bash
rclone mount oss-xhs:{Bucket名称}/sales/data materials/ \
  --cache-dir "$TEMP/rclone-cache" \
  --vfs-cache-mode writes &
```

挂载后 `materials/` 目录直接显示各项目素材目录（如 `中央半岛`、`凤翔豪庭` 等），省去 `sales/data/` 嵌套。

> **说明**：路径 `sales/data` 是此 Bucket 的实际素材根目录。如果 Bucket 结构调整，相应修改挂载路径即可。

## 步骤 5：验证

```bash
ls materials/
# 应直接看到各项目素材目录（如 中央半岛/、凤翔豪庭/ 等）
```

## 步骤 6：配置开机自启（可选）

项目已内置启动脚本 `scripts/mount-oss.bat`，通过 Windows 计划任务实现登录时自动挂载。

在项目根目录下执行：

```powershell
schtasks /Create /TN 'XHS Mount OSS' /TR "$((Get-Location).Path)\scripts\mount-oss.bat" /SC ONLOGON /F
```

验证：

```powershell
schtasks /Run /TN 'XHS Mount OSS'; Start-Sleep 6; Get-ChildItem materials\
```

管理：

```powershell
schtasks /Query /TN 'XHS Mount OSS'      # 查看任务
schtasks /Delete /TN 'XHS Mount OSS' /F  # 删除任务
```

## 注意事项

- Windows 不支持 `--daemon`，挂载以后台进程方式运行。重启电脑后由计划任务自动重新挂载
- 如有残留 rclone 进程导致挂载失败，先执行 `taskkill /F /IM rclone.exe` 清理
- 挂载路径 `materials/` 是相对路径，必须在项目根目录下执行
- 素材在 OSS 端由运营维护，本地只读，本项目的任何脚本或 Skill 均不允许向 `materials/` 写入

完成后执行 [03-init-project.md](03-init-project.md)。
