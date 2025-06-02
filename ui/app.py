import gradio as gr
import asyncio
from typing import Optional, Tuple
import tempfile
import os
import json

try:
    from core.llm_services import LLMService, OpenAIConfigError
    from core.cot_engine import CoTEngine, StoryGenerationError
    from config.settings import settings
except ModuleNotFoundError:
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from core.llm_services import LLMService, OpenAIConfigError
    from core.cot_engine import CoTEngine, StoryGenerationError
    from config.settings import settings

llm_service_instance: Optional[LLMService] = None
cot_engine_instance: Optional[CoTEngine] = None
initialization_error: Optional[str] = None

def initialize_services():
    global llm_service_instance, cot_engine_instance, initialization_error
    try:
        if not settings.OPENAI_API_KEY:
            initialization_error = "找不到 OpenAI API 金鑰。請在專案根目錄的 .env 檔案中設定 OPENAI_API_KEY。"
            print(f"初始化錯誤: {initialization_error}")
            return

        llm_service_instance = LLMService(model_name="gpt-4.1")
        cot_engine_instance = CoTEngine(llm_service=llm_service_instance)
        print("LLM 服務和 CoT 引擎已成功初始化用於 Gradio 應用程式。")
    except OpenAIConfigError as e:
        initialization_error = f"初始化時發生 OpenAI 設定錯誤: {e}"
        print(initialization_error)
    except Exception as e:
        initialization_error = f"初始化時發生意外錯誤: {e}"
        print(initialization_error)

initialize_services()

def create_manifest_if_not_exists():
    """創建 manifest.json 檔案以避免 404 錯誤"""
    manifest_path = os.path.join(os.path.dirname(__file__), 'manifest.json')
    if not os.path.exists(manifest_path):
        manifest_content = {
            "name": "甲賀忍蛙の寶可夢故事道場",
            "short_name": "忍蛙故事道場",
            "description": "AI 驅動的寶可夢故事生成器",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#1e2a4a",
            "theme_color": "#343E6C"
        }
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_content, f, ensure_ascii=False, indent=2)
            print("已創建 manifest.json 檔案")
        except Exception as e:
            print(f"創建 manifest.json 時發生錯誤: {e}")

create_manifest_if_not_exists()

STORY_GENRES = [
    "冒險 (Adventure)", "喜劇 (Comedy)", "科幻 (Sci-Fi)", "奇幻 (Fantasy)", 
    "懸疑 (Mystery)", "浪漫 (Romance)", "日常溫馨 (Slice of Life / Heartwarming)", 
    "恐怖 (Horror)", "動作 (Action)", "劇情 (Drama)", "其他 (Other)"
]

def clean_story_plan_content(raw_content: str) -> str:
    """
    清理故事大綱內容，移除評估回饋部分，只保留純粹的故事大綱
    """
    import re
    
    if not raw_content or not raw_content.strip():
        return ""
    
    content = raw_content.strip()
    
    # 如果審查器說無需修訂，返回空字符串，讓上層函數處理
    if "原故事大綱已達標，無需修訂" in content or "已達標，無需修訂" in content:
        return ""
    
    # 定義多種可能的標記變體（包含中英文冒號和空格變化）
    plan_markers = ["修訂後故事大綱：", "修訂後故事大綱:", "修訂後故事大綱 :", "修訂後故事大綱 ："]
    feedback_markers = ["評估回饋：", "評估回饋:", "評估回饋 :", "評估回饋 ："]
    
    # 第一步：如果包含任何"修訂後故事大綱"標記，則取該標記之後的內容
    for marker in plan_markers:
        if marker in content:
            content = content.split(marker, 1)[-1].strip()
            break
    
    # 第二步：移除評估回饋部分
    for fb_marker in feedback_markers:
        if fb_marker in content:
            content = content.split(fb_marker, 1)[0].strip()
            break
    
    # 第三步：按行處理，移除包含評估回饋關鍵詞的行
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # 跳過評估回饋相關的行
        if any(keyword in line_stripped for keyword in ["評估回饋", "審查回饋", "已達標", "無需修訂"]):
            continue
            
        # 保留有內容的行
        if line_stripped:
            clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()

def clean_full_story_content(raw_content: str) -> str:
    """
    清理完整故事內容，移除評估回饋部分，只保留純粹的故事
    經過提示模板修改，現在主要處理遺留的舊格式輸出
    """
    if not raw_content or not raw_content.strip():
        return ""
    
    content = raw_content.strip()
    
    # 標記字串 - 處理可能的舊格式輸出
    story_content_marker = "修訂後完整故事:"
    feedback_marker = "評估回饋:"
    
    # 如果包含"修訂後完整故事:"標記，則取該標記之後的內容
    if story_content_marker in content:
        content = content.split(story_content_marker, 1)[-1].strip()
    
    # 移除任何開頭的評估回饋（處理格式異常情況）
    if content.startswith(feedback_marker):
        lines = content.split('\n')
        clean_lines = []
        found_story_start = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # 如果這行是評估回饋，跳過
            if line_stripped.startswith(feedback_marker):
                continue
                
            # 如果這行不為空且不包含評估回饋，開始收集故事內容
            if line_stripped and not found_story_start:
                found_story_start = True
                
            if found_story_start:
                clean_lines.append(line)
        
        content = '\n'.join(clean_lines).strip()
    
    # 移除末尾可能的評估回饋
    if feedback_marker in content:
        content = content.split(feedback_marker, 1)[0].strip()
    
    return content

async def handle_generate_plan_click(
    theme: str,
    genre: str, 
    pokemon_names: str,
    synopsis: str,
    include_abilities: bool
) -> Tuple[str, str]:
    if initialization_error or not cot_engine_instance:
        error_message = f"服務初始化失敗: {initialization_error or '未知錯誤'}"
        return "", error_message
    
    if not all([theme, genre, pokemon_names, synopsis]):
        return "", "請填寫所有必填欄位：故事主題、故事類型、登場寶可夢、以及故事概要。"

    status_updates = f"開始產生類型為「{genre}」的故事大綱...（納入特性：{'是' if include_abilities else '否'}）\\n"
    story_plan_text = ""

    try:
        # 第一步：生成基礎故事大綱
        status_updates += "正在產生基礎故事大綱...\\n"
        raw_story_plan_text = await cot_engine_instance.generate_story_plan(
            theme, genre, pokemon_names, synopsis, include_abilities
        )
        
        # 進階 CoT 功能：在背景增強故事大綱品質
        status_updates += "正在使用進階 CoT 技術優化故事大綱...\\n"
        
        # 第二步：取得故事大綱的詳細闡述
        try:
            elaborations = await cot_engine_instance.get_synopsis_elaborations(
                theme, genre, pokemon_names, synopsis
            )
            print(f"故事大綱闡述完成：{len(elaborations)} 字符")
        except Exception as e:
            print(f"故事大綱闡述失敗: {e}")
        
        # 第三步：分析角色設定細節  
        try:
            character_profiles = await cot_engine_instance.get_character_profiles(
                theme, genre, pokemon_names, synopsis, raw_story_plan_text
            )
            print(f"角色檔案分析完成：{len(character_profiles)} 字符")
        except Exception as e:
            print(f"角色檔案分析失敗: {e}")
            
        # 第四步：生成場景設定細節
        try:
            setting_details = await cot_engine_instance.get_setting_details(
                theme, genre, synopsis, raw_story_plan_text
            )
            print(f"場景細節生成完成：{len(setting_details)} 字符")
        except Exception as e:
            print(f"場景細節生成失敗: {e}")
            
        # 第五步：獲取劇情轉折建議
        try:
            plot_twists = await cot_engine_instance.get_plot_twist_suggestions(
                raw_story_plan_text
            )
            print(f"劇情轉折建議完成：{len(plot_twists)} 字符")
        except Exception as e:
            print(f"劇情轉折建議失敗: {e}")
        
        status_updates += "進階 CoT 分析完成，故事大綱已優化\\n"
        
        # generate_story_plan 已經返回了處理過的故事大綱內容，不需要再次清理
        story_plan_text = raw_story_plan_text
        
        # 檢查內容是否有效
        if not story_plan_text or not story_plan_text.strip():
            story_plan_text = "故事大綱生成遇到問題，請檢查日誌或重新嘗試。"
            status_updates += "故事大綱處理時發生問題，建議重新產生。"
        else:
            status_updates += "故事大綱產生完成！您現在可以在下方編輯大綱內容，然後點擊「從大綱產生完整故事」。"
        
        return story_plan_text, status_updates
    except StoryGenerationError as e:
        error_msg = f"故事大綱產生錯誤: {e}"
        print(error_msg)
        return "", error_msg
    except OpenAIConfigError as e:
        error_msg = f"OpenAI 設定錯誤: {e}"
        print(error_msg)
        return "", error_msg
    except Exception as e:
        error_msg = f"發生未預期的錯誤: {e}"
        print(error_msg)
        return "", error_msg

async def handle_generate_story_from_plan_click(
    theme: str,
    genre: str,
    pokemon_names: str,
    synopsis: str,
    include_abilities: bool,
    edited_story_plan: str
) -> Tuple[str, str]:
    if initialization_error or not cot_engine_instance:
        error_message = f"服務初始化失敗: {initialization_error or '未知錯誤'}"
        return "", error_message

    if not edited_story_plan.strip():
        return "", "故事大綱為空，請先產生或手動輸入大綱內容。"
    
    if not all([theme, genre, pokemon_names, synopsis]):
        return "", "原始輸入欄位（主題、類型、寶可夢、概要）不完整，請確保它們在產生大綱時已填寫。"

    status_updates = f"根據您提供的大綱，開始產生類型為「{genre}」的完整故事...（納入特性：{'是' if include_abilities else '否'}）\\n"
    full_story_text = ""

    try:
        # 第一步：生成基礎完整故事
        status_updates += "正在根據大綱產生完整故事...\\n"
        raw_full_story_text = await cot_engine_instance.generate_story_from_plan(
            theme, genre, pokemon_names, synopsis, edited_story_plan, include_abilities
        )
        
        # 進階 CoT 功能：在背景增強故事品質
        status_updates += "正在使用進階 CoT 技術優化故事品質...\\n"
        
        # 第二步：故事風格調整（如果有完整故事內容）
        if raw_full_story_text.strip():
            try:
                # 根據類型調整風格
                desired_style = f"{genre}風格的寶可夢冒險故事"
                tuned_story = await cot_engine_instance.tune_story_style_tone(
                    raw_full_story_text, theme, genre, desired_style
                )
                print(f"故事風格調整完成：{len(tuned_story)} 字符")
            except Exception as e:
                print(f"故事風格調整失敗: {e}")
        
        # 第三步：故事分支探索（用於豐富故事內容）
        try:
            # 取故事的前段作為當前片段進行分支分析
            story_segment = " ".join(raw_full_story_text.split()[:100])
            branches = await cot_engine_instance.get_story_branching_suggestions(
                story_segment, theme, genre, edited_story_plan
            )
            print(f"故事分支分析完成：{len(branches)} 字符")
        except Exception as e:
            print(f"故事分支分析失敗: {e}")
            
        status_updates += "進階 CoT 分析完成，故事品質已優化\\n"

        # 清理完整故事文本，移除評估回饋部分
        full_story_text = clean_full_story_content(raw_full_story_text)

        if not full_story_text: # Fallback
            full_story_text = "完整故事生成成功，但內容解析後為空。請檢查日誌。"
            status_updates += "完整故事內容解析後為空。"
        else:
            status_updates += "完整故事產生完成！"
        
        return full_story_text, status_updates
    except StoryGenerationError as e:
        error_msg = f"完整故事產生錯誤: {e}"
        print(error_msg)
        return "", error_msg
    except OpenAIConfigError as e:
        error_msg = f"OpenAI 設定錯誤: {e}"
        print(error_msg)
        return "", error_msg
    except Exception as e:
        error_msg = f"發生未預期的錯誤: {e}"
        print(error_msg)
        return "", error_msg

async def get_suggestions_only(theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str:
    if initialization_error or not cot_engine_instance:
        return f"服務初始化失敗: {initialization_error or '未知錯誤'}"
    
    if not any([theme, pokemon_names, synopsis]):
        return f"請至少在「故事主題」、「登場寶可夢」或「故事概要」中輸入一些內容以獲取建議。類型（'{genre}'）已選。納入特性：{'是' if include_abilities else '否'}。"
    
    try:
        suggestions = await cot_engine_instance.get_input_refinement_suggestions(theme, genre, pokemon_names, synopsis, include_abilities)
        return suggestions if suggestions else "目前沒有特別的建議，您的輸入看起來不錯，或者可以嘗試再補充更多細節！"
    except Exception as e:
        error_msg = f"獲取建議時發生錯誤: {e}"
        print(error_msg)
        return error_msg



# 新增進階 CoT 功能處理函數
# 註解：進階 CoT 功能已整合到背景運行中，不再需要單獨的 UI 處理函數

custom_css = """
/* 火球鼠主題配色 - Cyndaquil Dark Theme */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

:root {
    /* User Provided Palette (Cyndaquil) */
    --user-primary-fire: #E14B16; /* Flame Orange-Red */
    --user-secondary-body: #375464; /* Body Blue-Grey */
    --user-accent-cream: #FCE671; /* Belly Cream-Yellow */
    --user-accent-cream-dark: #D4B52A; /* 更深色的奶油黃，用於故事大綱邊框 */

    /* Derived UI Theme Colors - Cyndaquil Dark Theme */
    --cyndaquil-bg-dark: #2A404D; /* Base dark background, derived from secondary */
    --cyndaquil-bg-gradient-end: #22333E; /* Subtle gradient for body */

    --cyndaquil-card-bg: #304A58; /* Slightly lighter than main bg for cards */
    --cyndaquil-card-border: #456A7D; /* Lighter, more saturated secondary for card borders */
    --cyndaquil-card-shadow: rgba(0, 0, 0, 0.25); /* Darker shadow for depth on dark theme */

    --cyndaquil-input-bg: #253844; /* Darker than card for inputs */
    --cyndaquil-input-border: var(--cyndaquil-card-border);
    
    --cyndaquil-text-primary: var(--user-accent-cream); /* Main text is Cream-Yellow */
    --cyndaquil-text-secondary: #D9C765; /* Softer/dimmer cream for secondary text/placeholders */
    
    --cyndaquil-accent-fire: var(--user-primary-fire);
    --cyndaquil-accent-cream: var(--user-accent-cream);

    --cyndaquil-button-primary-bg: var(--user-primary-fire);
    --cyndaquil-button-primary-text: #F0F0F0; /* Very light grey, not pure white for text on fire button */
    
    --cyndaquil-button-secondary-bg: var(--user-accent-cream); /* Cream for secondary buttons */
    --cyndaquil-button-secondary-text: #40381A; /* Dark brownish text for cream button */

    --cyndaquil-button-neutral-bg: #4A606E; /* Neutral button from body color family */
    --cyndaquil-button-neutral-text: var(--user-accent-cream);

    --cyndaquil-link-color: var(--user-accent-cream); /* Links also in cream */
    --cyndaquil-label-color: var(--user-primary-fire); /* Labels in Fire Orange */
    --cyndaquil-code-bg: #20303A; 
    --cyndaquil-code-text: var(--user-accent-cream);
    --cyndaquil-accordion-header-hover: var(--user-primary-fire);

    /* General UI Variables */
    --font-family-base: 'Noto Sans TC', 'Microsoft JhengHei', '微軟正黑體', Arial, sans-serif;
    --border-radius-main: 10px;
    --border-radius-small: 6px;
    --padding-card: 22px;
    --padding-input: 12px 15px;
    --padding-button: 12px 22px; 
    --shadow-focus-ring: rgba(225, 75, 22, 0.4); /* Fire orange focus ring */
}

/* 火球鼠吉祥物圖片樣式 */
.cyndaquil-mascot-image {
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* 強制所有子元素的 margin 和 padding 為 0 */
.cyndaquil-mascot-image,
.cyndaquil-mascot-image * {
    margin: 0 !重要;
    padding: 0 !重要;
}

.cyndaquil-mascot-image:hover {
    transform: scale(1.05) !important;
    filter: drop-shadow(0 0 15px rgba(225, 75, 22, 0.4)) !important;
}

/* 移除所有圖片相關的邊框和控制項 */
.cyndaquil-mascot-image .image-button-row,
.cyndaquil-mascot-image .download-button,
.cyndaquil-mascot-image .fullscreen-button,
.cyndaquil-mascot-image button[aria-label="Download"],
.cyndaquil-mascot-image button[title="View in full screen"],
.cyndaquil-mascot-image .gr-button-group,
.cyndaquil-mascot-image .image-controls {
    display: none !important;
    visibility: hidden !important;
}

/* 隱藏所有下載和複製按鈕 */
.gradio-container button[aria-label*="Download"],
.gradio-container button[aria-label*="Copy"],
.gradio-container button[title*="Download"],
.gradio-container button[title*="Copy"],
.gradio-container .download-button,
.gradio-container .copy-button,
.gradio-container [data-testid*="download"],
.gradio-container [data-testid*="copy"] {
    display: none !important;
    visibility: hidden !important;
}

/* 移除圖片容器的所有樣式 */
.cyndaquil-mascot-image .image-container,
.cyndaquil-mascot-image .gr-image,
.cyndaquil-mascot-image > div,
.cyndaquil-mascot-image [data-testid="image"] {
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* 確保圖片本身無邊框且無間距 */
.cyndaquil-mascot-image img {
    border: none !important;
    border-radius: 50% !important;
    box-shadow: none !important;
    outline: none !important;
    background: transparent !important;
    filter: drop-shadow(0 0 10px rgba(225, 75, 22, 0.3)) !important;
    margin: 0 !important;
    padding: 0 !important;
    display: block !important;
}

/* 移除任何可能的懸停效果邊框和間距 */
.cyndaquil-mascot-image *:hover,
.cyndaquil-mascot-image *:focus,
.cyndaquil-mascot-image *:active {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* 確保圖片容器沒有預設的 Gradio 樣式 */
.cyndaquil-mascot-image .gr-block,
.cyndaquil-mascot-image .gr-form,
.cyndaquil-mascot-image .gr-panel {
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
}

/* 頂部標題行樣式 */
.pc-header-row {
    margin-bottom: 20px !important;
    padding: 15px !important;
    background: linear-gradient(135deg, var(--cyndaquil-card-bg), var(--cyndaquil-bg-dark)) !important;
    border-radius: var(--border-radius-main) !important;
    border: 1px solid var(--cyndaquil-card-border) !important;
    align-items: center !important;
    box-shadow: 0 5px 15px var(--cyndaquil-card-shadow) !important;
}

html, body {
    color: var(--cyndaquil-text-primary) !important; 
}

.gradio-app, gradio-app {
    background: transparent !important; 
}

* {
    font-family: inherit !important;
    box-sizing: border-box;
}

.gradio-container .footer {
    display: none !important;
}

.gradio-container { 
    max-width: 1600px !important; 
    margin: 0 auto !important; 
    background: transparent !important; 
    padding: 20px !important;
    min-width: 800px !important;
    width: 100% !important;
}

.gr-interface {
    background: transparent !important; 
    padding: 0px !important; 
    border-radius: 0 !important;
    width: 100% !important;
    min-width: 800px !important;
}

/* 確保Gradio應用在載入時就有正確的尺寸 */
.gradio-app, gradio-app {
    width: 100% !important;
    min-width: 800px !important;
    background: transparent !important; 
}

/* 主要容器設定 */
.contain, .gr-container {
    width: 100% !important;
    min-width: 800px !important;
    max-width: 1600px !important;
    margin: 0 auto !important;
}

/* Card base style */
.pc-card {
    background-color: var(--cyndaquil-card-bg) !important;
    border: 1px solid var(--cyndaquil-card-border) !important;
    border-radius: var(--border-radius-main);
    padding: var(--padding-card);
    margin-bottom: 20px; 
    box-shadow: 0 5px 15px var(--cyndaquil-card-shadow);
}

/* Step card 步驟卡片樣式 */
.pc-step-card {
    position: relative;
    border-left: 5px solid var(--user-primary-fire) !important;
}

.pc-step-card > .gr-markdown h3::before {
    display: inline-block;
    margin-right: 8px;
    width: 28px;
    height: 28px;
    line-height: 26px;
    text-align: center;
    background-color: var(--user-primary-fire);
    color: white;
    border-radius: 50%;
    font-size: 0.9em;
}

/* Labels for inputs and Card Titles */
.gradio-container .label,
.gradio-container .gr-formlabel label span,
.gradio-container .gr-label,
.gradio-container .gr-checkbox label span,
.pc-card .gr-markdown > h3,
.pc-card > .gr-markdown:first-child > div > h3,
.pc-card > div > .gr-markdown > div > h3,
.pc-accordion > .gr-button
{
    color: var(--cyndaquil-label-color) !important; 
    font-weight: 700 !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    margin-bottom: 8px !important;
}
.pc-card > .gr-markdown:first-child > div > h3,
.pc-card > div > .gr-markdown > div > h3 {
    padding-bottom: 8px;
    border-bottom: 1px solid var(--cyndaquil-card-border);
}

.pc-card .gr-markdown > p, 
.pc-card .gr-markdown > ul > li {
    color: var(--cyndaquil-text-primary) !important; 
    font-size: 1em; 
    line-height: 1.7;
}

/* INPUT STYLING */
.gradio-container .gr-input-text input[type='text'],
.gradio-container .gr-textarea textarea,
.gradio-container div[data-testid="textbox"] textarea,
.gradio-container .gr-textbox textarea,
.gradio-container input[type="text"], 
.gradio-container input[type="number"],
.gradio-container input[type="email"],
.gradio-container input[type="password"],
.gradio-container textarea,
.gradio-container .gr-dropdown select, 
.gradio-container .gr-dropdown input[type="text"],
.gradio-container .gr-dropdown div[role="listbox"]
{
    background: var(--cyndaquil-input-bg) !important;
    color: var(--cyndaquil-text-primary) !important; 
    border: 1px solid var(--cyndaquil-input-border) !important;
    border-radius: var(--border-radius-small) !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3) !important; 
    padding: var(--padding-input) !important;
}
.gradio-container .gr-dropdown select {
    background-image: url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FCE671%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.4-5.4-13z%22/%3E%3C/svg%3E'); /* Arrow color to cream */
}

.gradio-container .gr-input-text input[type='text']::placeholder,
.gradio-container .gr-textarea textarea::placeholder,
.gradio-container div[data-testid="textbox"] textarea::placeholder,
.gradio-container .gr-textbox textarea::placeholder,
.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: var(--cyndaquil-text-secondary) !important;
    opacity: 1; 
}

.gradio-container .gr-input-text input[type='text']:focus,
.gradio-container .gr-textarea textarea:focus,
.gradio-container div[data-testid="textbox"] textarea:focus,
.gradio-container .gr-textbox textarea:focus,
.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container .gr-dropdown select:focus,
.gradio-container .gr-dropdown input[type="text"]:focus {
    border-color: var(--cyndaquil-accent-fire) !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.2), 0 0 0 3px var(--shadow-focus-ring) !important; 
}

/* 故事大綱專用樣式 - 火球鼠主題配色 */
#output-story-plan-textbox textarea,
#output-story-plan-textbox input,
div[data-testid="textbox"]#output-story-plan-textbox textarea,
.gradio-container #output-story-plan-textbox textarea,
.gradio-container #output-story-plan-textbox input[type="text"] {
    color: var(--cyndaquil-text-primary) !important; /* 主題奶油白文字 */
    background: linear-gradient(135deg, #3D5B6F 0%, #486882 100%) !important; /* 漸層藍灰背景 */
    border: 2px solid var(--user-accent-cream-dark) !important; /* 更深色的奶油黃邊框 */
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2), 0 1px 3px rgba(212, 181, 42, 0.4) !important; /* 內陰影 + 更深色黃外發光 */
}

#output-story-plan-textbox textarea:focus,
#output-story-plan-textbox input:focus,
div[data-testid="textbox"]#output-story-plan-textbox textarea:focus,
.gradio-container #output-story-plan-textbox textarea:focus,
.gradio-container #output-story-plan-textbox input[type="text"]:focus {
    color: var(--user-accent-cream) !important; /* 焦點時強調奶油黃文字 */
    background: linear-gradient(135deg, #425D73 0%, #516F8C 100%) !important; /* 焦點時更亮的漸層背景 */
    border-color: var(--user-primary-fire) !important; /* 焦點時火橙色邊框 */
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.15), 0 0 0 3px var(--shadow-focus-ring), 0 2px 8px rgba(225, 75, 22, 0.3) !important; /* 多層次陰影效果 */
}

#output-story-plan-textbox textarea::placeholder,
#output-story-plan-textbox input::placeholder,
div[data-testid="textbox"]#output-story-plan-textbox textarea::placeholder,
.gradio-container #output-story-plan-textbox textarea::placeholder,
.gradio-container #output-story-plan-textbox input[type="text"]::placeholder {
    color: var(--cyndaquil-text-secondary) !important; /* 使用主題次要文字顏色 */
    opacity: 0.9 !important;
}

/* Button Styles */
.gradio-container .gr-button {
    border-radius: var(--border-radius-small) !important;
    padding: var(--padding-button) !important;
    font-weight: 700;
    transition: all 0.15s ease-out;
    box-shadow: 0 2px 5px rgba(0,0,0,0.25), inset 0 1px 1px rgba(255,255,255,0.05) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid transparent !important; 
}
.gradio-container .gr-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,0.07) !important;
}
.gradio-container .gr-button:active {
    transform: translateY(0px);
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), inset 0 1px 2px rgba(0,0,0,0.1) !important;
}

/* Primary Button (Fire Orange) */
.gradio-container .gr-button.primary,
.gradio-container .greninja-primary-button.gr-button, 
.gradio-container .greninja-accent-button.gr-button { 
    background: var(--cyndaquil-button-primary-bg) !important;
    color: var(--cyndaquil-button-primary-text) !important;
    border-color: var(--cyndaquil-button-primary-bg) !important;
    text-shadow: 0 1px 1px rgba(0,0,0,0.3);
}
.gradio-container .gr-button.primary:hover,
.gradio-container .greninja-primary-button.gr-button:hover,
.gradio-container .greninja-accent-button.gr-button:hover {
    background: #C73A0F !important; /* Darker Fire */
    border-color: #C73A0F !important;
}

/* Secondary Button (Cream) */
.gradio-container .gr-button.secondary,
.gradio-container .greninja-secondary-button.gr-button {
    background: var(--cyndaquil-button-secondary-bg) !important;
    color: var(--cyndaquil-button-secondary-text) !important;
    border-color: var(--cyndaquil-button-secondary-bg) !important;
    text-shadow: 0 1px 1px rgba(0,0,0,0.1);
}
.gradio-container .gr-button.secondary:hover,
.gradio-container .greninja-secondary-button.gr-button:hover {
    background: #E0D060 !important; /* Darker Cream */
    border-color: #E0D060 !important;
    color: #302A10 !important;
}

/* Neutral Button (Body Blue-Grey family) */
.gradio-container .greninja-neutral-button.gr-button {
    background: var(--cyndaquil-button-neutral-bg) !important; 
    color: var(--cyndaquil-button-neutral-text) !important;
    border: 1px solid #5A788A !important; 
}
.gradio-container .greninja-neutral-button.gr-button:hover {
    background: #557080 !important; 
    border-color: #68889A !important;
}

/* Example Button (Subtle) */
.gradio-container .greninja-example-button.gr-button {
    background: rgba(252, 230, 113, 0.1) !important; /* Cream with alpha */
    color: var(--cyndaquil-accent-cream) !important;
    border: 1px solid rgba(252, 230, 113, 0.25) !important; 
    font-weight: 500 !important;
    padding: 8px 12px !important; 
    text-transform: none;
    letter-spacing: 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15) !important;
}
.gradio-container .greninja-example-button.gr-button:hover {
    background: rgba(225, 75, 22, 0.12) !important; /* Fire with alpha */
    border-color: var(--cyndaquil-accent-fire) !important; 
    color: var(--cyndaquil-accent-fire);
}

/* Markdown output styles */
.gr-output-markdown h1, .gr-output-markdown h2, .gr-output-markdown h3 {
    color: var(--cyndaquil-label-color) !important; 
    border-bottom: 1px solid var(--cyndaquil-card-border); 
}
.gr-output-markdown p, .gr-output-markdown li {
    color: var(--cyndaquil-text-primary) !important; 
}
.gr-output-markdown a {
    color: var(--cyndaquil-link-color) !important;
    border-bottom: 1px dotted var(--cyndaquil-link-color);
    font-weight: bold;
}
.gr-output-markdown a:hover {
    color: var(--user-primary-fire) !important; 
    border-bottom-color: var(--user-primary-fire);
}
.gr-output-markdown code {
    background: var(--cyndaquil-code-bg) !important; 
    color: var(--cyndaquil-code-text) !important;
    border: 1px solid var(--cyndaquil-card-border); 
}
.gr-output-markdown pre {
    background: var(--cyndaquil-code-bg) !important;
    border: 1px solid var(--cyndaquil-card-border) !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.25);
}

/* Accordion */
.pc-accordion > .gr-button { 
    color: var(--cyndaquil-link-color) !important; 
    border-bottom-color: var(--cyndaquil-card-border) !important;
}
.pc-accordion > .gr-button:hover, 
.pc-accordion > .gr-button[aria-expanded="true"] {
    color: var(--cyndaquil-accordion-header-hover) !important;
    border-bottom-color: var(--cyndaquil-accordion-header-hover) !important;
}
.pc-accordion-content {
    background: rgba(42, 64, 77, 0.3); /* Darker from main bg for depth */
}

/* Checkbox */
.gradio-container .gr-checkbox label span {
    color: var(--cyndaquil-text-primary) !important;
}
.gradio-container .gr-checkbox input[type="checkbox"] + span::before {
    border-color: var(--cyndaquil-input-border) !important;
    background: var(--cyndaquil-input-bg) !important;
}
.gradio-container .gr-checkbox input[type="checkbox"]:checked + span::before {
    background: var(--user-primary-fire) !important; 
    border-color: var(--user-primary-fire) !important;
}
.gradio-container .gr-checkbox input[type="checkbox"]:checked + span::after {
    border-color: #F0F0F0 !important; /* Light checkmark on fire bg */
}

/* Dropdown options */
.gradio-container .gr-dropdown ul.options {
    background: var(--cyndaquil-card-bg) !important; 
    border: 1px solid var(--cyndaquil-card-border) !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.35);
}
.gradio-container .gr-dropdown ul.options li.item {
    color: var(--cyndaquil-text-primary) !important;
    border-bottom: 1px solid var(--cyndaquil-input-border);
}
.gradio-container .gr-dropdown ul.options li.item:hover,
.gradio-container .gr-dropdown ul.options li.item.selected {
    background: var(--user-primary-fire) !important; 
    color: var(--cyndaquil-button-primary-text) !important; 
    border-bottom-color: var(--user-primary-fire) !important;
}

/* Main App Title */
.app-title-markdown h1 { 
    color: var(--user-primary-fire) !important; 
    text-shadow: 0 1px 2px rgba(0,0,0,0.5); 
}
.app-title-markdown > div > p { 
    color: var(--cyndaquil-text-primary) !important; 
}

/* Examples section */
.pc-examples-card .gr-examples .gr-sample-textbox { 
    border: 1px solid var(--cyndaquil-card-border) !important;
    background: var(--cyndaquil-input-bg) !important; 
    color: var(--cyndaquil-text-secondary) !important; 
}
.pc-examples-card .gr-examples .gr-sample-textbox:hover {
     border-color: var(--user-primary-fire) !important;
     background: var(--cyndaquil-card-bg) !important; 
}
.pc-examples-card .gr-examples .gr-sample-textbox.selected {
    border-color: var(--user-primary-fire) !important; 
    background: #402A1A !important; /* Darker, fire-tinted bg for selection */
    color: var(--user-accent-cream) !important;
}

/* 快速試玩範例標籤 */
.quick-examples-label {
    margin-bottom: 1px !important;
    margin-top: 15px !important;
}

.quick-examples-label h1,
.quick-examples-label h2,
.quick-examples-label h3,
.quick-examples-label p,
.quick-examples-label strong {
    color: var(--cyndaquil-accent-cream) !important;
    font-size: 0.9em !important;
    margin: 0 !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
}

/* 快速試玩範例按鈕容器 */
.pc-quick-examples-row {
    gap: 10px !important;
    margin-bottom: 5px !important;
}

/* 快速試玩範例按鈕樣式 */
.pc-quick-example-button.gr-button {
    background: rgba(252, 230, 113, 0.15) !important; /* Cream with low alpha */
    color: var(--cyndaquil-accent-cream) !important;
    border: 1px solid rgba(252, 230, 113, 0.3) !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    font-size: 0.85em !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    border-radius: 20px !important; /* 更圓的按鈕 */
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    transition: all 0.2s ease-out !important;
}

.pc-quick-example-button.gr-button:hover {
    background: rgba(252, 230, 113, 0.25) !important; 
    border-color: var(--cyndaquil-accent-cream) !important;
    color: var(--cyndaquil-accent-cream) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
}

.pc-quick-example-button.gr-button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
}

"""

# 自訂 HTML head 
custom_head = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#2A404D"> <!-- --cyndaquil-bg-dark for theme color -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0">
<style id="force-body-bg">
html, body {
    /* --cyndaquil-bg-dark, --cyndaquil-bg-gradient-end */
    background: linear-gradient(135deg, #2A404D 0%, #22333E 100%) !important; 
    min-height: 100vh;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}
.gradio-app, gradio-app, .gradio-container, .contain {
    background: transparent !important;
    width: 100% !important;
    min-width: 800px !important;
}
/* 確保在頁面載入時就設定正確的容器尺寸 */
.gradio-container {
    max-width: 1600px !important;
    margin: 0 auto !important;
    padding: 20px !important;
    width: 100% !important;
    min-width: 800px !important;
}
</style>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
body, * {
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', '微軟正黑體', Arial, sans-serif !important;
}
</style>
"""

with gr.Blocks(theme=None, css=custom_css, title="火球鼠の熱焰故事工房", head=custom_head) as demo:

    # 頂部標題區域，包含火球鼠圖片
    with gr.Row(elem_classes="pc-header-row"):
        with gr.Column(scale=5):
            gr.Markdown("""
            # 🔥 火球鼠の熱焰故事工房 ✨
            
            與火球鼠一起，用背上的火焰點燃無限的創作靈感，編織獨一無二的寶可夢冒險故事！
            """, elem_classes="app-title-markdown") # Main title
            
            # 快速試玩範例按鈕
            gr.Markdown("**快速試玩：**", elem_classes="quick-examples-label")
            with gr.Row(elem_classes="pc-quick-examples-row"):
                btn_example_1 = gr.Button("校園新夥伴", size="sm", elem_classes="pc-quick-example-button")
                btn_example_2 = gr.Button("辦公室幫手", size="sm", elem_classes="pc-quick-example-button")
                btn_example_3 = gr.Button("家庭小管家", size="sm", elem_classes="pc-quick-example-button")
                btn_example_4 = gr.Button("旅行好夥伴", size="sm", elem_classes="pc-quick-example-button")
                
        with gr.Column(scale=1, min_width=120):
            # 火球鼠圖片
            cyndaquil_image = gr.Image(
                value=os.path.join(os.path.dirname(__file__), "..", "cyndaquil.png"),
                label=None,
                show_label=False,
                container=False,
                width=150,
                height=150,
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False,
                elem_classes="cyndaquil-mascot-image"
            )

    # --- 主要內容區域：採用流程式設計，從上到下依照使用順序排列 ---
    with gr.Column():
        # 第1步：輸入故事基本資訊
        with gr.Column(elem_classes="pc-card pc-step-card"):
            gr.Markdown("### 第1步：輸入故事基本設定")
            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    input_theme = gr.Textbox(label="故事主題", placeholder="例如：意外的友誼、神秘的發現", scale=1, show_copy_button=False)
                    input_genre = gr.Dropdown(label="故事類型", choices=STORY_GENRES, value=STORY_GENRES[0], allow_custom_value=False, scale=1)
                with gr.Column(scale=1):
                    input_pokemon_names = gr.Textbox(label="登場寶可夢 (逗號分隔)", placeholder="例如：皮卡丘, 伊布", scale=1, show_copy_button=False)
                    input_include_abilities = gr.Checkbox(label="在故事中加入寶可夢的特性/能力", value=True)

        # 第2步：撰寫故事概要
        with gr.Column(elem_classes="pc-card pc-step-card"):
            gr.Markdown("### 第2步：撰寫您的故事概要")
            input_synopsis = gr.Textbox(
                label="故事概要 / 想法", 
                placeholder="詳細描述您的故事概念，或從上方的範例中選擇一個...", 
                lines=5,
                show_copy_button=False
            )
            with gr.Row():
                btn_get_suggestions = gr.Button("獲取寫作提示", elem_classes="greninja-accent-button")
                btn_generate_plan = gr.Button("產生故事大綱", variant="primary", elem_classes="greninja-primary-button")

        # 系統狀態與寫作建議 (放在中間以便用戶能隨時看到)
        with gr.Row():
            with gr.Column(scale=1, elem_classes="pc-card pc-status-card"):
                gr.Markdown("### 系統狀態")
                output_status = gr.Textbox(
                    label="系統狀態 / 訊息", 
                    lines=2, 
                    interactive=False, 
                    placeholder="系統更新與訊息將顯示在此...",
                    show_copy_button=False
                )
            with gr.Column(scale=1, elem_classes="pc-card pc-suggestions-card"):
                gr.Markdown("### 寫作建議")
                output_suggestions = gr.Markdown(
                    label="AI 提供的建議", 
                    elem_id="output-suggestions-markdown",
                )

        # 第3步：故事大綱 (可編輯)
        with gr.Column(elem_classes="pc-card pc-step-card"):
            gr.Markdown("### 第3步：故事大綱 (可編輯)")
            output_story_plan = gr.Textbox(
                label="產生的故事大綱", 
                lines=15,
                placeholder="故事大綱將在此顯示，您可以直接編輯...",
                elem_id="output-story-plan-textbox",
                show_copy_button=False
            )
            with gr.Row():
                btn_generate_story_from_plan = gr.Button(
                    "從大綱產生完整故事", 
                    variant="secondary", 
                    elem_classes="greninja-secondary-button"
                )

        # 第4步：完整故事
        with gr.Column(elem_classes="pc-card pc-step-card"):
            gr.Markdown("### 第4步：完整故事")
            output_full_story = gr.Markdown(
                label="產生的完整故事", 
                elem_id="output-full-story-markdown"
            )

    # --- 元件事件綁定 (保持不變) ---
    btn_generate_plan.click(
        fn=handle_generate_plan_click,
        inputs=[
            input_theme, input_genre, input_pokemon_names, 
            input_synopsis, input_include_abilities
        ],
        outputs=[output_story_plan, output_status]
    )

    btn_generate_story_from_plan.click(
        fn=handle_generate_story_from_plan_click,
        inputs=[
            input_theme, input_genre, input_pokemon_names, 
            input_synopsis, input_include_abilities, 
            output_story_plan
        ],
        outputs=[output_full_story, output_status]
    )
    
    btn_get_suggestions.click(
        fn=get_suggestions_only,
        inputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities],
        outputs=[output_suggestions]
    )
    
    # 快速試玩範例按鈕的事件綁定
    btn_example_1.click(
        fn=lambda: ["校園新夥伴", STORY_GENRES[1], "皮卡丘, 伊布", "高中生小明原本是個內向害羞的轉學生，在新學期第一天發現這所實驗性質的私立高中竟然允許學生攜帶寶可夢上課。他帶著從小陪伴他的皮卡丘來到新班級，卻因為緊張而不敢與同學交流。坐在隔壁的學級委員小華飼養著一隻聰明的伊布，注意到小明的孤單。當學校舉辦「寶可夢與人類合作」的專題研究時，小華主動邀請小明組隊。然而他們很快發現校園裡出現了奇怪的現象：圖書館的書本會自己移動、實驗室的器材莫名故障、甚至連學校的守護神雕像都開始發光。皮卡丘的電氣感應能力和伊布的適應性進化特質成為解謎的關鍵，而小明也在這次冒險中找到了真正的友誼，學會了勇敢表達自己。", True],
        outputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities]
    )
    
    btn_example_2.click(
        fn=lambda: ["辦公室的得力助手", STORY_GENRES[2], "喵喵, 卡比獸", "剛從大學畢業的小美懷著忐忑不安的心情來到東京市中心一棟摩天大樓上班，沒想到這家前衛的廣告公司竟然實施「寶可夢員工制度」。人事部安排給她的搭檔是一隻會說人話、戴著領帶的喵喵，專門負責整理文件和翻譯外國客戶的需求。然而這隻喵喵個性高傲又愛現，總是炫耀自己的「高學歷」，還會為了辦公室裡的小金魚鮑拉而分心。更讓小美頭痛的是，大樓一樓的保全卡比獸每天準時在午休時間於電梯門口倒頭就睡，導致所有員工都必須爬樓梯，但沒人有膽量叫醒牠。當公司接到一個重要的國際案子，而競爭對手派來神秘的商業間諜時，小美發現這些看似麻煩的寶可夢夥伴們其實各有神通，喵喵的敏銳觀察力和卡比獸的驚人直覺竟然成為守護公司機密的最佳防線。", False],
        outputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities]
    )
    
    btn_example_3.click(
        fn=lambda: ["家庭小管家", STORY_GENRES[6], "胖丁, 吉利蛋", "三十五歲的單親媽媽小雲每天在醫院擔任護理師，下班後還要照顧七歲的女兒小花和臥病在床的老奶奶，生活壓力讓她疲憊不堪。在朋友的建議下，她領養了兩隻寶可夢：一隻粉色的胖丁和一隻溫和的吉利蛋。起初小雲只是希望牠們能陪伴家人，沒想到這兩隻寶可夢竟然展現出驚人的照護天賦。胖丁發現小花每晚因為想念爸爸而失眠，便開始每晚為她唱搖籃曲，牠甜美的歌聲不僅讓小花安穩入睡，還意外改善了鄰居家嬰兒的睡眠問題。而吉利蛋則細心地照料著老奶奶，牠的蛋類營養補充和療癒能力讓奶奶的身體狀況逐漸好轉，甚至開始能下床走動。當小雲看著女兒和奶奶臉上重新綻放的笑容，她意識到家的溫暖不只來自血緣，更來自彼此真心的關懷與陪伴。", True],
        outputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities]
    )
    
    btn_example_4.click(
        fn=lambda: ["京都旅行的意外收穫", STORY_GENRES[0], "走路草, 櫻花寶", "大學情侶阿俊和小美計劃了一趟畢業旅行，選擇在櫻花盛開的季節造訪古都京都。他們原本只是想在清水寺拍攝唯美的畢業照片作為紀念，卻在參拜途中意外遇到一隻迷了路、看起來很焦急的走路草。這隻小寶可夢似乎在尋找什麼重要的東西，牠的葉片不停顫抖，眼中滿含淚水。善良的兩人決定暫停觀光計畫，跟隨走路草的引導穿過竹林小徑，來到一處遊客從未發現的秘密花園。在這裡，他們見到了傳說中只在特定時節才會現身的櫻花寶，牠正因為失去了世代守護的古老櫻花樹而憂傷不已。原來那棵神聖的櫻花樹因為環境變化而瀕臨枯死，而走路草一直在四處尋求幫助。透過阿俊的園藝知識和小美的細心照料，加上走路草的草系能力和櫻花寶的生命力量，他們合力拯救了這棵千年古樹。當櫻花再次綻放的那一刻，不僅見證了自然的奇蹟，也讓這對情侶明白了愛情如同花朵，需要用心呵護才能長久綻放。", True],
        outputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities]
    )

if __name__ == "__main__":
    if initialization_error:
        print(f"嚴重錯誤：由於服務初始化錯誤，Gradio 應用程式無法啟動: {initialization_error}")
        print("請確保您的 OPENAI_API_KEY 已正確設定在專案根目錄的 .env 檔案中，然後重新啟動。")
    else:
        print("正在啟動 Gradio 應用程式...")
        # 設定靜態檔案路徑
        static_files_path = os.path.dirname(__file__)
        
        demo.launch(
            server_port=7861,     # 改用不同的端口
            share=True,
            show_error=False,     # 隱藏不必要的錯誤訊息
            quiet=False,          # 保持一些輸出以便調試
            favicon_path=None,    # 避免 favicon 載入錯誤
            show_api=False,       # 隱藏 API 文檔以減少資源請求
            prevent_thread_lock=False,
            server_name="127.0.0.1"  # 明確指定服務器地址
        )