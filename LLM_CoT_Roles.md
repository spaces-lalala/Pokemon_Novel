# AI 寶可夢短篇小說產生器：CoT 各階段 LLM 角色設定說明

本文件詳細說明在「AI 寶可夢短篇小說產生器」的思維鏈 (Chain of Thought, CoT) 流程中，大型語言模型 (LLM) 在各個主要階段所扮演的角色、接收的指示以及期望的行為。

## 1. 階段：獲取寫作提示 (Input Refinement Suggestions)

-   **執行者**: `CoTEngine.get_input_refinement_suggestions()`
-   **Prompt Template**: `INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE`
-   **LLM 角色**: **樂於助人的 AI 助理 (Helpful AI Assistant)**
    -   **任務**: 分析使用者當前輸入的故事素材（主題、類型、寶可夢、概要、是否包含特性）。
    -   **目標**: 提供 1-2 條簡潔、有幫助的建議或引導性問題，鼓勵使用者補充更多細節，以豐富故事內容。
    -   **風格**: 提問應禮貌且易於使用者理解和回應，專注於能顯著提升故事深度或獨特性的方面。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出**: 僅提供建議，不包含額外的對話性內容。
    -   **核心 CoT 思想**: 問題分解與澄清，協助使用者深化初步構想。

## 2. 階段：AI 生成初步故事大綱 (Initial Story Planning)

-   **執行者**: `CoTEngine._generate_story_plan_initial()` (由 `generate_story_plan` 內部呼叫)
-   **Prompt Template**: `STORY_PLANNING_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢故事大師 (Master Storyteller specializing in Pokémon)**
    -   **任務**: 根據使用者提供的所有輸入，創建一個有意義且連貫的短篇寶可夢故事大綱。
    -   **目標**: 生成一個結構清晰的故事計劃，通常包含 3-5 個主要章節。
    -   **風格**: 大綱需連貫、富有創意，並忠於寶可夢世界的精神。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出**: 僅輸出故事大綱。
    -   **核心 CoT 思想**: 初步規劃與結構化思考。

## 3. 階段：AI 審閱與修訂故事大綱 (Story Plan Review and Revision)

-   **執行者**: `CoTEngine._review_and_revise_story_plan()` (由 `generate_story_plan` 內部呼叫)
-   **Prompt Template**: `STORY_PLAN_REVIEW_REVISE_PROMPT_TEMPLATE`
-   **LLM 角色**: **專業寶可夢故事大綱編輯 (Expert Pokémon Story Plan Editor)**
    -   **任務**: 審閱先前生成的初步故事大綱，並根據使用者原始輸入及特定審核標準進行評估。
    -   **目標**: 如果大綱已優良則予以肯定；若需改進，則提供建設性回饋及修訂後更佳版本的大綱。
    -   **審核標準**: 連貫性、邏輯性、與使用者輸入的契合度、寶可夢精神、創意與吸引力、結構與細節、文體適切性、特性整合 (若適用)。
    -   **風格**: 專業、具建設性。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 包含「評估回饋:」和「修訂後故事大綱:」兩部分。
    -   **核心 CoT 思想**: 批判性評估與迭代改進，確保大綱品質。

## 4. 階段：AI 根據最終大綱生成初步完整故事 (Initial Full Story Generation from Plan)

-   **執行者**: `CoTEngine._generate_story_from_plan_initial()` (由 `generate_story_from_plan` 內部呼叫)
-   **Prompt Template**: `STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢故事大師 (Master Storyteller specializing in Pokémon)**
    -   **任務**: 根據先前生成並審閱修訂過的故事大綱，以及使用者原始的輸入，撰寫一篇初步的完整寶可夢短篇故事。
    -   **目標**: 生成一篇約 1000-1500 字的詳細故事初稿。
    -   **風格**: 故事必須使用繁體中文（台灣常用風格），並強烈反映指定的「故事類型」。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **指示**: 詳細擴展大綱、整合寶可夢特性、注意敘事風格、角色塑造、節奏與完整性等。
    -   **輸出**: 僅輸出初步的完整故事。
    -   **核心 CoT 思想**: 初步擴展與潤色，將結構化大綱轉化為敘事初稿。

## 5. 階段：AI 審閱與修訂完整故事 (Full Story Review and Revision)

-   **執行者**: `CoTEngine._review_and_revise_full_story()` (由 `generate_story_from_plan` 內部呼叫)
-   **Prompt Template**: `FULL_STORY_REVIEW_REVISE_PROMPT_TEMPLATE`
-   **LLM 角色**: **細心的寶可夢故事編輯 (Meticulous Pokémon Story Editor)**
    -   **任務**: 審閱先前生成的初步完整故事，並根據使用者原始輸入、指導性故事大綱及特定品質標準進行評估。
    -   **目標**: 如果故事已優良則予以肯定；若需改進，則提供建設性回饋及修訂後更佳版本的完整故事。
    -   **審核標準**: 大綱遵循度、吸引力與節奏、語言與風格、文體一致性、角色塑造、寶可夢整合、連貫性與清晰度、完整性與字數、情感影響力 (若適用)。
    -   **風格**: 專業、注重細節、具建設性。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 包含「評估回饋:」和「修訂後完整故事:」兩部分。
    -   **核心 CoT 思想**: 深度批判性評估與最終打磨，確保成品故事的最高品質。

---
*注意：隨著專案的演進，未來可能會加入更多 CoT 階段。*

## 6. 階段：主題/概要擴展與細化 (Synopsis Elaboration)

-   **執行者**: `CoTEngine.get_synopsis_elaborations()`
-   **Prompt Template**: `SYNOPSIS_ELABORATION_PROMPT_TEMPLATE`
-   **LLM 角色**: **創意腦力激盪夥伴 (Creative Brainstorming Partner for Pokémon story ideas)**
    -   **任務**: 根據使用者初步（可能簡短）的主題和概要，提出 3-4 個不同且引人入勝的闡述或替代方向。
    -   **目標**: 每個闡述都應提供獨特的視角、潛在衝突或有趣的子情節，幫助使用者拓展最初的構想。
    -   **風格**: 富有創意，緊扣寶可夢世界觀，並具備發展成引人入勝故事的潛力。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 提供 3-4 個帶編號的闡述段落，每個段落包含一個標題和詳細說明。
    -   **核心 CoT 思想**: 發散性思維與初步構想的深化，探索故事核心的多種可能性。

## 7. 階段：角色塑造深化 (Character Development)

-   **執行者**: `CoTEngine.get_character_profiles()`
-   **Prompt Template**: `CHARACTER_DEVELOPMENT_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢角色分析師與傳記作家 (Pokémon Character Analyst and Biographer)**
    -   **任務**: 根據主要寶可夢、故事主題、類型和概要，為每個關鍵寶可夢創建更豐富的角色檔案。
    -   **目標**: 產出的角色檔案應包含性格特點、核心動機、潛在內心衝突、與其他角色的可能關係，以及一句代表性的內心獨白（可選），以利於撰寫更具吸引力的故事。
    -   **風格**: 分析深入，描述生動，有助於角色立體化。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 清晰列出每個指定寶可夢的詳細檔案。
    -   **核心 CoT 思想**: 角色深度挖掘與具象化，賦予角色更豐富的內涵。

## 8. 階段：世界觀/場景設定細化 (Setting Detailing)

-   **執行者**: `CoTEngine.get_setting_details()`
-   **Prompt Template**: `SETTING_DETAIL_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢世界建構師與場景設計師 (Pokémon World Builder and Scene Designer)**
    -   **任務**: 根據使用者的故事主題、類型和概要，詳細描述一個關鍵的潛在場景。
    -   **目標**: 產出場景描述，包含自創的設定名稱、整體氛圍、視覺/聽覺/嗅覺/觸覺細節、與故事的關聯性，以及該環境中可能棲息的寶可夢類型，以增強故事的沉浸感。
    -   **風格**: 描述豐富，引人入勝，充滿想像力。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 一段或數段詳細的場景描述。
    -   **核心 CoT 思想**: 環境具象化與氛圍營造，豐富故事的背景舞台。

## 9. 階段：多角度情節推演 (Plot Twist Suggestion)

-   **執行者**: `CoTEngine.get_plot_twist_suggestions()`
-   **Prompt Template**: `PLOT_TWIST_SUGGESTION_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢故事劇情反轉大師 (Master of Plot Twists for Pokémon stories)**
    -   **任務**: 針對一個故事大綱（或其特定部分），提出 2-3 個引人入勝且出乎意料的情節轉折。
    -   **目標**: 提供的劇情反轉建議應巧妙、符合寶可夢世界觀，並大致與主題和類型一致（除非轉折本身就是要顛覆類型），使故事更刺激或深刻。
    -   **風格**: 構思巧妙，出人意表，能有效提升故事張力。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 提供 2-3 個帶編號的劇情反轉建議，每個建議包含標題和詳細說明其如何改變故事走向或意義。
    -   **核心 CoT 思想**: 敘事結構的動態調整與預期顛覆，增加故事的複雜度和趣味性。

## 10. 階段：特定風格/語氣轉換器 (Style/Tone Tuning)

-   **執行者**: `CoTEngine.tune_story_style_tone()`
-   **Prompt Template**: `STYLE_TONE_TUNING_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢敘事文學風格模擬器 (Literary Style Emulator specializing in Pokémon narratives)**
    -   **任務**: 將一段給定的寶可夢故事文本改寫成符合新的期望風格或語氣，同時保留核心事件和角色。
    -   **目標**: 根據使用者指定的風格/語氣（例如「更加懸疑緊張」、「更幽默詼諧」），調整文本的措辭、句式、節奏和描述性語言。
    -   **風格**: 忠實模擬目標風格，轉換自然流暢。
    -   **語言**: 改寫後的文本使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 提供符合新風格/語氣的改寫後故事文本。
    -   **核心 CoT 思想**: 敘事表達的靈活調整與情感共鳴的精準控制。

## 11. 階段：互動式分歧點建議 (Story Branching Suggestion)

-   **執行者**: `CoTEngine.get_story_branching_suggestions()`
-   **Prompt Template**: `STORY_BRANCHING_SUGGESTION_PROMPT_TEMPLATE`
-   **LLM 角色**: **寶可夢故事導航員 (Pokémon Story Navigator)**
    -   **任務**: 根據故事的當前片段，提出 2-3 個不同且合理的後續場景或發展，代表故事可能採取的不同選擇或路徑。
    -   **目標**: 提供的分支建議應像是自然的延續，但在結果或焦點上提供有意義的差異，讓使用者可以選擇或得到啟發。
    -   **風格**: 合乎邏輯，具有想像空間，能激發使用者對後續劇情的思考。
    -   **語言**: 使用繁體中文（台灣常用風格）。
    -   **輸出格式**: 提供 2-3 個帶編號的後續故事分支建議，每個建議包含簡短標題和情節描述。
    -   **核心 CoT 思想**: 敘事路徑探索與可能性擴展，賦予故事發展更多元的選擇。 