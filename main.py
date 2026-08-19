import os
import json
from typing import Optional, Dict, Any, List
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At, Reply
from astrbot.api.provider import ProviderInfo
from astrbot.core.provider.manager import ProviderManager
from astrbot.core.provider.base import BaseProvider

@register("auto_reply_mention_or_quote", "智能回复提及与引用", "智能检测@或引用机器人自身的消息并使用指定模型回复", "1.0.0")
class AutoReplyMentionOrQuotePlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.config = config
        self.provider_manager: Optional[ProviderManager] = None
        self.provider: Optional[BaseProvider] = None
        self._initialize_provider()

    def _initialize_provider(self):
        """根据配置初始化模型提供商"""
        provider_name = self.config.get("provider")
        if not provider_name:
            self.logger.warning("未配置模型提供商，插件将无法回复。请前往插件配置设置。")
            return

        try:
            self.provider_manager = self.context.get_provider_manager()
            if not self.provider_manager:
                self.logger.error("无法获取 ProviderManager 实例。")
                return

            # 查找并设置提供商
            self.provider = self.provider_manager.get_provider_by_name(provider_name)
            if not self.provider:
                self.logger.error(f"未找到名为 '{provider_name}' 的提供商。请检查配置。")
                return

            info = self.provider.get_info()
            self.logger.info(f"成功初始化提供商: {info.name} (模型: {info.current_model})")
        except Exception as e:
            self.logger.error(f"初始化提供商时出错: {e}")

    async def is_bot_mentioned_or_quoted(self, event: AstrMessageEvent) -> bool:
        """
        判断当前消息是否 @ 了机器人自身，或者引用了机器人自身的消息。
        """
        if not event.message_obj:  # 确保消息对象存在
            return False

        bot_id = event.message_obj.self_id  # 获取机器人自身的ID
        message_chain = event.message_obj.message  # 获取消息链
        
        # 1. 检查 @ 机器人
        for component in message_chain:
            if isinstance(component, At) and component.qq == bot_id:
                self.logger.debug(f"检测到 @ 机器人 (ID: {bot_id})")
                return True
        
        # 2. 检查引用机器人消息
        for component in message_chain:
            if isinstance(component, Reply):
                # Reply 消息段的 message_id 是被回复消息的ID，我们需要获取被回复消息的发送者ID
                # 这通常需要调用平台适配器的方法或查询消息历史。AstrBot 的 event 对象可能提供相关信息。
                # 如果 event 有 get_reply_message() 方法或类似功能，可以这样调用：
                # try:
                #     reply_message = event.get_reply_message()
                #     if reply_message and reply_message.sender.id == bot_id:
                #         self.logger.debug(f"检测到引用机器人消息 (ID: {bot_id})")
                #         return True
                # except:
                #     pass
                
                # 由于 AstrBot 的 API 可能没有直接暴露获取被回复消息发送者ID的方法，
                # 这里使用一种更通用的方式：尝试从 event 的原始消息中提取。
                # 这依赖于平台适配器的实现，可能需要根据实际情况调整。
                # 一个常见的实现是 raw_message 中会包含 reply sender 的信息。
                raw_message = event.message_obj.raw_message
                if hasattr(raw_message, 'reply') and raw_message.reply:
                    # 假设 raw_message.reply 是一个包含发送者信息的对象
                    # 结构可能因平台而异，例如 raw_message.reply.sender.id 或 raw_message.reply.user_id
                    # 这里需要根据实际平台调整。以下为一种可能的实现方式：
                    try:
                        if hasattr(raw_message.reply, 'sender') and hasattr(raw_message.reply.sender, 'id'):
                            if raw_message.reply.sender.id == bot_id:
                                self.logger.debug(f"检测到引用机器人消息 (ID: {bot_id})")
                                return True
                        elif hasattr(raw_message.reply, 'user_id'):  # 某些平台可能直接有 user_id
                            if raw_message.reply.user_id == bot_id:
                                self.logger.debug(f"检测到引用机器人消息 (ID: {bot_id})")
                                return True
                    except Exception as e:
                        self.logger.debug(f"解析引用消息发送者ID时出错（这是预期的，可能不支持此平台）: {e}")

        return False

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """
        主事件监听器，处理所有类型的消息。
        """
        # 1. 判断消息是否满足触发条件
        is_mentioned_or_quoted = await self.is_bot_mentioned_or_quoted(event)
        
        if not is_mentioned_or_quoted:
            return  # 不满足触发条件，直接返回

        # 2. 准备发送回复
        if not self.provider:
            self.logger.warning("未配置有效的模型提供商，无法生成回复。请前往插件配置设置。")
            yield event.plain_result("抱歉，我暂时无法回复，因为模型提供商未配置或出错。")
            return

        try:
            # 获取发送者信息
            sender_name = event.get_sender_name()
            user_message = event.message_str  # 获取消息的纯文本内容
            
            # 构建对话消息
            messages = [
                {"role": "system", "content": f"你是一个友好的助手，请回复 {sender_name}。"},
                {"role": "user", "content": user_message}
            ]
            
            # 调用LLM生成回复
            response_text = await self._generate_response(messages)
            
            # 发送回复
            if response_text:
                yield event.plain_result(response_text)
            else:
                self.logger.warning("模型返回了空内容。")
                yield event.plain_result("抱歉，我没有生成任何回复。")
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
            yield event.plain_result("抱歉，处理你的请求时出现了错误。")

    async def _generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        调用配置的模型提供商生成回复。
        """
        try:
            # 调用提供商的聊天完成方法
            response = await self.provider.chat_completion(
                messages=messages,
                temperature=0.7,
                top_p=1.0,
                max_tokens=2048
            )
            return response
        except Exception as e:
            self.logger.error(f"调用模型生成回复时出错: {e}")
            return ""