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

重启终端后验证：

```bash
rclone --version
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

```bash
mkdir -p materials
rclone mount oss-xhs:{Bucket名称} materials/ \
  --cache-dir "$TEMP/rclone-cache" \
  --vfs-cache-mode writes \
  --daemon
```

挂载后 `materials/` 目录显示 OSS 中的文件。

## 步骤 5：验证

```bash
ls materials/
# 应看到 OSS 中各项目的素材目录
```

## 注意事项

- `--daemon` 使 Rclone 在后台运行。重启电脑后需重新挂载（可配置为开机自启）
- 挂载路径 `materials/` 是相对路径，必须在项目根目录下执行
- 素材在 OSS 端由运营维护，本地只读，本项目的任何脚本或 Skill 均不允许向 `materials/` 写入

完成后执行 [03-init-project.md](03-init-project.md)。
