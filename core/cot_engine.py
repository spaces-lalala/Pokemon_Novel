from typing import Dict, Any, Optional, Tuple, TypedDict
import asyncio

from core.llm_services import LLMService, OpenAIConfigError
from core import prompt_templates
from core.pokemon_knowledge_base import format_pokemon_names_for_prompt

class StoryGenerationError(Exception):
    pass

class ReviewerOutput(TypedDict):
    feedback: str
    revised_content: str

def _parse_reviewer_output(raw_output: str, original_content_if_no_revision: str) -> ReviewerOutput:
    """
    解析審查者輸出，支援新舊格式，處理中英文冒號
    """
    # 支援中英文冒號的標記
    feedback_markers = ["評估回饋：", "評估回饋:"]
    content_markers = ["修訂後故事大綱：", "修訂後故事大綱:", "修訂後完整故事：", "修訂後完整故事:"]

    # 尋找標記位置
    feedback_start = -1
    feedback_marker_len = 0
    for marker in feedback_markers:
        pos = raw_output.find(marker)
        if pos != -1:
            feedback_start = pos
            feedback_marker_len = len(marker)
            break
    
    content_start = -1
    content_marker_len = 0
    for marker in content_markers:
        pos = raw_output.find(marker)
        if pos != -1:
            content_start = pos
            content_marker_len = len(marker)
            break
    
    # 如果找到任何標記，按標記格式處理
    if feedback_start != -1 or content_start != -1:
        feedback = ""
        revised_content = original_content_if_no_revision

        # 提取評估回饋
        if feedback_start != -1:
            if content_start != -1:
                feedback = raw_output[feedback_start + feedback_marker_len:content_start].strip()
            else:
                feedback = raw_output[feedback_start + feedback_marker_len:].strip()
        
        # 提取修訂後內容
        if content_start != -1:
            parsed_content = raw_output[content_start + content_marker_len:].strip()
            if parsed_content and not parsed_content.startswith("原故事大綱已達標") and not parsed_content.startswith("原故完整事已達標"):
                revised_content = parsed_content
            elif parsed_content.startswith("原故事大綱已達標") or parsed_content.startswith("原故完整事已達標"):
                revised_content = original_content_if_no_revision
        elif feedback_start != -1 and content_start == -1:
            # 只有評估回饋，沒有修訂內容，使用原始內容
            revised_content = original_content_if_no_revision
                
        return ReviewerOutput(feedback=feedback, revised_content=revised_content)
    
    # 沒有標記格式：直接使用整個輸出作為故事內容
    else:
        if raw_output.strip():
            # 檢查是否是 "已達標" 類型的回應
            if "已達標" in raw_output or "無需修訂" in raw_output:
                return ReviewerOutput(feedback="原內容已達標", revised_content=original_content_if_no_revision)
            else:
                # 直接使用 LLM 輸出作為修訂後的故事內容
                return ReviewerOutput(feedback="直接修訂", revised_content=raw_output.strip())
        else:
            # 如果輸出為空，使用原始內容
            return ReviewerOutput(feedback="空回應", revised_content=original_content_if_no_revision)

class CoTEngine:

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def _generate_story_plan_initial(self, theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str:
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            plan_prompt = prompt_templates.STORY_PLANNING_PROMPT_TEMPLATE.format(
                theme=theme,
                genre=genre,
                pokemon_names=formatted_pokemon_names,
                synopsis=synopsis,
                include_abilities="是" if include_abilities else "否"
            )
            story_plan = await self.llm_service.generate_text(plan_prompt, max_tokens=1536)
            if not story_plan or story_plan.strip() == "":
                raise StoryGenerationError("LLM 無法產生初始故事大綱。回應為空。")
            return story_plan
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"初始大綱產生時發生 LLM 設定錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"初始大綱產生時發生提示格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"初始故事大綱產生時發生意外錯誤：{e}") from e

    async def _review_and_revise_story_plan(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        include_abilities: bool, story_plan_to_review: str
    ) -> ReviewerOutput:
        try:
            formatted_pokemon_names_for_review = format_pokemon_names_for_prompt(pokemon_names)
            review_prompt = prompt_templates.STORY_PLAN_REVIEW_REVISE_PROMPT_TEMPLATE.format(
                theme=theme, genre=genre, pokemon_names=formatted_pokemon_names_for_review,
                synopsis=synopsis, include_abilities="是" if include_abilities else "否",
                story_plan_to_review=story_plan_to_review
            )
            raw_reviewer_output = await self.llm_service.generate_text(review_prompt, max_tokens=2048)
            if not raw_reviewer_output or raw_reviewer_output.strip() == "":
                 raise StoryGenerationError("審閱者 LLM 無法提供故事大綱的回饋/修訂。")
            
            parsed_output = _parse_reviewer_output(raw_reviewer_output, story_plan_to_review)
            print(f"大綱審閱回饋：{parsed_output['feedback']}")
            return parsed_output
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"大綱審閱時發生 LLM 設定錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"大綱審閱時發生提示格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"故事大綱審閱時發生意外錯誤：{e}") from e

    async def generate_story_plan(self, theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str:
        print(f"正在產生初始故事大綱：主題='{theme}', 類型='{genre}', 能力='{include_abilities}'")
        initial_plan = await self._generate_story_plan_initial(theme, genre, pokemon_names, synopsis, include_abilities)

        print("正在審閱和修訂故事大綱...")
        reviewer_result = await self._review_and_revise_story_plan(
            theme, genre, pokemon_names, synopsis, include_abilities, initial_plan
        )
        return reviewer_result['revised_content']

    async def _generate_story_from_plan_initial(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        story_plan: str, include_abilities: bool
    ) -> str:
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            story_prompt = prompt_templates.STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE.format(
                story_plan=story_plan, theme=theme, genre=genre, 
                pokemon_names=formatted_pokemon_names, synopsis=synopsis,
                include_abilities="是" if include_abilities else "否"
            )
            full_story = await self.llm_service.generate_text(story_prompt, max_tokens=4096, temperature=0.75)
            if not full_story or full_story.strip() == "":
                raise StoryGenerationError("LLM 未能生成初始完整故事。回應為空。")
            return full_story
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"初始故事生成期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"初始故事生成期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"初始完整故事生成期間發生意外錯誤：{e}") from e

    async def _review_and_revise_full_story(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        include_abilities: bool, story_plan: str, full_story_to_review: str
    ) -> ReviewerOutput:
        try:
            formatted_pokemon_names_for_review = format_pokemon_names_for_prompt(pokemon_names)
            review_prompt = prompt_templates.FULL_STORY_REVIEW_REVISE_PROMPT_TEMPLATE.format(
                theme=theme, genre=genre, pokemon_names=formatted_pokemon_names_for_review,
                synopsis=synopsis, include_abilities="是" if include_abilities else "否",
                story_plan=story_plan,
                full_story_to_review=full_story_to_review
            )
            raw_reviewer_output = await self.llm_service.generate_text(review_prompt, max_tokens=4096) 
            if not raw_reviewer_output or raw_reviewer_output.strip() == "":
                 raise StoryGenerationError("評論者 LLM 未能為完整故事提供回饋/修訂。")
            
            parsed_output = _parse_reviewer_output(raw_reviewer_output, full_story_to_review)
            print(f"完整故事評論回饋：{parsed_output['feedback']}")
            return parsed_output
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"完整故事評論期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"完整故事評論期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"完整故事評論期間發生意外錯誤：{e}") from e

    async def generate_story_from_plan(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        story_plan: str, include_abilities: bool
    ) -> str:
        print(f"根據計畫生成初始完整故事：主題='{theme}', 類型='{genre}', 能力='{include_abilities}'")
        initial_story = await self._generate_story_from_plan_initial(
            theme, genre, pokemon_names, synopsis, story_plan, include_abilities
        )
        
        print("正在評論並修訂完整故事...")
        reviewer_result = await self._review_and_revise_full_story(
            theme, genre, pokemon_names, synopsis, include_abilities, story_plan, initial_story
        )
        return reviewer_result['revised_content']

    async def generate_complete_story(
        self, 
        theme: str, 
        genre: str,
        pokemon_names: str, 
        synopsis: str,
        include_abilities: bool
    ) -> Tuple[str, str]:
        print(f"開始故事生成：主題：'{theme}', 類型：'{genre}', 包含能力：{include_abilities}")
        story_plan = await self._generate_story_plan_initial(theme, genre, pokemon_names, synopsis, include_abilities)
        print("故事計畫已生成。現在生成完整故事...")
        full_story = await self._generate_story_from_plan_initial(theme, genre, pokemon_names, synopsis, story_plan, include_abilities)
        print("完整故事生成成功。")
        return story_plan, full_story

    async def get_input_refinement_suggestions(
        self, 
        theme: Optional[str],
        genre: Optional[str],
        pokemon_names: Optional[str],
        synopsis: Optional[str],
        include_abilities: bool
    ) -> str:
        theme_context = theme if theme else "未指定"
        genre_context = genre if genre else "任何"
        pokemon_names_context = pokemon_names if pokemon_names else "未指定"
        synopsis_context = synopsis if synopsis else "未指定"

        pokemon_suggestion_context_val = "寶可夢"
        if pokemon_names:
            first_pokemon = pokemon_names.split(',')[0].strip()
            if first_pokemon:
                pokemon_suggestion_context_val = first_pokemon
        
        try:
            suggestion_prompt = prompt_templates.INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE.format(
                theme=theme_context,
                genre=genre_context,
                pokemon_names=pokemon_names_context,
                pokemon_names_for_suggestion_context=pokemon_suggestion_context_val,
                synopsis=synopsis_context,
                include_abilities="是" if include_abilities else "否"
            )
            suggestions = await self.llm_service.generate_text(suggestion_prompt, max_tokens=200, temperature=0.5)
            if not suggestions or suggestions.strip() == "":
                return "目前沒有特定建議，您的輸入看起來相當完整！" 
            return suggestions
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"建議生成期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"建議生成期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"建議生成期間發生意外錯誤：{e}") from e

    async def get_synopsis_elaborations(
        self,
        theme: str,
        genre: str,
        pokemon_names: str,
        synopsis: str
    ) -> str:
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            prompt = prompt_templates.SYNOPSIS_ELABORATION_PROMPT_TEMPLATE.format(
                theme=theme,
                genre=genre,
                pokemon_names=formatted_pokemon_names,
                synopsis=synopsis
            )
            elaborations = await self.llm_service.generate_text(prompt, max_tokens=1024, temperature=0.7)
            if not elaborations or elaborations.strip() == "":
                raise StoryGenerationError("LLM 未能生成故事大綱闡述。")
            return elaborations
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"故事大綱闡述期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"故事大綱闡述期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"故事大綱闡述期間發生意外錯誤：{e}") from e

    async def get_character_profiles(
        self,
        theme: str,
        genre: str,
        pokemon_names: str,
        synopsis: str,
        story_plan: Optional[str] = None
    ) -> str:
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            # 使用基本模板，因為沒有專門的角色模板
            prompt = f"""<s>[INST] 您是一位寶可夢故事分析專家。根據以下資訊，請為故事中的主要角色（寶可夢和人類）建立詳細的角色檔案。

故事資訊：
- 主題：{theme}
- 類型：{genre}
- 寶可夢：{formatted_pokemon_names}
- 概要：{synopsis}
- 故事大綱：{story_plan if story_plan else "未提供"}

請為每個角色提供：
1. 性格特徵
2. 動機和目標
3. 背景故事
4. 在故事中的作用

請使用繁體中文回答。[/INST]"""
            
            profiles = await self.llm_service.generate_text(prompt, max_tokens=1536, temperature=0.6)
            if not profiles or profiles.strip() == "":
                raise StoryGenerationError("LLM 未能生成角色檔案。")
            return profiles
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"角色檔案建立期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"角色檔案建立期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"角色檔案建立期間發生意外錯誤：{e}") from e

    async def get_setting_details(
        self,
        theme: str,
        genre: str,
        synopsis: str,
        story_plan: Optional[str] = None
    ) -> str:
        try:
            prompt = f"""<s>[INST] 您是一位寶可夢世界建構專家。根據以下故事資訊，請詳細描述故事發生的場景和環境。

故事資訊：
- 主題：{theme}
- 類型：{genre}
- 概要：{synopsis}
- 故事大綱：{story_plan if story_plan else "未提供"}

請提供：
1. 主要場景描述
2. 環境氛圍
3. 地理特徵
4. 氣候和時間設定
5. 對故事情節的影響

請使用繁體中文回答。[/INST]"""
            
            setting_details = await self.llm_service.generate_text(prompt, max_tokens=1024, temperature=0.7)
            if not setting_details or setting_details.strip() == "":
                raise StoryGenerationError("LLM 未能生成場景細節。")
            return setting_details
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"場景細節生成期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"場景細節生成期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"場景細節生成期間發生意外錯誤：{e}") from e

    async def get_plot_twist_suggestions(
        self,
        story_plan: str,
        section_to_twist: Optional[str] = None
    ) -> str:
        try:
            prompt = f"""<s>[INST] 您是一位創意故事顧問。根據以下故事大綱，請提供3-4個有趣的劇情轉折建議。

故事大綱：
{story_plan}

特定區段（如有）：{section_to_twist if section_to_twist else "整體故事"}

請為每個轉折提供：
1. 轉折點描述
2. 對故事的影響
3. 如何自然融入現有情節

請使用繁體中文回答。[/INST]"""
            
            twists = await self.llm_service.generate_text(prompt, max_tokens=768, temperature=0.75)
            if not twists or twists.strip() == "":
                raise StoryGenerationError("LLM 未能生成劇情轉折建議。")
            return twists
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"劇情轉折建議期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"劇情轉折建議期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"劇情轉折建議期間發生意外錯誤：{e}") from e

    async def tune_story_style_tone(
        self,
        story_text_to_tune: str,
        theme: str,
        genre: str,
        desired_style_tone: str
    ) -> str:
        try:
            prompt = f"""<s>[INST] 您是一位故事風格編輯專家。請根據指定的風格和語調調整以下故事文本。

原始故事文本：
{story_text_to_tune}

故事背景：
- 主題：{theme}
- 類型：{genre}
- 期望風格：{desired_style_tone}

請重寫故事文本，使其符合指定的風格和語調，同時保持原有的情節和角色。

請使用繁體中文回答。[/INST]"""
            
            tuned_text = await self.llm_service.generate_text(prompt, max_tokens=len(story_text_to_tune.split())*2 + 512, temperature=0.7)
            if not tuned_text or tuned_text.strip() == "":
                raise StoryGenerationError("LLM 未能調整故事風格/語調。")
            return tuned_text
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"風格/語調調整期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"風格/語調調整期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"風格/語調調整期間發生意外錯誤：{e}") from e

    async def get_story_branching_suggestions(
        self,
        current_story_segment: str,
        theme: str,
        genre: str,
        story_plan: Optional[str] = None
    ) -> str:
        try:
            prompt = f"""<s>[INST] 您是一位互動故事專家。根據目前的故事片段，請提供3-4個可能的故事發展方向。

目前故事片段：
{current_story_segment}

故事背景：
- 主題：{theme}
- 類型：{genre}
- 原始大綱：{story_plan if story_plan else "未提供"}

請為每個分支提供：
1. 分支描述
2. 可能的後果
3. 如何與主題保持一致

請使用繁體中文回答。[/INST]"""
            
            branches = await self.llm_service.generate_text(prompt, max_tokens=1024, temperature=0.7)
            if not branches or branches.strip() == "":
                raise StoryGenerationError("LLM 未能生成故事分支建議。")
            return branches
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"故事分支期間發生 LLM 配置錯誤：{e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"故事分支期間發生提詞格式錯誤：{e}") from e
        except Exception as e:
            raise StoryGenerationError(f"故事分支期間發生意外錯誤：{e}") from e

async def main_test_cot() -> None:
    print("--- 測試 CoTEngine ---")
    try:
        llm = LLMService(model_name="gpt-4.1")
        cot_engine = CoTEngine(llm_service=llm)

        test_theme = "勇敢的寶可夢面對最大的恐懼"
        test_genre = "冒險 (Adventure)"
        test_pokemon = "皮丘"
        test_synopsis = "一隻小小隻的皮丘非常害怕高處，但牠必須爬上一棵高聳的大樹，為生病的朋友摘取稀有的果實。"
        test_include_abilities = True

        print(f"\n測試輸入優化建議：主題='{test_theme}', 類型='{test_genre}', 寶可夢='{test_pokemon}', 大綱='{test_synopsis[:30]}...', 能力：{test_include_abilities}")
        suggestions = await cot_engine.get_input_refinement_suggestions(test_theme, test_genre, test_pokemon, test_synopsis, test_include_abilities)
        print(f"輸入優化建議：\n{suggestions}")

        print("\n僅測試故事計畫生成...")
        generated_plan = await cot_engine.generate_story_plan(
            theme=test_theme,
            genre=test_genre,
            pokemon_names=test_pokemon,
            synopsis=test_synopsis,
            include_abilities=test_include_abilities
        )
        print("\n--- 生成的故事計畫（獨立測試）---")
        print(generated_plan)

    except StoryGenerationError as e:
        print(f"故事生成錯誤：{e}")
    except OpenAIConfigError as e:
        print(f"OpenAI 配置錯誤：{e}")
    except Exception as e:
        print(f"CoT 引擎測試期間發生意外錯誤：{e}")

if __name__ == "__main__":
    asyncio.run(main_test_cot())