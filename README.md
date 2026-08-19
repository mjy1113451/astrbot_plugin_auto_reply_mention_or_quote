# Astrbot Plugin: auto_reply_mention_or_quote

当机器人被 @ 提及（mention）或被引用（quote）时，自动回复指定内容。

## 功能

- **自动回复**: 机器人被提及或引用时，自动发送预设的回复内容
- **可配置回复文本**: 可在配置中修改自动回复的内容
- **开关控制**: 可通过配置随时启用/禁用

## 安装

将该插件仓库克隆到 Astrbot 的插件目录下：

```bash
cd your astrbot plugins dir
git clone https://github.com/mjy1113451/astrbot_plugin_auto_reply_mention_or_quote.git
```

## 配置

在 Astrbot 管理面板或配置文件中设置以下参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `reply_text` | string | `收到！` | 自动回复的文本内容 |
| `enabled` | bool | `true` | 是否启用插件 |

## 工作原理

该插件监听 `bot_mention_or_quote` 事件，当检测到机器人被 @ 或被引用时，触发 `on_mention_or_quote` 方法，发送配置的回复内容。

## License

MIT
