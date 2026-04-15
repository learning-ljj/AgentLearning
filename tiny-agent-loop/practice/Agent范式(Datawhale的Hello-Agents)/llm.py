import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict

# 导入 Pydantic 相关模块
from pydantic import Field, ValidationError, ConfigDict
from pydantic_settings import BaseSettings  # 专门用于配置管理的基类

# 加载 .env 文件（pydantic-settings 也能自动加载，但保留 dotenv 也无妨）
load_dotenv(dotenv_path=".env")

# --- 1. 定义配置模型 ---
class LLMSettings(BaseSettings):
    """
    用 Pydantic 定义的配置类。
    它会自动从环境变量中读取同名（或指定前缀）的变量。
    """
    # Field() 是 Pydantic 的字段描述器，用于添加元数据、默认值或验证规则。
    # 第一个参数是默认值。
    model: str = Field(default="deepseek-v3-2-251201", description="模型 ID")
    api_key: str
    base_url: str
    timeout: int = 60

    model_config = ConfigDict(
        case_sensitive=False,
        env_prefix="LLM_"   # 推荐使用统一前缀
    )


# --- 2. 改进后的 LLM 客户端类 ---
class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的LLM客户端。
    现在配置通过 Pydantic 管理，代码更简洁、更安全。
    """
    def __init__(self, settings: LLMSettings = None):
        """
        初始化客户端。
        
        Args:
            settings: 可选的 LLMSettings 实例。若不提供，则自动从环境变量创建。
        """
        # 如果调用者没有传入配置对象，我们就自己创建一个。
        # 这个创建过程会自动读取环境变量并进行校验。
        # 如果环境变量缺失或格式错误，这里会抛出 ValidationError。
        self.settings = settings or LLMSettings()  # 类型: LLMSettings
        
        # 现在，self.settings 里的字段都是已经校验过的、类型正确的值。
        self.model = self.settings.model
        self.client = OpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url,
            timeout=self.settings.timeout
        )
        # 注意：由于 Pydantic 已经保证了 api_key, base_url 等字段非空，
        # 我们不需要再写那一大堆 if not all(...) 的检查代码了。
        # 配置错误会在 LLMSettings() 构造时就被拦截。

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        调用大语言模型进行思考，并返回其响应。
        """
        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            print("✅ 大语言模型响应成功:")
            # response 不是一次性完整文本，而是“很多小块数据”（chunk）按顺序到来。每个 chunk 里通常只包含一小段新文本。
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or "" # 从当前 chunk 里取出新增文本内容。若取到的是空值（例如 None），就用空字符串 "" 代替。
                print(content, end="", flush=True) # 把当前片段立即打印出来，不自动换行。立刻把缓冲区内容刷到屏幕，不等缓存。
                collected_content.append(content)
            print()
            return "".join(collected_content)

        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None


# --- 3. 使用示例 ---
if __name__ == '__main__':
    try:
        # 方式一：直接创建，LLMSettings 会自动从环境变量加载
        llmClient = HelloAgentsLLM()
        
        # 方式二：如果你想手动传入配置（比如测试时），可以：
        # custom_settings = LLMSettings(
        #     model="custom-model",
        #     api_key="sk-xxx",
        #     base_url="https://custom.api.com/v1",
        #     timeout=30
        # )
        # llmClient = HelloAgentsLLM(settings=custom_settings)
        
        exampleMessages = [
            {"role": "system", "content": "You are a helpful assistant that writes Python code."},
            {"role": "user", "content": "写一个快速排序算法"}
        ]
        
        print("--- 调用LLM ---")
        responseText = llmClient.think(exampleMessages)
        if responseText:
            print("\n\n--- 完整模型响应 ---")
            print(responseText)

    except ValidationError as e:
        # 这里捕获 Pydantic 在创建 LLMSettings 时抛出的校验错误
        print("❌ 配置错误，请检查 .env 文件或环境变量：")
        print(e.errors())  # 以 JSON 格式输出详细的错误信息，比如哪个字段缺失了