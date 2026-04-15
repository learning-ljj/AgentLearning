import os
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(dotenv_path=".env")

# 第一步：定义配置模型
class SerpApiSettings(BaseSettings):
    """
    SerpApi 配置类，自动从环境变量或 .env 文件加载。
    Pydantic v2 的配置方式与 v1 略有不同，主要体现在 Config 类被 model_config 替代。
    """
    # Field 的用法与 v1 类似，但推荐使用更明确的 validation_alias 来指定环境变量名
    api_key: str = Field(
        ...,  # 必填字段
        validation_alias="SERPAPI_API_KEY",  # 告诉 Pydantic 从哪个环境变量取值
        description="SerpApi 的 API 密钥"
    )
    gl: str = Field(
        default="cn",
        validation_alias="SERPAPI_GL",
        description="国家/地区代码，影响搜索结果的地域倾向"
    )
    hl: str = Field(
        default="zh-cn",
        validation_alias="SERPAPI_HL",
        description="界面语言代码"
    )
    timeout: int = Field(
        default=30,
        validation_alias="SERPAPI_TIMEOUT",
        description="请求超时时间（秒）"
    )

    # v2 使用 model_config 替代内部 Config 类
    model_config = SettingsConfigDict(
        case_sensitive=False,      # 环境变量名大小写不敏感
        extra="ignore"             # 忽略额外的环境变量，避免误报
    )


# 第二步：定义响应结构模型(Pydantic Model)
from pydantic import BaseModel, Field as PydanticField
from typing import List, Optional

class AnswerBox(BaseModel):
    """知识图谱/直接答案框"""
    answer: Optional[str] = None
    title: Optional[str] = None

class KnowledgeGraph(BaseModel):
    """右侧知识面板"""
    title: Optional[str] = None
    description: Optional[str] = None

class OrganicResult(BaseModel):
    """自然搜索结果"""
    title: Optional[str] = None
    snippet: Optional[str] = None
    link: Optional[str] = None

class SerpApiResponse(BaseModel):
    """
    SerpApi 返回结果的结构化描述。
    我们只定义解析逻辑中会用到的字段，其他字段全部忽略。
    """
    answer_box_list: Optional[List[str]] = PydanticField(default=None, alias="answer_box_list")
    answer_box: Optional[AnswerBox] = PydanticField(default=None, alias="answer_box")
    knowledge_graph: Optional[KnowledgeGraph] = PydanticField(default=None, alias="knowledge_graph")
    organic_results: Optional[List[OrganicResult]] = PydanticField(default=None, alias="organic_results")

    # 允许模型接受原始 JSON 中多余的字段，但不会报错
    model_config = {"extra": "ignore"}


# 第三步：实现 Search Tool，注入依赖（client: SerpApiClient）
from serpapi import SerpApiClient

# 传入参数不能包含client参数，这样会不方便调用，因为需要在调用时传递client参数。
def search(
    query: str,
    settings: SerpApiSettings = None,
) -> str:
    """
    执行一次网页搜索，返回格式化后的文本结果。
    
    Args:
        query: 搜索查询字符串。    
    Returns:
        格式化后的搜索结果文本。出错时返回以 "错误:" 或 "搜索时发生错误:" 开头的字符串。
    """
    print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
    
    try:
        settings = settings or SerpApiSettings()  # 从环境变量加载配置，如果缺失必填字段会抛出 ValidationError
        client_params = {
            "api_key": settings.api_key,
            "engine": "google",
            "q": query,
            "gl": settings.gl,
            "hl": settings.hl,
        }

        # 如果 client 需要每次用不同参数，我们可以在外部构造它。
        raw_result = SerpApiClient(client_params).get_dict()
        
        # 将原始字典解析成我们定义好的 Pydantic 模型，一个 SerpApiResponse 对象
        # 这样后面就可以享受类型安全和 IDE 自动补全了！
        # 如果数据不符合模型（比如某个字段类型不对），它会抛出明确的 ValidationError，我们可以在外层统一处理。
        parsed = SerpApiResponse.model_validate(raw_result) 
        
        # 智能解析逻辑，现在代码的可读性大幅提升
        if parsed.answer_box_list:
            return "\n".join(parsed.answer_box_list)
        
        if parsed.answer_box and parsed.answer_box.answer:
            return parsed.answer_box.answer
        
        if parsed.knowledge_graph and parsed.knowledge_graph.description:
            return parsed.knowledge_graph.description
        
        if parsed.organic_results:
            # 取前三条自然结果，格式化输出
            snippets = [
                f"[{i+1}] {res.title or ''}\n{res.snippet or ''}"
                for i, res in enumerate(parsed.organic_results[:3])
            ]
            return "\n\n".join(snippets)
        
        return f"对不起，没有找到关于 '{query}' 的信息。"
    
    except Exception as e:
        return f"搜索时发生错误: {e}"
    

# 第四步：编写调用示例（包含依赖注入的组装）
if __name__ == "__main__":
    
    # 调用搜索函数
    query = "Python 快速排序"
    response_text = search(query=query)
    
    print("\n--- 搜索结果 ---")
    print(response_text)


# 第五步：得益于依赖注入，轻松编写单元测试
'''
import unittest
from unittest.mock import MagicMock

class TestSearchFunction(unittest.TestCase):
    def test_search_with_answer_box(self):
        # 1. 准备假配置
        settings = SerpApiSettings(
            api_key="fake-key",
            gl="us",
            hl="en"
        )
        
        # 2. 创建 Mock 客户端
        mock_client = MagicMock()
        # 模拟 get_dict() 返回一个包含 answer_box 的字典
        mock_client.get_dict.return_value = {
            "answer_box": {
                "answer": "快速排序是一种分治算法。"
            }
        }
        
        # 3. 调用函数，传入 Mock 对象
        result = search(
            query="快速排序",
            client=mock_client
        )
        
        # 4. 断言
        self.assertIn("分治算法", result)
        self.assertNotIn("错误", result)
    
    def test_search_no_results(self):
        settings = SerpApiSettings(api_key="fake-key")
        mock_client = MagicMock()
        mock_client.get_dict.return_value = {}  # 空字典
        
        result = search("不存在的查询", mock_client)
        self.assertTrue(result.startswith("对不起"))

if __name__ == "__main__":
    unittest.main()
'''