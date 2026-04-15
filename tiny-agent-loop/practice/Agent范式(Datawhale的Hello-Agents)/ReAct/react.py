# ReAct 提示词模板
REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# 当直接运行本脚本时，Python 的模块搜索路径（sys.path）通常不包含上级目录，
# 导致像 `from llm import HelloAgentsLLM` 这样的导入失败（ModuleNotFoundError）。
# 这里把上级目录加入 sys.path，确保可以导入同一目录下的模块（如 llm.py）
import sys # 导入 Python 的运行时模块搜索与解释器相关接口（比如 sys.path）
import os # 导入与操作系统路径、文件相关的实用函数（比如 os.path.dirname、os.path.join）
_here = os.path.dirname(__file__) # __file__ 是当前脚本文件的路径（运行时由解释器设置）；os.path.dirname(...) 返回该文件所在的目录（相对或绝对，取决于 __file__）
_parent = os.path.abspath(os.path.join(_here, "..")) # os.path.join(_here, "..") 构造父目录的路径表达（“上一级”）；os.path.abspath(...) 将路径转换为绝对路径，确保在不同目录下也能正常工作
if _parent not in sys.path: # 检查父目录是否已经在模块搜索路径中，避免重复添加
    sys.path.insert(0, _parent) # 将父目录插入到 sys.path 的开头，确保在导入模块时优先搜索父目录

from llm import HelloAgentsLLM
from tool.toolexecutor import ToolExecutor

# REACT_PROMPT_TEMPLATE 已在别处定义，我们用 Pydantic 来管理它的参数
class ReActPromptParams(BaseModel):
    """用于格式化 ReAct 提示词的参数模型"""
    tools: str = Field(..., description="可用工具的描述文本")
    question: str = Field(..., description="用户原始问题")
    history: str = Field(default="", description="历史 Action/Observation 记录")

# 用 Pydantic 模型定义 LLM 的结构化输出
class AgentAction(BaseModel):
    """定义 Agent 可能产生的动作指令"""
    thought: Optional[str] = Field(None, description="推理过程")
    action: str = Field(..., description="要执行的动作，格式为 'ToolName[input]' 或 'Finish[answer]'")
    
    @classmethod
    def from_llm_text(cls, text: str) -> "AgentAction":
        """
        从 LLM 自由文本中解析出结构化动作。
        这里为了兼容性保留正则解析，但在现代化方案中，
        你会倾向于让 LLM 直接返回符合该模型的 JSON。
        """
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else ""
        return cls(thought=thought, action=action)

    def is_finished(self) -> bool:
        return self.action.startswith("Finish")

    def parse_tool_call(self) -> tuple[Optional[str], Optional[str]]:
        """解析工具调用，返回 (tool_name, tool_input)"""
        match = re.match(r"(\w+)\[(.*)\]", self.action, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

class AgentStep(BaseModel):
    """单步执行的完整记录"""
    step_num: int
    thought: Optional[str] = None
    action: str
    observation: str

class ReActAgent:
    """
    现代化重构的 ReAct 智能体。
    - 使用 Pydantic 模型管理状态和解析结果
    - 保留依赖注入以提高可测试性
    """
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history: List[AgentStep] = []  # 改用结构化历史记录

    def run(self, question: str) -> Optional[str]:
        self.history = []
        
        for step_num in range(1, self.max_steps + 1):
            print(f"--- 第 {step_num} 步 ---")
            
            # 1. 格式化提示词（参数用 Pydantic 模型校验）
            params = ReActPromptParams(
                tools=self.tool_executor.getAvailableTools(),
                question=question,
                history=self._format_history()
            )
            prompt = REACT_PROMPT_TEMPLATE.format(**params.model_dump())
            
            # 2. 调用 LLM
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误: LLM 未返回有效响应。")
                break
            
            # 3. 使用 Pydantic 模型解析输出（这里展示了两种可能的路径）
            agent_action = AgentAction.from_llm_text(response_text)
            if agent_action.thought:
                print(f"思考: {agent_action.thought}")
            
            if not agent_action.action:
                print("警告: 未能解析出有效 Action，流程终止。")
                break
            
            # 4. 处理 Finish 指令（支持跨行的 Finish[...] 内容）
            if agent_action.is_finished():
                m = re.search(r"Finish\[(.*)\]", agent_action.action, re.DOTALL)
                if m:
                    final_answer = m.group(1)
                else:
                    # 尝试保守截取（若格式不完全匹配）
                    s = agent_action.action
                    if s.startswith("Finish[") and s.endswith("]"):
                        final_answer = s[len("Finish["):-1]
                    else:
                        final_answer = s
                print(f"🎉 最终答案: {final_answer}")
                return final_answer
            
            # 5. 执行工具调用
            tool_name, tool_input = agent_action.parse_tool_call()
            if not tool_name or not tool_input:
                observation = f"错误: 无效的 Action 格式 '{agent_action.action}'"
            else:
                print(f"🎬 行动: {tool_name}[{tool_input}]")
                tool_func = self.tool_executor.getTool(tool_name)
                if not tool_func:
                    observation = f"错误: 未找到名为 '{tool_name}' 的工具。"
                else:
                    try:
                        observation = tool_func(tool_input)
                    except Exception as e:
                        observation = f"错误: 工具执行时发生异常 - {e}"
            
            print(f"👀 观察: {observation}")
            
            # 6. 记录结构化历史
            self.history.append(AgentStep(
                step_num=step_num,
                thought=agent_action.thought,
                action=agent_action.action,
                observation=observation
            ))
        
        print("已达到最大步数，流程终止。")
        return None

    def _format_history(self) -> str:
        """将结构化历史记录格式化为文本，用于提示词"""
        lines = []
        for step in self.history:
            lines.append(f"Action: {step.action}")
            lines.append(f"Observation: {step.observation}")
        return "\n".join(lines)


if __name__ == "__main__":
    # 要执行的查询（端到端测试问题）
    question = "华为最新发布的手机以及其卖点是什么"

    # 1) 尝试构造真实的 LLM 客户端
    try:
        llm_client = HelloAgentsLLM()
        print(f"LLM 已初始化: {llm_client.model}")
    except Exception as e:
        print(f"⚠️ 无法初始化 HelloAgentsLLM: {e}\n")

    # 2) 构造工具执行器并注册 Search 的包装器（使工具对 Agent 使用时只接受一个参数 query）
    tool_executor = ToolExecutor()

    try:
        from tool.search_tool import SerpApiSettings, search as serp_search

        def search_wrapper(query: str) -> str:
            try:
                settings = SerpApiSettings()
            except Exception as e:
                return f"错误: 无法加载 SerpApiSettings: {e}"

            try:
                # 调用当前实现的签名：search(query, settings)
                return serp_search(query, settings)
            except Exception as e:
                return f"搜索失败: {e}"

    except Exception as e:
        # 如果导入 SerpApi 相关模块失败，提供降级的本地模拟函数
        print(f"⚠️ SerpApi 初始化失败: {e}")

    tool_executor.registerTool("Search", "网页搜索（使用 SerpApi）", search_wrapper)

    # 3) 运行 ReAct 智能体
    agent = ReActAgent(llm_client=llm_client, tool_executor=tool_executor, max_steps=4)
    print("\n=== 开始 ReAct 端到端测试 ===")
    final_answer = agent.run(question)
    print("\n=== 测试结束，最终答案 ===")
    print(final_answer)