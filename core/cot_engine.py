from typing import Dict, Any, Optional, Tuple, TypedDict

from core.llm_services import LLMService, OpenAIConfigError
from core import prompt_templates
from core.pokemon_knowledge_base import format_pokemon_names_for_prompt

class StoryGenerationError(Exception):
    pass

class ReviewerOutput(TypedDict):
    feedback: str
    revised_content: str

def _parse_reviewer_output(raw_output: str, original_content_if_no_revision: str) -> ReviewerOutput:
    feedback_marker = "評估回饋:"
    content_marker = "修訂後故事大綱:"
    if content_marker not in raw_output:
        content_marker = "修訂後完整故事:"

    feedback = ""
    revised_content = original_content_if_no_revision

    feedback_start = raw_output.find(feedback_marker)
    content_start = raw_output.find(content_marker)

    if feedback_start != -1:
        if content_start != -1:
            feedback = raw_output[feedback_start + len(feedback_marker):content_start].strip()
        else:
            feedback = raw_output[feedback_start + len(feedback_marker):].strip()
    
    if content_start != -1:
        parsed_content = raw_output[content_start + len(content_marker):].strip()
        if parsed_content and not parsed_content.startswith("原故事大綱已達標") and not parsed_content.startswith("原故完整事已達標"):
            revised_content = parsed_content
        elif parsed_content.startswith("原故事大綱已達標") or parsed_content.startswith("原故完整事已達標"):
            if not feedback:
                feedback = "審閱者認為內容已達標，無需修訂。"
    elif feedback_start == -1:
        if raw_output.strip():
            revised_content = raw_output.strip()
            feedback = "審閱者未提供明確回饋標記，但提供了內容。"
        else:
            feedback = "審閱者輸出格式不正確或為空。"
            
    return ReviewerOutput(feedback=feedback, revised_content=revised_content)

class CoTEngine:

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def _generate_story_plan_initial(self, theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str:
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            plan_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_PLANNING_PROMPT_TEMPLATE,
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
            review_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_PLAN_REVIEW_REVISE_PROMPT_TEMPLATE,
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
            # 先將寶可夢名稱格式化為「中文名 (英文名)」
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            story_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE,
                story_plan=story_plan, theme=theme, genre=genre, 
                pokemon_names=formatted_pokemon_names, synopsis=synopsis,
                include_abilities="Yes" if include_abilities else "No"
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
            review_prompt = prompt_templates.format_prompt(
                prompt_templates.FULL_STORY_REVIEW_REVISE_PROMPT_TEMPLATE,
                theme=theme, genre=genre, pokemon_names=formatted_pokemon_names_for_review,
                synopsis=synopsis,                include_abilities="是" if include_abilities else "否",
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
            suggestion_prompt = prompt_templates.format_prompt(
                prompt_templates.INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE,
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.SYNOPSIS_ELABORATION_PROMPT_TEMPLATE,
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.CHARACTER_DEVELOPMENT_PROMPT_TEMPLATE,
                theme=theme,
                genre=genre,
                pokemon_names=formatted_pokemon_names,
                synopsis=synopsis,
                story_plan=story_plan if story_plan else "N/A"
            )
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.SETTING_DETAIL_PROMPT_TEMPLATE,
                theme=theme,
                genre=genre,
                synopsis=synopsis,
                story_plan=story_plan if story_plan else "N/A"
            )
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.PLOT_TWIST_SUGGESTION_PROMPT_TEMPLATE,
                story_plan=story_plan,
                section_to_twist=section_to_twist if section_to_twist else "（整體計畫或高潮）"
            )
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.STYLE_TONE_TUNING_PROMPT_TEMPLATE,
                story_text_to_tune=story_text_to_tune,
                theme=theme,
                genre=genre,
                desired_style_tone=desired_style_tone
            )
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
            prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_BRANCHING_SUGGESTION_PROMPT_TEMPLATE,
                current_story_segment=current_story_segment,
                theme=theme,
                genre=genre,
                story_plan=story_plan if story_plan else "N/A"
            )
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
        llm = LLMService(model_name="gpt-4-turbo")
        cot_engine = CoTEngine(llm_service=llm)

        test_theme = "勇敢的寶可夢面對最大的恐懼"
        test_genre = "冒險 (Adventure)"
        test_pokemon = "皮丘 (Pichu)"
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

        if generated_plan and generated_plan.strip():
            print("\n測試從上述計畫生成完整故事...")
            full_story_from_plan = await cot_engine.generate_story_from_plan(
                theme=test_theme,
                genre=test_genre,
                pokemon_names=test_pokemon,
                synopsis=test_synopsis,
                story_plan=generated_plan, 
                include_abilities=test_include_abilities
            )
            print("\n--- 生成的完整故事（來自獨立計畫測試）---")
            print(full_story_from_plan)

            print("\n--- 測試進階 CoT 階段：故事大綱闡述 ---")
            elaborations = await cot_engine.get_synopsis_elaborations(
                theme=test_theme, genre=test_genre, pokemon_names=test_pokemon, synopsis=test_synopsis
            )
            print(f"故事大綱闡述：\n{elaborations}")

            print("\n--- 測試進階 CoT 階段：角色檔案 ---")
            char_profiles = await cot_engine.get_character_profiles(
                theme=test_theme, genre=test_genre, pokemon_names=test_pokemon, synopsis=test_synopsis, story_plan=generated_plan
            )
            print(f"角色檔案：\n{char_profiles}")

            print("\n--- 測試進階 CoT 階段：場景細節 ---")
            setting_desc = await cot_engine.get_setting_details(
                theme=test_theme, genre=test_genre, synopsis=test_synopsis, story_plan=generated_plan
            )
            print(f"場景描述：\n{setting_desc}")

            print("\n--- 測試進階 CoT 階段：劇情轉折建議 ---")
            twists = await cot_engine.get_plot_twist_suggestions(story_plan=generated_plan)
            print(f"劇情轉折建議：\n{twists}")
            
            if full_story_from_plan and full_story_from_plan.strip():
                print("\n--- 測試進階 CoT 階段：風格/語調調整 ---")
                story_snippet_for_tuning = " ".join(full_story_from_plan.split()[:100])
                desired_style = "更加史詩與莊嚴感"
                tuned_segment = await cot_engine.tune_story_style_tone(
                    story_text_to_tune=story_snippet_for_tuning, 
                    theme=test_theme, 
                    genre=test_genre, 
                    desired_style_tone=desired_style
                )
                print(f"調整後的故事片段（調整為'{desired_style}'）：\n{tuned_segment}")

                print("\n--- 測試進階 CoT 階段：故事分支建議 ---")
                branch_suggestions = await cot_engine.get_story_branching_suggestions(
                    current_story_segment=story_snippet_for_tuning,
                    theme=test_theme,
                    genre=test_genre,
                    story_plan=generated_plan
                )
                print(f"故事分支建議：\n{branch_suggestions}")
        else:
            print("由於計畫為空，跳過完整故事和進階 CoT 測試。")


        test_theme_2 = "兩隻互相競爭的寶可夢學會合作"
        test_genre_2 = "喜劇 (Comedy)"
        test_pokemon_2 = "小火龍 (Charmander), 傑尼龜 (Squirtle)"
        test_synopsis_2 = "一隻小火龍和一隻傑尼龜總是互相競爭，但牠們被困在一個洞穴裡，需要彼此合作才能逃脫。"
        test_include_abilities_2 = False
        
        print(f"\n測試輸入優化建議：主題='{test_theme_2}', 類型='{test_genre_2}', 寶可夢='{test_pokemon_2}', 大綱='{test_synopsis_2[:30]}...', 能力：{test_include_abilities_2}")
        suggestions_2 = await cot_engine.get_input_refinement_suggestions(test_theme_2, test_genre_2, test_pokemon_2, test_synopsis_2, test_include_abilities_2)
        print(f"輸入優化建議（第二個例子）：\n{suggestions_2}")

        print("\n僅測試故事計畫生成（第二個例子）...")
        generated_plan_2 = await cot_engine.generate_story_plan(
            theme=test_theme_2,
            genre=test_genre_2,
            pokemon_names=test_pokemon_2,
            synopsis=test_synopsis_2,
            include_abilities=test_include_abilities_2
        )
        print("\n--- 生成的故事計畫（獨立測試 - 第二個例子）---")
        print(generated_plan_2)

        if generated_plan_2 and generated_plan_2.strip():
            print("\n測試從上述計畫生成完整故事（第二個例子）...")
            full_story_from_plan_2 = await cot_engine.generate_story_from_plan(
                theme=test_theme_2,
                genre=test_genre_2,
                pokemon_names=test_pokemon_2,
                synopsis=test_synopsis_2,
                story_plan=generated_plan_2,
                include_abilities=test_include_abilities_2
            )
            print("\n--- 生成的完整故事（來自獨立計畫測試 - 第二個例子）---")
            print(full_story_from_plan_2)

            print("\n--- 測試進階 CoT 階段：故事大綱闡述（第二個例子）---")
            elaborations_2 = await cot_engine.get_synopsis_elaborations(
                theme=test_theme_2, genre=test_genre_2, pokemon_names=test_pokemon_2, synopsis=test_synopsis_2
            )
            print(f"故事大綱闡述（第二個例子）：\n{elaborations_2}")

            print("\n--- 測試進階 CoT 階段：角色檔案（第二個例子）---")
            char_profiles_2 = await cot_engine.get_character_profiles(
                theme=test_theme_2, genre=test_genre_2, pokemon_names=test_pokemon_2, synopsis=test_synopsis_2, story_plan=generated_plan_2
            )
            print(f"角色檔案（第二個例子）：\n{char_profiles_2}")
            
        else:
            print("由於第二個例子的計畫為空，跳過完整故事和進階 CoT 測試。")

    except StoryGenerationError as e:
        print(f"故事生成錯誤：{e}")
    except OpenAIConfigError as e:
        print(f"OpenAI 配置錯誤：{e}")
    except Exception as e:
        print(f"CoT 引擎測試期間發生意外錯誤：{e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_test_cot()) 