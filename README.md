# AI 寶可夢短篇小說產生器

本專案是一個以 Gradio 為前端、OpenAI LLM 為後端的互動式寶可夢短篇小說生成器，支援多階段 Chain-of-Thought（CoT）推理，協助使用者從故事構想到完整小說創作。

## 主要功能
- 📝 支援故事主題、類型、寶可夢、概要等多元輸入
- 🧠 多階段 CoT：故事大綱、角色塑造、場景細化、情節分歧、風格轉換等
- 🤖 整合 OpenAI GPT-4 Turbo（可自訂 API Key）
- 🎨 Gradio 互動式網頁介面，支援即時生成、下載
- 💡 寫作建議、分支選擇、風格調整等輔助功能

## 安裝與啟動
1. **安裝依賴**（建議使用 Poetry 或 venv）：
   ```bash
   # 使用 Poetry
   poetry install
   # 或使用 venv
   python -m venv venv
   source venv/bin/activate  # Windows 請用 venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **設定 OpenAI API Key**：
   - 在專案根目錄建立 `.env` 檔，內容：
     ```
     OPENAI_API_KEY=你的金鑰
     ```
3. **啟動 Gradio 介面**：
   ```bash
   python -m ui.app
   # 或
   python ui/app.py
   ```

## 目錄結構簡介
- `core/`：主要邏輯（CoT 引擎、LLM 服務、提示模板等）
- `ui/`：Gradio 前端介面
- `config/`：設定檔
- `data/`、`output/`：資料與輸出
- `colab/`：Colab 筆記本（如有）

## 貢獻與聯絡
歡迎 issue、PR 或討論改進！

---
本專案僅供學術與教學用途，寶可夢相關內容版權屬原公司所有。
