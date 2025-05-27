import gradio as gr
import asyncio
from typing import Optional, Tuple
import tempfile
import os

# Adjust imports based on your project structure if these are not found directly
# This assumes that when running `python -m ui.app` or `python ui/app.py` (with PYTHONPATH set),
# the `core` and `config` directories are discoverable.
try:
    from core.llm_services import LLMService, OpenAIConfigError
    from core.cot_engine import CoTEngine, StoryGenerationError
    from config.settings import settings
except ModuleNotFoundError:
    # This block is for easier direct execution from the ui folder during development,
    # but for packaging or robust execution, ensure PYTHONPATH is set correctly or use `python -m ui.app`.
    import sys
    import os
    # Add project root to sys.path to allow finding core and config modules
    # This is a common pattern but might need adjustment based on how you run the app
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from core.llm_services import LLMService, OpenAIConfigError
    from core.cot_engine import CoTEngine, StoryGenerationError
    from config.settings import settings

# --- Global instances --- 
# These will be initialized once when the script is loaded.
llm_service_instance: Optional[LLMService] = None
cot_engine_instance: Optional[CoTEngine] = None
initialization_error: Optional[str] = None

def initialize_services():
    """Initialize the LLM and CoT engine services."""
    global llm_service_instance, cot_engine_instance, initialization_error
    try:
        if not settings.OPENAI_API_KEY:
            initialization_error = "OpenAI API Key not found. Please set OPENAI_API_KEY in your .env file in the project root."
            print(f"Initialization Error: {initialization_error}")
            return

        # Consider using a more general model from settings if defined, or default to gpt-3.5-turbo for cost/speed in UI.
        # For final use, you might want to use "gpt-4-turbo" as initially planned.
        llm_service_instance = LLMService(model_name="gpt-4-turbo") # Or use a model from settings
        cot_engine_instance = CoTEngine(llm_service=llm_service_instance)
        print("LLMService and CoTEngine initialized successfully for Gradio app.")
    except OpenAIConfigError as e:
        initialization_error = f"OpenAI Configuration Error during initialization: {e}"
        print(initialization_error)
    except Exception as e:
        initialization_error = f"An unexpected error occurred during service initialization: {e}"
        print(initialization_error)

# Initialize services when the script is loaded by Gradio
initialize_services()

# --- Story Genres List ---
# Commonly used story genres, can be expanded.
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

# --- Gradio State Variables (if needed for more complex interactions) ---
# For this change, we pass the plan directly from the editable textbox.

# --- Gradio Handler Functions ---

async def handle_generate_plan_click(
    theme: str,
    genre: str, 
    pokemon_names: str,
    synopsis: str,
    include_abilities: bool
) -> Tuple[str, str]: # plan, status
    """Handles the 'Generate Story Plan' button click."""
    if initialization_error or not cot_engine_instance:
        error_message = f"服務初始化失敗: {initialization_error or '未知錯誤'}"
        return "", error_message
    
    if not all([theme, genre, pokemon_names, synopsis]):
        return "", "請填寫所有必填欄位：故事主題、故事類型、登場寶可夢、以及故事概要。"

    status_updates = f"開始產生類型為「{genre}」的故事大綱...（納入特性：{'是' if include_abilities else '否'}）\n"
    story_plan_text = ""

    try:
        status_updates += "Generating story plan...\n"
        story_plan_text = await cot_engine_instance.generate_story_plan(
            theme, genre, pokemon_names, synopsis, include_abilities
        )
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
    theme: str, # Original theme
    genre: str, # Original genre
    pokemon_names: str, # Original Pokémon names
    synopsis: str, # Original synopsis
    include_abilities: bool, # Original include_abilities choice
    edited_story_plan: str # The (potentially) edited story plan from the textbox
) -> Tuple[str, str]: # story, status
    """Handles the 'Generate Full Story from Plan' button click."""
    if initialization_error or not cot_engine_instance:
        error_message = f"服務初始化失敗: {initialization_error or '未知錯誤'}"
        return "", error_message

    if not edited_story_plan.strip():
        return "", "故事大綱為空，請先產生或手動輸入大綱內容。"
    
    if not all([theme, genre, pokemon_names, synopsis]): # Check original inputs again for safety
        return "", "原始輸入欄位（主題、類型、寶可夢、概要）不完整，請確保它們在產生大綱時已填寫。"

    status_updates = f"根據您提供的大綱，開始產生類型為「{genre}」的完整故事...（納入特性：{'是' if include_abilities else '否'}）\n"
    full_story_text = ""

    try:
        status_updates += "Generating full story from plan...\n"
        full_story_text = await cot_engine_instance.generate_story_from_plan(
            theme, genre, pokemon_names, synopsis, edited_story_plan, include_abilities
        )
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
    """Handles the 'Get Suggestions' button click."""
    if initialization_error or not cot_engine_instance:
        return f"服務初始化失敗: {initialization_error or '未知錯誤'}"
    
    if not any([theme, pokemon_names, synopsis]): # Genre is always present from dropdown, so no need to check it here specifically for emptiness of all fields.
        return f"請至少在「故事主題」、「登場寶可夢」或「故事概要」中輸入一些內容以獲取建議。類型（'{genre}'）已選。納入特性：{'是' if include_abilities else '否'}。"
    
    try:
        suggestions = await cot_engine_instance.get_input_refinement_suggestions(theme, genre, pokemon_names, synopsis, include_abilities)
        return suggestions if suggestions else "目前沒有特別的建議，您的輸入看起來不錯，或者可以嘗試再補充更多細節！"
    except Exception as e:
        error_msg = f"獲取建議時發生錯誤: {e}"
        print(error_msg)
        return error_msg

# --- Download Handler Functions ---
def handle_download_text_as_file(text_content: str, filename_prefix: str) -> Optional[str]:
    """
    Creates a temporary .txt file with the given text content and returns its path for download.

    Args:
        text_content: The string content to write to the file.
        filename_prefix: A prefix for the temporary filename (e.g., "story_plan").

    Returns:
        The path to the temporary file if content is provided, otherwise None.
    """
    if not text_content or not text_content.strip():
        # Optionally, could raise an error or return a message to be displayed in status
        print(f"Download request for '{filename_prefix}' but content is empty.")
        return None # Returning None should prevent Gradio File from showing a download

    try:
        # Create a temporary file that Gradio can serve
        # We use delete=False because Gradio needs to access it after this function returns.
        # Consideration for server environments: these files should be cleaned up periodically.
        with tempfile.NamedTemporaryFile(
            mode="w", 
            encoding="utf-8", 
            suffix=".txt", 
            prefix=f"{filename_prefix}_", 
            delete=False,
            dir=tempfile.gettempdir() # Explicitly use system temp dir
        ) as tmp_file:
            tmp_file.write(text_content)
            tmp_file_path = tmp_file.name
        print(f"Content for '{filename_prefix}' written to temporary file: {tmp_file_path}")
        return tmp_file_path
    except Exception as e:
        print(f"Error creating temporary file for '{filename_prefix}': {e}")
        # Optionally, update a status component here to inform the user
        return None

# --- Gradio Interface Definition ---

# Custom CSS for better styling (optional)
custom_css = """
body {
    font-family: 'Arial', '微軟正黑體', 'Microsoft JhengHei', sans-serif;
    background-color: #0D1117 !important; /* Very dark background (e.g., GitHub dark) */
    color: #C9D1D9 !important; /* Light text color (e.g., GitHub dark text) */
}

.gr-interface {
    background-color: transparent !important;
    padding: 20px;
}

/* General Input/Textbox/Dropdown Styling */
.gradio-container .gr-input,
.gradio-container .gr-textbox textarea,
.gradio-container .gr-dropdown select {
    background-color: #161B22 !important; /* Dark input background */
    color: #C9D1D9 !important; /* Light text in input */
    border: 1px solid #343E6C !important; /* Primary as border */
    border-radius: 6px !important;
}
.gradio-container .gr-input::placeholder,
.gradio-container .gr-textbox textarea::placeholder {
    color: #768390 !important; /* Dimmer light placeholder text */
}
.gradio-container label > .label-text {
    color: #E4AD9E !important; /* Secondary for label text (for contrast and style) */
    font-weight: bold;
}

/* Default Button Styling */
.gradio-container .gr-button {
    background-color: #21262D !important; /* Dark button default (e.g., GitHub dark button) */
    color: #C9D1D9 !important; /* Light text */
    border: 1px solid #30363D !important; /* Dark border */
    border-radius: 6px !important;
    padding: 10px 15px !important;
    font-weight: bold;
    transition: background-color 0.2s ease, border-color 0.2s ease;
}
.gradio-container .gr-button:hover {
    background-color: #30363D !important;
    border-color: #8B949E !important;
}

/* Primary Button Styling (variant="primary" or specific class) */
.gradio-container .gr-button.primary,
.gradio-container button[class*="primary_"].gr-button, /* Covers classes like gradio-primary-button */
.gradio-container .lucario-primary-button.gr-button {
    background-color: #343E6C !important; /* Primary color */
    color: #FFFFFF !important;
    border: 1px solid #5A6A9C !important; /* Slightly lighter primary for border */
}
.gradio-container .gr-button.primary:hover,
.gradio-container button[class*="primary_"].gr-button:hover,
.gradio-container .lucario-primary-button.gr-button:hover {
    background-color: #434F81 !important; /* Lighter shade of primary */
    border-color: #6A7AAF !important;
}

/* Secondary Button Styling (variant="secondary" or specific class) */
.gradio-container .gr-button.secondary,
.gradio-container button[class*="secondary_"].gr-button,
.gradio-container .lucario-secondary-button.gr-button {
    background-color: #E4AD9E !important; /* Secondary color */
    color: #26130D !important; /* Dark text for contrast on light pink */
    border: 1px solid #D99A8B !important; /* Darker secondary for border */
}
.gradio-container .gr-button.secondary:hover,
.gradio-container button[class*="secondary_"].gr-button:hover,
.gradio-container .lucario-secondary-button.gr-button:hover {
    background-color: #D99A8B !important; /* Darker shade of secondary */
    border-color: #C98A7B !important;
}

/* Accent Button Styling */
.gradio-container .lucario-accent-button.gr-button {
    background-color: #64DCFC !important; /* Accent color */
    color: #003440 !important; /* Dark text for contrast on cyan */
    border: 1px solid #50B0C8 !important; /* Darker accent for border */
}
.gradio-container .lucario-accent-button.gr-button:hover {
    background-color: #50B0C8 !important; /* Darker shade of accent */
    border-color: #3A8CA0 !important;
}

/* Neutral Button Styling (for download, etc.) */
.gradio-container .lucario-neutral-button.gr-button {
    background-color: #21262D !important; /* Consistent with default dark button */
    color: #C9D1D9 !important;
    border: 1px solid #30363D !important;
}
.gradio-container .lucario-neutral-button.gr-button:hover {
    background-color: #30363D !important;
    border-color: #8B949E !important;
}

/* Example Button Styling (for synopsis examples) */
.gradio-container .lucario-example-button.gr-button {
    background-color: transparent !important;
    color: #64DCFC !important; /* Accent color for text */
    border: 1px solid #343E6C !important; /* Primary border */
    font-weight: normal !important;
    padding: 6px 12px !important; /* Adjusted padding */
}
.gradio-container .lucario-example-button.gr-button:hover {
    background-color: rgba(100, 220, 252, 0.1) !important; /* Slight accent background on hover */
    border-color: #64DCFC !important; /* Accent border on hover */
    color: #7AFEFF !important;
}

/* Markdown Styling */
.gr-output-markdown h1, .gr-output-markdown h2, .gr-output-markdown h3 {
    color: #E4AD9E !important; /* Secondary for headers */
    border-bottom: 1px solid #343E6C; /* Primary for underline */
    padding-bottom: 0.3em;
    margin-top: 1em;
    margin-bottom: 0.5em;
}
.gr-output-markdown p, .gr-output-markdown li {
    color: #C9D1D9 !important; /* Light text for markdown content */
    line-height: 1.6;
}
.gr-output-markdown a {
    color: #64DCFC !important; /* Accent for links */
    text-decoration: none;
}
.gr-output-markdown a:hover {
    text-decoration: underline;
}
.gr-output-markdown code {
    background-color: #161B22 !important; /* Dark input background for inline code */
    color: #E4AD9E !important; /* Secondary for code text */
    padding: 0.2em 0.4em;
    margin: 0 0.1em;
    font-size: 85%;
    border-radius: 6px;
    border: 1px solid #343E6C; /* Primary border for inline code */
}
.gr-output-markdown pre { /* Code blocks */
    background-color: #161B22 !important;
    border: 1px solid #343E6C !important; /* Primary border */
    border-radius: 6px;
    padding: 1em;
    overflow-x: auto;
}
.gr-output-markdown pre code { /* Code inside pre, reset some inline styles */
    background-color: transparent !important;
    padding: 0;
    margin: 0;
    border: none !important;
    font-size: inherit; /* Use pre's font size */
}


/* Accent color usage example - for .highlight-accent class */
.highlight-accent {
    border-left: 4px solid #64DCFC !important; /* ACCENT color for a left border */
    background-color: rgba(100, 220, 252, 0.05) !important; /* Very slight accent background */
    padding: 10px !important;
    margin-bottom: 10px;
    border-radius: 4px;
}

/* Tab Styling (if using gr.Tabs) */
.gradio-container .tabs > .tab-nav > button.selected {
    color: #64DCFC !important; /* Accent for selected tab text */
    border-bottom: 2px solid #64DCFC !important; /* Accent for underline */
    background: transparent !important;
}
.gradio-container .tabs > .tab-nav > button {
    color: #768390 !important; /* Dimmer light for unselected tab text */
    background: transparent !important;
    font-weight: bold;
}

/* Checkbox styling */
.gradio-container .gr-checkbox {
    color: #C9D1D9 !important; /* Light text for checkbox label */
}
.gradio-container .gr-checkbox input[type="checkbox"] + span::before { /* Unchecked box style */
    border-color: #343E6C !important; /* Primary border */
    background-color: #161B22 !important; /* Dark input background */
}
.gradio-container .gr-checkbox input[type="checkbox"]:checked + span::before { /* Checked box style */
    background-color: #64DCFC !important; /* Accent color for checked */
    border-color: #64DCFC !important;
}
.gradio-container .gr-checkbox input[type="checkbox"]:checked + span::after { /* Checkmark */
    border-color: #0D1117 !important; /* Dark checkmark for contrast on accent */
}

/* Dropdown selected value text */
.gradio-container .gr-dropdown div[data-testid="dropdown-value-text"] {
     color: #C9D1D9 !important;
}
/* Styling for dropdown items when open */
.gradio-container .gr-dropdown ul.options li.item {
    background-color: #161B22 !important;
    color: #C9D1D9 !important;
}
.gradio-container .gr-dropdown ul.options li.item:hover,
.gradio-container .gr-dropdown ul.options li.item.selected {
    background-color: #343E6C !important; /* Primary on hover/selected */
    color: #FFFFFF !important;
}

"""

with gr.Blocks(theme=None, css=custom_css, title="寶可夢宇宙 - 故事生成助手") as demo:
    gr.Markdown("""
    # AI 寶可夢短篇小說產生器 🐉📝
    
    歡迎！讓我們一起來創作獨一無二的寶可夢冒險故事吧！
    請您提供故事主題、登場的寶可夢以及基本的故事情節，AI 將會為您編織一篇精彩的故事。
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 步驟一：您的故事素材")
            input_theme = gr.Textbox(label="故事主題", placeholder="例如：意外的友誼、神秘的發現、前往傳說之地旅程")
            input_genre = gr.Dropdown(label="故事類型", choices=STORY_GENRES, value=STORY_GENRES[0], allow_custom_value=False)
            input_pokemon_names = gr.Textbox(label="登場寶可夢 (請用逗號分隔)", placeholder="例如：皮卡丘, 伊布, 噴火龍")
            input_synopsis = gr.Textbox(label="故事概要 / 想法", placeholder="例如：兩隻敵對的寶可夢意外一同迷路，必須同心協力才能找到回家的路。一位訓練家踏上尋找夢幻寶可夢的旅程。", lines=4)
            input_include_abilities = gr.Checkbox(label="在故事中加入寶可夢的特性/能力", value=True)
            
            gr.Markdown("💡 **故事概要範例 (點擊填入)**")
            with gr.Row():
                for title, text in DEFAULT_SYNOPSIS_EXAMPLES.items():
                    # Use a unique object for each button's click method to pass the correct text
                    # Passing `text` directly to lambda would cause late binding issues in a loop
                    # One way is to use a helper or functools.partial, or ensure unique scope
                    btn = gr.Button(title, scale=1, elem_classes="lucario-example-button")
                    btn.click(lambda s=text: s, inputs=None, outputs=input_synopsis)
            
            with gr.Row():
                btn_get_suggestions = gr.Button("💡 獲取寫作提示", elem_classes="lucario-accent-button")
                btn_generate_plan = gr.Button("📝 產生故事大綱", variant="primary", elem_classes="lucario-primary-button") # Changed button
        
        with gr.Column(scale=2):
            gr.Markdown("### 步驟二：AI 故事創作輔助")
            output_status = gr.Textbox(label="狀態 / 錯誤訊息", lines=3, interactive=False, placeholder="系統更新與錯誤訊息將會顯示在此處...")
            output_suggestions = gr.Markdown(label="寫作建議") # Suggestions output remains Markdown
            
            gr.Markdown("### 步驟三：故事大綱 (可編輯)")
            output_story_plan = gr.Markdown(label="產生的故事大綱") # Plan output is now Markdown
            btn_download_plan = gr.Button("📥 下載故事大綱 (.txt)", elem_classes="lucario-neutral-button")
            download_plan_file = gr.File(label="下載大綱檔案", visible=False, interactive=False)

            btn_generate_story_from_plan = gr.Button("📜 從上方大綱產生完整故事", variant="secondary", elem_classes="lucario-secondary-button")
            
            gr.Markdown("### 步驟四：完整故事")
            output_full_story = gr.Markdown(label="產生的完整故事") # Full story output is now Markdown
            btn_download_story = gr.Button("📥 下載完整故事 (.txt)", elem_classes="lucario-neutral-button")
            download_story_file = gr.File(label="下載故事檔案", visible=False, interactive=False)

    # --- Event Handlers ---
    btn_generate_plan.click(
        fn=handle_generate_plan_click,
        inputs=[
            input_theme, input_genre, input_pokemon_names, 
            input_synopsis, input_include_abilities
        ],
        outputs=[output_story_plan, output_status] # Plan and status
    )

    btn_generate_story_from_plan.click(
        fn=handle_generate_story_from_plan_click,
        inputs=[
            input_theme, input_genre, input_pokemon_names, 
            input_synopsis, input_include_abilities, 
            output_story_plan # Pass the potentially edited story plan
        ],
        outputs=[output_full_story, output_status] # Full story and status
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
        inputs=[output_full_story, gr.Textbox(value="full_story", visible=False)], # output_full_story is Markdown, need its value
        outputs=download_story_file,
        show_progress=False
    )
    
    gr.Examples(
        examples=[
            ["意外的友誼", STORY_GENRES[0], "皮卡丘, 伊布", "一隻皮卡丘和一隻伊布原本屬於互相競爭的訓練家，在一場暴風雨中一起迷路了，牠們必須學會合作才能找到回家的路。", True],
            ["勇敢的寶可夢面對最大的恐懼", STORY_GENRES[0], "小鋸鱷", "一隻小小的小鋸鱷非常害怕高處，但牠必須爬上一棵高聳的大樹，為生病的朋友摘取稀有的果實。", True],
            ["尋找傳說中的寶可夢", STORY_GENRES[3], "卡蒂狗, 風速狗", "一位年輕的訓練家和她的卡蒂狗聽說了傳說中的風速狗居住在火山之巔的故事，決定一同前往尋找牠。", True],
            ["寶可夢華麗大賽的挑戰", STORY_GENRES[6], "狩獵鳳蝶, 毒粉蛾", "兩位訓練家和他們的寶可夢在地區的寶可夢華麗大賽中是競爭對手，目標都是贏得大型慶典的緞帶獎章。", False],
            ["月光下的祕密集會", STORY_GENRES[4], "夢妖, 耿鬼, 引夢貘人", "每當滿月之夜，一些幽靈系寶可夢會聚集在古老的墓園，似乎在舉行神秘的儀式。一位膽大的訓練家決定偷偷觀察。", True],
            ["來自星星的訪客", STORY_GENRES[2], "皮寶寶, 月石, 太陽岩", "一顆隕石墜落在小鎮附近，帶來了一隻從未見過的宇宙寶可夢。它似乎在尋找回家的路。", False],
            ["烏龍大盜與迷糊偵探", STORY_GENRES[1], "扒手貓, 偵探皮卡丘", "笨拙的扒手貓試圖偷走美術館的寶石，卻遇上了同樣迷糊的偵探皮卡丘，引發一連串搞笑事件。", True],
        ],
        inputs=[input_theme, input_genre, input_pokemon_names, input_synopsis, input_include_abilities],
        # For examples, they will just populate the input fields. 
        # The user then clicks the buttons sequentially.
    )

if __name__ == "__main__":
    if initialization_error:
        print(f"CRITICAL: Gradio app cannot start due to service initialization error: {initialization_error}")
        print("Please ensure your OPENAI_API_KEY is correctly set in a .env file in the project root and restart.")
    else:
        print("Launching Gradio app...")
        # The launch() method now includes an `auth` parameter. 
        # If you need authentication, you can provide a callable or a (username, password) tuple.
        # For no authentication: demo.launch()
        # For simple authentication: demo.launch(auth=("admin", "password123"))
        demo.launch(server_name='0.0.0.0',share=True) # share=True can be used to create a temporary public link if needed. 