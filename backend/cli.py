#!/usr/bin/env python3
"""
Deep Research Agent - 交互式多智能体深度调研工作台 (Phase 2 全功能增强版)
包含 100% 真实大模型推理、真实全网检索、人机协同大纲在线审核、Critic 事实反思评估与 Verifier 引用防幻觉校验
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 确保 backend 根目录在 sys.path 中
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.table import Table
from rich.prompt import Prompt

console = Console()

from app.core.config import settings, call_llm
from app.agents.state import ResearchState, ChapterOutline
from app.agents.planner import plan_outline_node
from app.agents.researcher import research_worker_node
from app.agents.critic import critic_node
from app.agents.writer import synthesize_report_node
from app.agents.verifier import citation_verifier_node

def check_or_setup_api_key():
    """检查 API Key 配置"""
    settings.reload()
    api_key = settings.LLM_API_KEY
    if not api_key:
        console.print(Panel(
            "[bold yellow]⚠️ 检测到尚未配置大模型 API Key[/bold yellow]\n"
            "[dim]系统需要真实的大模型（如 DeepSeek、OpenAI、通义千问等）进行实时推理与撰写。[/dim]",
            border_style="yellow"
        ))
        user_key = Prompt.ask("🔑 请输入您的 API Key (如 sk-...)").strip()
        user_url = Prompt.ask("🌐 API Base URL", default="https://api.deepseek.com").strip()
        user_model = Prompt.ask("🤖 模型名称", default="deepseek-chat").strip()
        
        env_path = backend_dir / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"LLM_API_KEY={user_key}\n")
            f.write(f"LLM_BASE_URL={user_url}\n")
            f.write(f"LLM_MODEL={user_model}\n")
            f.write("TAVILY_API_KEY=\n")
            f.write("DEFAULT_RESEARCH_DEPTH=standard\n")
            
        settings.reload()
        console.print("[bold green]✅ API 配置已成功保存至 backend/.env 文件！[/bold green]\n")

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🔍 Deep Research Agent (AI 深度研究助手) · Phase 2[/bold cyan]\n"
        "[dim]真实大模型推理 · 全网实时检索 · 人机大纲协同 · Critic事实反思 · Verifier防幻觉[/dim]",
        border_style="cyan"
    ))

def render_outline_table(outline: List[ChapterOutline]):
    """渲染大纲表格"""
    table = Table(title="🎯 当前调研大纲与检索规划", border_style="blue", show_header=True)
    table.add_column("序号", justify="center", style="cyan", no_wrap=True)
    table.add_column("章节标题", style="bold white")
    table.add_column("重点调研方向", style="bright_white")
    table.add_column("规划检索词", style="dim cyan")
    
    for ch in outline:
        queries = ch.get("search_queries", [])
        q_text = "\n".join([f"• {q}" for q in queries]) if queries else "未指定"
        table.add_row(
            f"第 {ch.get('chapter_num')} 章",
            ch.get("title", ""),
            ch.get("focus", ""),
            q_text
        )
    console.print(table)

def interactive_outline_review(initial_outline: List[ChapterOutline]) -> List[ChapterOutline]:
    """人机协同大纲审核与编辑交互循环 (Human-in-the-Loop)"""
    outline = [dict(ch) for ch in initial_outline]
    
    while True:
        console.print("\n")
        render_outline_table(outline)
        
        console.print("\n[bold yellow]⚙️ 【人机协同交互 (Human-in-the-Loop)】请对大纲进行确认或调整：[/bold yellow]")
        console.print("  [bold green][Enter][/bold green] 确认当前大纲，立即启动全网真实调研")
        console.print("  [bold cyan][1][/bold cyan] 修改指定章节标题/关注点")
        console.print("  [bold cyan][2][/bold cyan] 增加自定义新章节/研究维度")
        console.print("  [bold cyan][3][/bold cyan] 删除指定章节")
        
        choice = Prompt.ask("👉 请选择操作 (回车直接确认)", default="").strip()
        
        if choice == "":
            console.print("[bold green]✅ 大纲已由人工确认通过！正式进入全网深度调研...[/bold green]\n")
            return outline
        elif choice == "1":
            try:
                ch_idx_str = Prompt.ask(f"请输入要修改的章节序号 (1~{len(outline)})")
                ch_idx = int(ch_idx_str) - 1
                if 0 <= ch_idx < len(outline):
                    curr_title = outline[ch_idx]["title"]
                    new_title = Prompt.ask("新章节标题", default=curr_title).strip()
                    curr_focus = outline[ch_idx]["focus"]
                    new_focus = Prompt.ask("新调研重点", default=curr_focus).strip()
                    outline[ch_idx]["title"] = new_title
                    outline[ch_idx]["focus"] = new_focus
                    console.print("[green]已更新章节！[/green]")
            except Exception as e:
                console.print(f"[red]输入错误: {e}[/red]")
        elif choice == "2":
            new_title = Prompt.ask("请输入新增章节标题").strip()
            new_focus = Prompt.ask("请输入该章节重点调研方向").strip()
            new_query = Prompt.ask("请输入该章节搜索关键词 (选填)").strip()
            queries = [new_query] if new_query else [new_title]
            new_num = len(outline) + 1
            outline.append({
                "chapter_num": new_num,
                "title": new_title,
                "focus": new_focus,
                "search_queries": queries,
                "extracted_facts": []
            })
            console.print("[green]已成功添加新章节！[/green]")
        elif choice == "3":
            try:
                ch_idx_str = Prompt.ask(f"请输入要删除的章节序号 (1~{len(outline)})")
                ch_idx = int(ch_idx_str) - 1
                if 0 <= ch_idx < len(outline):
                    if len(outline) <= 1:
                        console.print("[red]至少需要保留一个调研章节！[/red]")
                    else:
                        deleted = outline.pop(ch_idx)
                        for i, ch in enumerate(outline):
                            ch["chapter_num"] = i + 1
                        console.print(f"[yellow]已删除第 {ch_idx+1} 章：{deleted['title']}[/yellow]")
            except Exception as e:
                console.print(f"[red]输入错误: {e}[/red]")

def interactive_qa_session(final_report: str, state: ResearchState):
    """研报生成后的交互式问答 REPL"""
    console.print("\n" + "=" * 70)
    console.print(Panel(
        "[bold cyan]💬 交互式问答模式已开启 (Deep-Dive Q&A)[/bold cyan]\n"
        "[dim]Agent 现已掌握本次调研的所有原始文献与生成研报，你可以随时针对细节提问（输入 q 或 exit 退出）。[/dim]",
        border_style="cyan"
    ))
    
    while True:
        try:
            user_q = Prompt.ask("\n[bold green]❓ 请输入您的追问[/bold green]").strip()
            if not user_q or user_q.lower() in ["q", "exit", "quit", "退出"]:
                console.print("[bold yellow]已退出问答模式。感谢使用 Deep Research Agent！[/bold yellow]")
                break
                
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
                console=console
            ) as progress:
                progress.add_task("[cyan]Agent 正在检索研报与事实库组织回答...", total=None)
                
                qa_prompt = f"""
你是一位顶级研究助理。以下是刚刚完成的深度研究报告全文及事实库：

【研报全文与事实来源】：
{final_report}

【用户针对报告的追问】：
{user_q}

请基于上述报告和事实来源，准确、严谨地回答用户的问题。如果报告中有相关数据支撑，请明确指出。
"""
                answer = call_llm(qa_prompt, system_prompt="You are a helpful and precise research assistant.")
                
            console.print(Panel(Markdown(answer), title="🤖 助手回答", border_style="green"))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]回答生成异常: {e}[/red]")

def main():
    print_banner()
    check_or_setup_api_key()
    
    parser = argparse.ArgumentParser(description="Deep Research Agent Interactive CLI")
    parser.add_argument("--query", "-q", type=str, help="调研课题 / 核心命题")
    parser.add_argument("--depth", "-d", choices=["quick", "standard", "deep"], default="standard", help="调研深度")
    parser.add_argument("--style", "-s", choices=["consulting", "academic", "executive"], default="consulting", help="报告风格")
    parser.add_argument("--output", "-o", type=str, default=None, help="自定义研报输出路径 (.md)")
    
    args = parser.parse_args()
    
    query = args.query
    if not query:
        console.print("\n[bold yellow]💡 请输入你想深度调研的任意真实课题：[/bold yellow]")
        user_input = Prompt.ask("👉 调研课题").strip()
        query = user_input if user_input else "全球固态电池商业化进展与主要厂商壁垒对比"
    
    max_iterations = 1 if args.depth == "quick" else (3 if args.depth == "deep" else 2)
    
    console.print(f"\n[bold green]🚀 正在启动多智能体深度调研流程 (Phase 2)...[/bold green]")
    console.print(f"📌 [cyan]课题:[/cyan] {query}")
    console.print(f"⚙️ [cyan]模型:[/cyan] {settings.LLM_MODEL} | [cyan]深度:[/cyan] {args.depth} (最大反思轮数: {max_iterations}) | [cyan]风格:[/cyan] {args.style}\n")

    state: ResearchState = {
        "task_id": f"task_{os.urandom(4).hex()}",
        "user_query": query,
        "research_depth": args.depth,
        "report_style": args.style,
        "clarification": "",
        "outline": [],
        "citations": [],
        "current_step": "plan",
        "iteration_count": 1,
        "max_iterations": max_iterations,
        "critic_feedback": "",
        "needs_more_research": False,
        "draft_report": "",
        "final_report": "",
        "logs": []
    }

    # 1. 真实大模型规划大纲 (Planner)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("[cyan]Planner Agent 正在调用大模型拆解课题并规划大纲...", total=None)
        plan_res = plan_outline_node(state)
        state.update(plan_res)

    console.print(f"[bold green]✨ Planner 规划完成！[/bold green] [dim]{state.get('clarification')}[/dim]")
    
    # 2. 人机协同大纲在线确认 (Human-in-the-Loop)
    approved_outline = interactive_outline_review(state["outline"])
    state["outline"] = approved_outline

    # 3. 检索与 Critic 反思循环
    while True:
        current_iter = state.get("iteration_count", 1)
        console.print(f"\n[bold blue]━━━ 正在执行第 {current_iter}/{max_iterations} 轮网络检索与事实提取 ━━━[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=False,
            console=console
        ) as progress:
            task_res = progress.add_task(f"[cyan]Researcher 正在执行全网检索与 Map-Reduce 事实压缩...", total=None)
            res_data = research_worker_node(state)
            state.update(res_data)
            progress.update(task_res, completed=100, description="[green]✅ 本轮事实抽取完成！")

        # Critic 评估节点
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console
        ) as progress:
            progress.add_task("[yellow]Critic Agent 正在对搜集到的事实进行充实度评估与反思...", total=None)
            critic_data = critic_node(state)
            state.update(critic_data)

        console.print(f"[bold yellow]🔍 Critic 评估意见:[/bold yellow] {state.get('critic_feedback')}")
        
        if state.get("needs_more_research", False) and state.get("iteration_count", 1) <= max_iterations:
            console.print(f"[bold magenta]⚡ 触发第二轮针对性深搜，补充薄弱维度的证据...[/bold magenta]")
        else:
            console.print(f"[bold green]✅ 证据库已充分，批准进入研报撰写阶段！[/bold green]\n")
            break

    # 4. 撰写研报初稿 (Writer)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("[cyan]Writer Agent 正在整合多轮事实材料，撰写结构化研报初稿...", total=None)
        writer_res = synthesize_report_node(state)
        state.update(writer_res)

    # 5. 防幻觉引用校验 (Verifier)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("[cyan]Verifier Agent 正在执行引用溯源字符级 1:1 校验与防幻觉修正...", total=None)
        verifier_res = citation_verifier_node(state)
        state.update(verifier_res)

    # 6. 保存并展示研报
    output_dir = backend_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "report")
    output_path = Path(args.output) if args.output else output_dir / f"{task_id}.md"
    
    report_content = state.get("final_report", "")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    # 同步归档至 SQLite 数据库
    try:
        from app.db.sqlite_store import save_report_archive
        save_report_archive(
            task_id=task_id,
            user_query=state.get("user_query", ""),
            research_depth=state.get("research_depth", "standard"),
            report_style=state.get("report_style", "consulting"),
            final_report=report_content,
            outline=state.get("outline", []),
            citations=state.get("citations", []),
            summary=state.get("clarification", "")
        )
    except Exception as e:
        console.print(f"[dim yellow]SQLite 归档跳过: {e}[/dim yellow]")

    console.print(f"\n[bold green]🎉 深度研究报告已通过防幻觉校验并成功落盘！[/bold green]")
    console.print(f"📄 [yellow]文件保存路径:[/yellow] {output_path.resolve()}\n")
    
    console.print(Panel(
        Markdown(report_content[:2000] + "\n\n*(篇幅较长，请在编辑器中查看完整保存文件...)*"),
        title=f"📖 最终深度研报预览 ({task_id})",
        border_style="green"
    ))

    # 7. 进入交互式追问会话
    interactive_qa_session(report_content, state)

if __name__ == "__main__":
    main()
