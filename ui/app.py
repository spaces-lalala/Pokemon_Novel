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

        llm_service_instance = LLMService(model_name="gpt-4-turbo")
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

DEFAULT_SYNOPSIS_EXAMPLES = {
    "範例一：迷途的夥伴": "兩隻來自不同地區、性格迥異的寶可夢在一場意外中一同迷失在未知的森林。牠們必須克服彼此的差異，學會合作，才能找到回家的路，並在過程中建立深厚的友誼。",
    "範例二：神秘的遺物": "一位年輕的寶可夢研究員在古老的遺址中發現了一個從未見過的神秘道具。這個道具似乎與某個傳說中的寶可夢有關，並引來了企圖不明的組織覬覦。",
    "範例三：成長的試煉": "一隻膽小怯懦的寶可夢，為了保護自己重要的夥伴/訓練家，必須鼓起勇氣面對自己最大的恐懼，並在關鍵時刻爆發出驚人的潛力，完成一次重要的蛻變。",
    "範例四：被遺忘的傳說": "在一個偏遠的小村莊，流傳著一個關於守護神寶可夢的古老傳說。隨著時間的流逝，傳說漸漸被遺忘，村莊也面臨了危機。主角們需要重新喚醒傳說，找到守護神，解救村莊。"
}

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
        status_updates += "正在產生故事大綱...\\n"
        raw_story_plan_text = await cot_engine_instance.generate_story_plan(
            theme, genre, pokemon_names, synopsis, include_abilities
        )
        
        # Clean up the plan text to remove any lingering review markers, just in case
        # Prefer content after "修訂後故事大綱:" if present, otherwise use the whole text
        # and then strip any "評估回饋:"
        plan_content_marker = "修訂後故事大綱:"
        feedback_marker = "評估回饋:"
        
        if plan_content_marker in raw_story_plan_text:
            story_plan_text = raw_story_plan_text.split(plan_content_marker, 1)[-1].strip()
        else:
            story_plan_text = raw_story_plan_text
        
        if feedback_marker in story_plan_text:
             # If feedback marker is still in the content, it implies it was part of the "revised_content"
             # and not a separate section. We will take content before it.
            story_plan_text = story_plan_text.split(feedback_marker, 1)[0].strip()

        if not story_plan_text: # Fallback if cleaning results in empty string
            story_plan_text = "故事大綱生成成功，但內容解析後為空。請檢查日誌。"
            status_updates += "故事大綱內容解析後為空。"
        else:
            status_updates += "故事大綱產生完成！您現在可以編輯下方的大綱，然後點擊「從大綱產生完整故事」。"
        
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
        status_updates += "正在根據大綱產生完整故事...\\n"
        raw_full_story_text = await cot_engine_instance.generate_story_from_plan(
            theme, genre, pokemon_names, synopsis, edited_story_plan, include_abilities
        )

        # Clean up the full story text
        story_content_marker = "修訂後完整故事:"
        feedback_marker = "評估回饋:"

        if story_content_marker in raw_full_story_text:
            full_story_text = raw_full_story_text.split(story_content_marker, 1)[-1].strip()
        else:
            full_story_text = raw_full_story_text
            
        if feedback_marker in full_story_text:
            full_story_text = full_story_text.split(feedback_marker, 1)[0].strip()

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

def handle_download_text_as_file(text_content: str, filename_prefix: str) -> Optional[str]:
    if not text_content or not text_content.strip():
        print(f"下載請求 '{filename_prefix}' 但內容為空。")
        return None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", 
            encoding="utf-8", 
            suffix=".txt", 
            prefix=f"{filename_prefix}_", 
            delete=False,
            dir=tempfile.gettempdir()
        ) as tmp_file:
            tmp_file.write(text_content)
            tmp_file_path = tmp_file.name
        print(f"內容 '{filename_prefix}' 已寫入暫存檔案: {tmp_file_path}")
        return tmp_file_path
    except Exception as e:
        print(f"建立暫存檔案 '{filename_prefix}' 時發生錯誤: {e}")
        return None

custom_css = """
/* 火球鼠主題配色 - Cyndaquil Dark Theme */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

:root {
    /* User Provided Palette (Cyndaquil) */
    --user-primary-fire: #E14B16; /* Flame Orange-Red */
    --user-secondary-body: #375464; /* Body Blue-Grey */
    --user-accent-cream: #FCE671; /* Belly Cream-Yellow */

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
    margin: 0 !important;
    padding: 0 !important;
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
    padding: 20px; 
}

.gr-interface {
    background: transparent !important; 
    padding: 0px; 
    border-radius: 0;
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

"""

# 自訂 HTML head 
custom_head = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#2A404D"> <!-- --cyndaquil-bg-dark for theme color -->
<style id="force-body-bg">
html, body {
    /* --cyndaquil-bg-dark, --cyndaquil-bg-gradient-end */
    background: linear-gradient(135deg, #2A404D 0%, #22333E 100%) !important; 
    min-height: 100vh;
    margin: 0 !important;
    padding: 0 !important;
}
.gradio-app, gradio-app, .gradio-container, .contain {
    background: transparent !important;
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
        with gr.Column(scale=1, min_width=120):
            # 火球鼠圖片
            cyndaquil_image = gr.Image(
                value=os.path.join(os.path.dirname(__file__), "..", "cyndaquil.png"),
                label=None,
                show_label=False,
                container=False,
                width=150,  # 從 100 放大到 150 (1.5倍)
                height=150, # 從 100 放大到 150 (1.5倍)
                interactive=False,
                show_download_button=False,
                show_fullscreen_button=False,
                elem_classes="cyndaquil-mascot-image"
            )

    # --- 頂部核心輸入區 (Card) ---
    with gr.Column(elem_classes="pc-card pc-main-inputs-card"): # Added pc-card
        gr.Markdown("### 🚀 快速開始您的故事設定") # Card title
        with gr.Row(elem_classes="pc-main-inputs-row"):
            input_theme = gr.Textbox(label="故事主題", placeholder="例如：意外的友誼、神秘的發現", scale=2)
            input_genre = gr.Dropdown(label="故事類型", choices=STORY_GENRES, value=STORY_GENRES[0], allow_custom_value=False, scale=1)
            input_pokemon_names = gr.Textbox(label="登場寶可夢 (逗號分隔)", placeholder="例如：皮卡丘, 伊布", scale=2)

    # --- 主內容區 (左右分欄) ---
    with gr.Row(elem_classes="pc-content-columns"):
        # --- 左側欄 ---
        with gr.Column(scale=2, elem_classes="pc-left-column"): # Adjusted scale for better balance
            with gr.Column(elem_classes="pc-card pc-synopsis-card"): # Synopsis input as a card
                gr.Markdown("### ✏️ 撰寫您的故事概要")
                input_synopsis = gr.Textbox(
                    label="故事概要 / 想法", 
                    placeholder="詳細描述您的故事概念...", 
                    lines=10 # Increased lines for PC
                )
            input_include_abilities = gr.Checkbox(label="在故事中加入寶可夢的特性/能力", value=True)
            
            with gr.Column(elem_classes="pc-card pc-examples-input-card"): # Synopsis examples as a card
                gr.Markdown("💡 **故事概要範例 (點擊填入)**")
                with gr.Column(elem_classes="pc-synopsis-examples-grid"):
                    for title, text in DEFAULT_SYNOPSIS_EXAMPLES.items():
                        btn = gr.Button(title, elem_classes="greninja-example-button") # Will be styled by Togepi's example button style
                        btn.click(lambda s=text: s, inputs=None, outputs=input_synopsis)
            
            with gr.Column(elem_classes="pc-card pc-actions-card"): # Action buttons as a card
                gr.Markdown("### ✨ 生成內容")
                with gr.Row(elem_classes="pc-action-buttons-row"):
                    btn_get_suggestions = gr.Button("💡 獲取寫作提示", elem_classes="greninja-accent-button") # Mapped to Togepi primary button
                    btn_generate_plan = gr.Button("📝 產生故事大綱", variant="primary", elem_classes="greninja-primary-button") # Mapped to Togepi primary button
        
        # --- 右側欄 ---
        with gr.Column(scale=3, elem_classes="pc-right-column"): # Adjusted scale for better balance
            with gr.Column(elem_classes="pc-card pc-status-card"): # Status output as a card
                gr.Markdown("### 📢 系統狀態")
                output_status = gr.Textbox(
                    label="系統狀態 / 訊息", 
                    lines=3, 
                    interactive=False, 
                    placeholder="系統更新與訊息將顯示在此...",
                    elem_classes="pc-status-output"
                )
            
            with gr.Column(elem_classes="pc-card pc-suggestions-card"): # Suggestions as a card
                with gr.Accordion("💡 寫作建議 (點擊展開/收合)", open=False, elem_classes="pc-accordion"):
                    output_suggestions = gr.Markdown(label="AI 提供的建議", elem_id="output-suggestions-markdown", elem_classes="pc-suggestions-output")

            with gr.Column(elem_classes="pc-card pc-plan-card"): # Story plan as a card
                with gr.Accordion("📖 故事大綱 (可編輯)", open=True, elem_classes="pc-accordion"):
                    with gr.Column(elem_classes="pc-accordion-content"):
                        output_story_plan = gr.Markdown(label="產生的故事大綱", elem_id="output-story-plan-markdown")
                        with gr.Row(elem_classes="pc-download-button-row"):
                            btn_download_plan = gr.Button("📥 下載大綱", elem_classes="greninja-neutral-button")
                        download_plan_file = gr.File(label="下載大綱檔案", visible=False, interactive=False)
                btn_generate_story_from_plan = gr.Button(
                    "📜 從上方大綱產生完整故事", 
                    variant="secondary", 
                    elem_classes="greninja-secondary-button", 
                    #elem_id="generate-story-full-width-button" 
                )
            
            with gr.Column(elem_classes="pc-card pc-story-card"): # Full story as a card
                with gr.Accordion("📚 完整故事", open=True, elem_classes="pc-accordion"):
                    with gr.Column(elem_classes="pc-accordion-content"):
                        output_full_story = gr.Markdown(label="產生的完整故事", elem_id="output-full-story-markdown")
                        with gr.Row(elem_classes="pc-download-button-row"):
                            btn_download_story = gr.Button("📥 下載故事", elem_classes="greninja-neutral-button")
            download_story_file = gr.File(label="下載故事檔案", visible=False, interactive=False)

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

    btn_download_plan.click(
        fn=handle_download_text_as_file,
        inputs=[output_story_plan, gr.Textbox(value="story_plan", visible=False)],
        outputs=download_plan_file,
        show_progress=False
    )

    btn_download_story.click(
        fn=handle_download_text_as_file,
        inputs=[output_full_story, gr.Textbox(value="full_story", visible=False)],
        outputs=download_story_file,
        show_progress=False
    )
    
    # --- Examples Section (Card) ---
    with gr.Column(elem_classes="pc-card pc-examples-card"): # Examples as a card
        gr.Markdown("### ✨ 快速試玩範例 ✨")
        gr.Examples(
            examples=[
                ["意外的友誼", STORY_GENRES[0], "皮卡丘, 波克比", "一隻迷路的皮卡丘遇到了一隻剛孵化的波克比，牠們一起踏上了尋找皮卡丘訓練家的旅程，並遇到了各種挑戰。", True],
                ["幸運日", STORY_GENRES[6], "波克比, 吉利蛋", "波克比不小心打翻了吉利蛋的藥水，卻意外配置出了能帶來超級好運的配方，引發了一連串幸運事件。", False],
                ["守護彩虹的蛋", STORY_GENRES[3], "波克比, 鳳王", "古老的傳說中，只有最純真的波克比才能找到傳說中鳳王守護的彩虹蛋，為世界帶來和平與幸福。", True],
                ["尋找神秘的搖籃曲", STORY_GENRES[4], "波克比, 胖丁", "波克比晚上睡不著，聽說森林深處有隻胖丁會唱最美的搖籃曲，於是決定和朋友一起去找牠。", True],
                ["搗蛋的鏡子模仿者", STORY_GENRES[1], "波克比, 魔尼尼", "一隻愛惡作劇的魔尼尼複製了波克比的樣子到處搗蛋，真正的波克比必須想辦法證明自己的清白。", False],
            ],
            inputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities],
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