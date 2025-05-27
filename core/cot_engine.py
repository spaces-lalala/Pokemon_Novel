from typing import Dict, Any, Optional, Tuple, TypedDict

from core.llm_services import LLMService, OpenAIConfigError
from core import prompt_templates
from core.pokemon_knowledge_base import format_pokemon_names_for_prompt

class StoryGenerationError(Exception):
    """Custom exception for errors during the story generation process."""
    pass

class ReviewerOutput(TypedDict):
    feedback: str
    revised_content: str

def _parse_reviewer_output(raw_output: str, original_content_if_no_revision: str) -> ReviewerOutput:
    """Parses the raw output from a reviewer LLM."""
    feedback_marker = "評估回饋:"
    content_marker = "修訂後故事大綱:" # For plan
    if content_marker not in raw_output:
        content_marker = "修訂後完整故事:" # For story

    feedback = ""
    revised_content = original_content_if_no_revision # Default to original if parsing fails or no revision needed

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
            # Reviewer explicitly states no revision needed
            if not feedback: # Add generic feedback if reviewer didn't provide one
                feedback = "審閱者認為內容已達標，無需修訂。"
            # revised_content remains original_content_if_no_revision
    elif feedback_start == -1: # Neither marker found, assume it might be just the content or an error
        # This case might need more robust handling or logging if it occurs often
        # For now, if no markers, and raw_output is not empty, assume it is the revised content.
        # This is a fallback, proper formatting by LLM is expected.
        if raw_output.strip():
            revised_content = raw_output.strip()
            feedback = "審閱者未提供明確回饋標記，但提供了內容。"
        else:
            feedback = "審閱者輸出格式不正確或為空。"
            
    return ReviewerOutput(feedback=feedback, revised_content=revised_content)

class CoTEngine:
    """
    Chain of Thought Engine for generating Pokémon stories.
    Now includes review and revision stages.

    This engine orchestrates a multi-step process to generate stories:
    1. Plan the story based on user inputs.
    2. Generate the full story based on the plan.
    It can also be used to suggest refinements to user inputs.
    """

    def __init__(self, llm_service: LLMService) -> None:
        """
        Initializes the CoTEngine with an LLMService instance.

        Args:
            llm_service: An instance of LLMService to interact with the LLM.
        """
        self.llm_service = llm_service

    async def _generate_story_plan_initial(self, theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str:
        """
        Internal method to generate an initial story plan using the LLM.

        Args:
            theme: The theme of the story.
            genre: The genre of the story.
            pokemon_names: Comma-separated string of Pokémon names.
            synopsis: The user-provided synopsis or story idea.
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            The generated initial story plan as a string.

        Raises:
            StoryGenerationError: If the LLM fails to generate an initial plan.
        """
        try:
            # 先將寶可夢名稱格式化為「中文名 (英文名)」
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            plan_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_PLANNING_PROMPT_TEMPLATE,
                theme=theme,
                genre=genre,
                pokemon_names=formatted_pokemon_names,
                synopsis=synopsis,
                include_abilities="Yes" if include_abilities else "No"
            )
            # print("DEBUG: Story Planning Prompt:\n", plan_prompt) # For debugging
            story_plan = await self.llm_service.generate_text(plan_prompt, max_tokens=1536) # Increased max_tokens for a more detailed plan
            if not story_plan or story_plan.strip() == "":
                raise StoryGenerationError("LLM failed to generate an initial story plan. The response was empty.")
            # print("DEBUG: Generated Story Plan:\n", story_plan) # For debugging
            return story_plan
        except OpenAIConfigError as e:
            # Forward OpenAI specific configuration errors
            raise StoryGenerationError(f"LLM configuration error during initial plan generation: {e}") from e
        except KeyError as e:
            # This might happen if prompt template placeholders change and code isn't updated
            raise StoryGenerationError(f"Prompt formatting error during initial plan generation: {e}") from e
        except Exception as e:
            # Catch any other unexpected errors from LLM service or other issues
            raise StoryGenerationError(f"Unexpected error during initial story plan generation: {e}") from e

    async def _review_and_revise_story_plan(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        include_abilities: bool, story_plan_to_review: str
    ) -> ReviewerOutput: # Changed return type
        """
        Generates a revised story plan based on a previously created plan.

        Args:
            theme: The original theme of the story.
            genre: The genre of the story.
            pokemon_names: The original comma-separated string of Pokémon names.
            synopsis: The original user-provided synopsis.
            story_plan: The story plan generated by the LLM.
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            A tuple containing (feedback, revised_story_plan).

        Raises:
            StoryGenerationError: If the LLM fails to generate the revised story plan.
        """
        try:
            formatted_pokemon_names_for_review = format_pokemon_names_for_prompt(pokemon_names)
            review_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_PLAN_REVIEW_REVISE_PROMPT_TEMPLATE,
                theme=theme, genre=genre, pokemon_names=formatted_pokemon_names_for_review,
                synopsis=synopsis, include_abilities="Yes" if include_abilities else "No",
                story_plan_to_review=story_plan_to_review
            )
            raw_reviewer_output = await self.llm_service.generate_text(review_prompt, max_tokens=2048) # Increased max_tokens for review+revision
            if not raw_reviewer_output or raw_reviewer_output.strip() == "":
                 raise StoryGenerationError("Reviewer LLM failed to provide feedback/revision for the story plan.")
            
            # Use the new parser
            parsed_output = _parse_reviewer_output(raw_reviewer_output, story_plan_to_review)
            print(f"Plan Review Feedback: {parsed_output['feedback']}") # Log feedback
            return parsed_output
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during plan review: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during plan review: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during story plan review: {e}") from e

    async def generate_story_plan(self, theme: str, genre: str, pokemon_names: str, synopsis: str, include_abilities: bool) -> str: # Return is now just the revised plan string for Gradio
        """
        Generates a revised story plan based on user inputs.

        Args:
            theme: The theme of the story.
            genre: The genre of the story.
            pokemon_names: Comma-separated string of Pokémon names.
            synopsis: The user-provided synopsis or story idea.
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            The generated revised story plan as a string.

        Raises:
            StoryGenerationError: If the LLM fails to generate the revised story plan.
        """
        print(f"Generating initial story plan for: Theme='{theme}', Genre='{genre}', Abilities='{include_abilities}'")
        initial_plan = await self._generate_story_plan_initial(theme, genre, pokemon_names, synopsis, include_abilities)

        print("Reviewing and revising story plan...")
        reviewer_result = await self._review_and_revise_story_plan(
            theme, genre, pokemon_names, synopsis, include_abilities, initial_plan
        )
        # For Gradio, we currently just return the revised content string.
        # If feedback needs to be displayed, Gradio handler and this return type would change.
        return reviewer_result['revised_content']

    async def _generate_story_from_plan_initial(
        self, theme: str, genre: str,pokemon_names: str, synopsis: str, 
        story_plan: str, include_abilities: bool
    ) -> str:
        """
        Generates the initial full story based on a previously created plan.

        Args:
            theme: The original theme of the story.
            genre: The genre of the story.
            pokemon_names: The original comma-separated string of Pokémon names.
            synopsis: The original user-provided synopsis.
            story_plan: The story plan generated by the LLM.
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            The generated initial full story as a string.

        Raises:
            StoryGenerationError: If the LLM fails to generate the initial full story.
        """
        try:
            # 先將寶可夢名稱格式化為「中文名 (英文名)」
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            story_prompt = prompt_templates.format_prompt(
                prompt_templates.STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE,
                story_plan=story_plan, theme=theme, genre=genre, 
                pokemon_names=formatted_pokemon_names, synopsis=synopsis,
                include_abilities="Yes" if include_abilities else "No"
            )
            # print("DEBUG: Story Generation Prompt:\n", story_prompt) # For debugging
            # Increased max_tokens for the full story. Adjust as needed.
            # For an 1000-1500-word story, max_tokens might need to be around 3000-4500 tokens.
            # GPT-4 Turbo has a large context window, so we can be generous here.
            full_story = await self.llm_service.generate_text(story_prompt, max_tokens=4096, temperature=0.75)
            if not full_story or full_story.strip() == "":
                raise StoryGenerationError("LLM failed to generate the initial full story. The response was empty.")
            # print("DEBUG: Generated Full Story:\n", full_story) # For debugging
            return full_story
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during initial story generation: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during initial story generation: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during initial full story generation: {e}") from e

    async def _review_and_revise_full_story(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        include_abilities: bool, story_plan: str, full_story_to_review: str
    ) -> ReviewerOutput: # Changed return type
        """
        Generates a revised full story based on a previously created story.

        Args:
            theme: The original theme of the story.
            genre: The genre of the story.
            pokemon_names: The original comma-separated string of Pokémon names.
            synopsis: The original user-provided synopsis.
            story_plan: The story plan generated by the LLM.
            full_story: The generated full story.

        Returns:
            A tuple containing (feedback, revised_story).

        Raises:
            StoryGenerationError: If the LLM fails to generate the revised story.
        """
        try:
            formatted_pokemon_names_for_review = format_pokemon_names_for_prompt(pokemon_names)
            review_prompt = prompt_templates.format_prompt(
                prompt_templates.FULL_STORY_REVIEW_REVISE_PROMPT_TEMPLATE,
                theme=theme, genre=genre, pokemon_names=formatted_pokemon_names_for_review,
                synopsis=synopsis, include_abilities="Yes" if include_abilities else "No",
                story_plan=story_plan, # Pass the guiding plan to the story reviewer
                full_story_to_review=full_story_to_review
            )
            # Story review might need more tokens if the story is long and revision is substantial
            raw_reviewer_output = await self.llm_service.generate_text(review_prompt, max_tokens=4096) 
            if not raw_reviewer_output or raw_reviewer_output.strip() == "":
                 raise StoryGenerationError("Reviewer LLM failed to provide feedback/revision for the full story.")
            
            parsed_output = _parse_reviewer_output(raw_reviewer_output, full_story_to_review)
            print(f"Full Story Review Feedback: {parsed_output['feedback']}") # Log feedback
            return parsed_output
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during full story review: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during full story review: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during full story review: {e}") from e

    async def generate_story_from_plan(
        self, theme: str, genre: str, pokemon_names: str, synopsis: str, 
        story_plan: str, include_abilities: bool
    ) -> str: # Return is now just the revised story string for Gradio
        """
        Generates a revised full story based on a (potentially user-edited) plan.

        Args:
            theme: The original theme of the story.
            genre: The genre of the story.
            pokemon_names: The original comma-separated string of Pokémon names.
            synopsis: The original user-provided synopsis.
            story_plan: The story plan (potentially edited by the user).
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            The generated revised full story as a string.

        Raises:
            StoryGenerationError: If the LLM fails to generate the revised story.
        """
        print(f"Generating initial full story from plan for: Theme='{theme}', Genre='{genre}', Abilities='{include_abilities}'")
        initial_story = await self._generate_story_from_plan_initial(
            theme, genre, pokemon_names, synopsis, story_plan, include_abilities
        )
        
        print("Reviewing and revising full story...")
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
        """
        Generates a complete Pokémon story through a two-step CoT process:
        1. Generate a story plan.
        2. Generate the full story from the plan.

        Args:
            theme: The theme of the story.
            genre: The genre of the story.
            pokemon_names: Comma-separated string of Pokémon names.
            synopsis: The user-provided synopsis or story idea.
            include_abilities: Whether to include Pokémon abilities in the story.

        Returns:
            A tuple containing (generated_story_plan, full_generated_story).

        Raises:
            StoryGenerationError: If any part of the story generation process fails.
        """
        print(f"Starting story generation for theme: '{theme}', genre: '{genre}', include_abilities: {include_abilities}")
        # 這裡不再需要額外格式化，因為下游方法已處理
        story_plan = await self._generate_story_plan_initial(theme, genre, pokemon_names, synopsis, include_abilities)
        print("Story plan generated. Now generating full story...")
        full_story = await self._generate_story_from_plan_initial(theme, genre, pokemon_names, synopsis, story_plan, include_abilities)
        print("Full story generated successfully.")
        return story_plan, full_story

    async def get_input_refinement_suggestions(
        self, 
        theme: Optional[str],
        genre: Optional[str],
        pokemon_names: Optional[str],
        synopsis: Optional[str],
        include_abilities: bool
    ) -> str:
        """
        Generates suggestions to help the user refine their story inputs.

        Args:
            theme: The current story theme input by the user.
            genre: The current story genre input by the user.
            pokemon_names: The current Pokémon names input by the user.
            synopsis: The current story synopsis input by the user.
            include_abilities: Whether the user wants to include Pokémon abilities.

        Returns:
            A string containing 1-2 suggestions, or an error message if generation fails.
        
        Raises:
            StoryGenerationError: If suggestion generation fails.
        """
        # Handle potentially empty inputs for the prompt context
        theme_context = theme if theme else "Not specified"
        genre_context = genre if genre else "Any"
        pokemon_names_context = pokemon_names if pokemon_names else "None specified"
        synopsis_context = synopsis if synopsis else "Not specified"

        # Determine a good value for {pokemon_names_for_suggestion_context}
        # If multiple pokemon, could pick the first, or a generic term.
        # If only one, use its name. If none, use a generic term.
        pokemon_suggestion_context_val = "the Pokémon"
        if pokemon_names:
            first_pokemon = pokemon_names.split(',')[0].strip()
            if first_pokemon:
                pokemon_suggestion_context_val = first_pokemon
        
        try:
            suggestion_prompt = prompt_templates.format_prompt(
                prompt_templates.INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE,
                theme=theme_context,
                genre=genre_context,
                pokemon_names=pokemon_names_context, # This is for the 'Pokémon Involved' field in prompt
                pokemon_names_for_suggestion_context=pokemon_suggestion_context_val, # This is for the example suggestion
                synopsis=synopsis_context,
                include_abilities="Yes" if include_abilities else "No"
            )
            # print("DEBUG: Suggestion Prompt:\n", suggestion_prompt) # For debugging
            suggestions = await self.llm_service.generate_text(suggestion_prompt, max_tokens=200, temperature=0.5)
            if not suggestions or suggestions.strip() == "":
                # It's possible the LLM legitimately returns no suggestions if input is very good.
                # However, for robustness, we can treat empty as a minor issue or return a default.
                return "No specific suggestions at this time, your input looks quite comprehensive!" 
            return suggestions
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during suggestion generation: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during suggestion generation: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during suggestion generation: {e}") from e

    # --- New methods for advanced CoT stages ---

    async def get_synopsis_elaborations(
        self,
        theme: str,
        genre: str,
        pokemon_names: str,
        synopsis: str
    ) -> str:
        """Generates multiple elaborations or alternative directions for a given story synopsis.

        Args:
            theme: The story theme.
            genre: The story genre.
            pokemon_names: Comma-separated string of Pokémon names.
            synopsis: The initial story synopsis.

        Returns:
            A string containing 3-4 elaborated synopsis options, or an error message.

        Raises:
            StoryGenerationError: If elaboration generation fails.
        """
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
                raise StoryGenerationError("LLM failed to generate synopsis elaborations.")
            return elaborations
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during synopsis elaboration: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during synopsis elaboration: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during synopsis elaboration: {e}") from e

    async def get_character_profiles(
        self,
        theme: str,
        genre: str,
        pokemon_names: str,
        synopsis: str,
        story_plan: Optional[str] = None
    ) -> str:
        """Generates richer character profiles for the key Pokémon in the story.

        Args:
            theme: The story theme.
            genre: The story genre.
            pokemon_names: Comma-separated string of Pokémon names.
            synopsis: The initial story synopsis.
            story_plan: Optional existing story plan for additional context.

        Returns:
            A string containing detailed profiles for key Pokémon, or an error message.

        Raises:
            StoryGenerationError: If character profile generation fails.
        """
        try:
            formatted_pokemon_names = format_pokemon_names_for_prompt(pokemon_names)
            prompt = prompt_templates.format_prompt(
                prompt_templates.CHARACTER_DEVELOPMENT_PROMPT_TEMPLATE,
                theme=theme,
                genre=genre,
                pokemon_names=formatted_pokemon_names, # Pass the formatted list for the LLM to iterate
                synopsis=synopsis,
                story_plan=story_plan if story_plan else "N/A"
            )
            profiles = await self.llm_service.generate_text(prompt, max_tokens=1536, temperature=0.6)
            if not profiles or profiles.strip() == "":
                raise StoryGenerationError("LLM failed to generate character profiles.")
            return profiles
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during character profiling: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during character profiling: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during character profiling: {e}") from e

    async def get_setting_details(
        self,
        theme: str,
        genre: str,
        synopsis: str,
        story_plan: Optional[str] = None
    ) -> str:
        """Generates a detailed description of a key potential setting for the story.

        Args:
            theme: The story theme.
            genre: The story genre.
            synopsis: The initial story synopsis.
            story_plan: Optional existing story plan for additional context.

        Returns:
            A string containing a detailed setting description, or an error message.

        Raises:
            StoryGenerationError: If setting detail generation fails.
        """
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
                raise StoryGenerationError("LLM failed to generate setting details.")
            return setting_details
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during setting detailing: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during setting detailing: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during setting detailing: {e}") from e

    async def get_plot_twist_suggestions(
        self,
        story_plan: str,
        section_to_twist: Optional[str] = None
    ) -> str:
        """Suggests intriguing plot twists for a given story plan or a section of it.

        Args:
            story_plan: The guiding story plan.
            section_to_twist: Optional specific section of the plan to focus on for twists.

        Returns:
            A string containing 2-3 plot twist suggestions, or an error message.

        Raises:
            StoryGenerationError: If plot twist suggestion generation fails.
        """
        try:
            prompt = prompt_templates.format_prompt(
                prompt_templates.PLOT_TWIST_SUGGESTION_PROMPT_TEMPLATE,
                story_plan=story_plan,
                section_to_twist=section_to_twist if section_to_twist else "(Overall Plan or Climax)"
            )
            twists = await self.llm_service.generate_text(prompt, max_tokens=768, temperature=0.75)
            if not twists or twists.strip() == "":
                raise StoryGenerationError("LLM failed to generate plot twist suggestions.")
            return twists
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during plot twist suggestion: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during plot twist suggestion: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during plot twist suggestion: {e}") from e

    async def tune_story_style_tone(
        self,
        story_text_to_tune: str,
        theme: str, # Added theme and genre for context
        genre: str,
        desired_style_tone: str
    ) -> str:
        """Rewrites a piece of story text to match a new desired style or tone.

        Args:
            story_text_to_tune: The original story text or segment.
            theme: The original story theme for context.
            genre: The original story genre for context.
            desired_style_tone: The new style or tone to apply (e.g., "更加懸疑緊張").

        Returns:
            The rewritten story text in the new style/tone, or an error message.

        Raises:
            StoryGenerationError: If style/tone tuning fails.
        """
        try:
            prompt = prompt_templates.format_prompt(
                prompt_templates.STYLE_TONE_TUNING_PROMPT_TEMPLATE,
                story_text_to_tune=story_text_to_tune,
                theme=theme,
                genre=genre,
                desired_style_tone=desired_style_tone
            )
            tuned_text = await self.llm_service.generate_text(prompt, max_tokens=len(story_text_to_tune.split())*2 + 512, temperature=0.7) # Allow more tokens for rewrite
            if not tuned_text or tuned_text.strip() == "":
                raise StoryGenerationError("LLM failed to tune story style/tone.")
            return tuned_text
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during style/tone tuning: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during style/tone tuning: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during style/tone tuning: {e}") from e

    async def get_story_branching_suggestions(
        self,
        current_story_segment: str,
        theme: str,
        genre: str,
        story_plan: Optional[str] = None
    ) -> str:
        """Proposes distinct next scenes or developments for a given story segment.

        Args:
            current_story_segment: The current part of the story.
            theme: The original story theme.
            genre: The original story genre.
            story_plan: Optional guiding story plan for context.

        Returns:
            A string containing 2-3 suggested story branches, or an error message.

        Raises:
            StoryGenerationError: If branching suggestion generation fails.
        """
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
                raise StoryGenerationError("LLM failed to generate story branching suggestions.")
            return branches
        except OpenAIConfigError as e:
            raise StoryGenerationError(f"LLM configuration error during story branching: {e}") from e
        except KeyError as e:
            raise StoryGenerationError(f"Prompt formatting error during story branching: {e}") from e
        except Exception as e:
            raise StoryGenerationError(f"Unexpected error during story branching: {e}") from e

async def main_test_cot() -> None:
    print("--- Testing CoTEngine ---")
    try:
        # Ensure LLMService is initialized (requires .env with OPENAI_API_KEY)
        llm = LLMService(model_name="gpt-4-turbo") # Cheaper model for testing CoT flow
        cot_engine = CoTEngine(llm_service=llm)

        test_theme = "勇敢的寶可夢面對最大的恐懼"
        test_genre = "冒險 (Adventure)"
        test_pokemon = "皮丘 (Pichu)"
        test_synopsis = "一隻小小隻的皮丘非常害怕高處，但牠必須爬上一棵高聳的大樹，為生病的朋友摘取稀有的果實。"
        test_include_abilities = True

        print(f"\nTesting input refinement suggestions for: Theme='{test_theme}', Genre='{test_genre}', Pokémon='{test_pokemon}', Synopsis='{test_synopsis[:30]}...', Abilities: {test_include_abilities}")
        suggestions = await cot_engine.get_input_refinement_suggestions(test_theme, test_genre, test_pokemon, test_synopsis, test_include_abilities)
        print(f"Suggestions for input refinement:\n{suggestions}")

        print("\nTesting story plan generation only...")
        generated_plan = await cot_engine.generate_story_plan(
            theme=test_theme,
            genre=test_genre,
            pokemon_names=test_pokemon,
            synopsis=test_synopsis,
            include_abilities=test_include_abilities
        )
        print("\n--- Generated Story Plan (Standalone Test) ---")
        print(generated_plan)

        if generated_plan and generated_plan.strip(): # Ensure plan is not empty
            print("\nTesting full story generation from the above plan...")
            full_story_from_plan = await cot_engine.generate_story_from_plan(
                theme=test_theme,
                genre=test_genre,
                pokemon_names=test_pokemon,
                synopsis=test_synopsis,
                story_plan=generated_plan, 
                include_abilities=test_include_abilities
            )
            print("\n--- Generated Full Story (from Standalone Plan Test) ---")
            print(full_story_from_plan)

            print("\n--- Testing Advanced CoT Stage: Synopsis Elaboration ---")
            elaborations = await cot_engine.get_synopsis_elaborations(
                theme=test_theme, genre=test_genre, pokemon_names=test_pokemon, synopsis=test_synopsis
            )
            print(f"Synopsis Elaborations:\n{elaborations}")

            print("\n--- Testing Advanced CoT Stage: Character Profiles ---")
            char_profiles = await cot_engine.get_character_profiles(
                theme=test_theme, genre=test_genre, pokemon_names=test_pokemon, synopsis=test_synopsis, story_plan=generated_plan
            )
            print(f"Character Profiles:\n{char_profiles}")

            print("\n--- Testing Advanced CoT Stage: Setting Details ---")
            setting_desc = await cot_engine.get_setting_details(
                theme=test_theme, genre=test_genre, synopsis=test_synopsis, story_plan=generated_plan
            )
            print(f"Setting Description:\n{setting_desc}")

            print("\n--- Testing Advanced CoT Stage: Plot Twist Suggestions ---")
            # Potentially pick a section from generated_plan to test section_to_twist
            # For now, testing with overall plan
            twists = await cot_engine.get_plot_twist_suggestions(story_plan=generated_plan)
            print(f"Plot Twist Suggestions:\n{twists}")
            
            if full_story_from_plan and full_story_from_plan.strip():
                print("\n--- Testing Advanced CoT Stage: Style/Tone Tuning ---")
                # Take a snippet of the generated story for tuning
                story_snippet_for_tuning = " ".join(full_story_from_plan.split()[:100]) # First 100 words approx
                desired_style = "更加史詩與莊嚴感"
                tuned_segment = await cot_engine.tune_story_style_tone(
                    story_text_to_tune=story_snippet_for_tuning, 
                    theme=test_theme, 
                    genre=test_genre, 
                    desired_style_tone=desired_style
                )
                print(f"Tuned Story Segment (to '{desired_style}'):\n{tuned_segment}")

                print("\n--- Testing Advanced CoT Stage: Story Branching Suggestions ---")
                # Use the same snippet or another part of the story
                branch_suggestions = await cot_engine.get_story_branching_suggestions(
                    current_story_segment=story_snippet_for_tuning,
                    theme=test_theme,
                    genre=test_genre,
                    story_plan=generated_plan
                )
                print(f"Story Branching Suggestions:\n{branch_suggestions}")
        else:
            print("Skipping full story and advanced CoT tests due to empty plan.")


        # Test with slightly different inputs
        test_theme_2 = "兩隻互相競爭的寶可夢學會合作"
        test_genre_2 = "喜劇 (Comedy)"
        test_pokemon_2 = "小火龍 (Charmander), 傑尼龜 (Squirtle)"
        test_synopsis_2 = "一隻小火龍和一隻傑尼龜總是互相競爭，但牠們被困在一個洞穴裡，需要彼此合作才能逃脫。"
        test_include_abilities_2 = False
        
        print(f"\nTesting input refinement suggestions for: Theme='{test_theme_2}', Genre='{test_genre_2}', Pokémon='{test_pokemon_2}', Synopsis='{test_synopsis_2[:30]}...', Abilities: {test_include_abilities_2}")
        suggestions_2 = await cot_engine.get_input_refinement_suggestions(test_theme_2, test_genre_2, test_pokemon_2, test_synopsis_2, test_include_abilities_2)
        print(f"Suggestions for input refinement (2nd example):\n{suggestions_2}")

        print("\nTesting story plan generation only (2nd example)...")
        generated_plan_2 = await cot_engine.generate_story_plan(
            theme=test_theme_2,
            genre=test_genre_2,
            pokemon_names=test_pokemon_2,
            synopsis=test_synopsis_2,
            include_abilities=test_include_abilities_2
        )
        print("\n--- Generated Story Plan (Standalone Test - 2nd Example) ---")
        print(generated_plan_2)

        if generated_plan_2 and generated_plan_2.strip(): # Ensure plan is not empty
            print("\nTesting full story generation from the above plan (2nd example)...")
            full_story_from_plan_2 = await cot_engine.generate_story_from_plan(
                theme=test_theme_2,
                genre=test_genre_2,
                pokemon_names=test_pokemon_2,
                synopsis=test_synopsis_2,
                story_plan=generated_plan_2,
                include_abilities=test_include_abilities_2
            )
            print("\n--- Generated Full Story (from Standalone Plan Test - 2nd Example) ---")
            print(full_story_from_plan_2)

            # Add tests for new advanced CoT stages for the second example as well
            print("\n--- Testing Advanced CoT Stage: Synopsis Elaboration (2nd Example) ---")
            elaborations_2 = await cot_engine.get_synopsis_elaborations(
                theme=test_theme_2, genre=test_genre_2, pokemon_names=test_pokemon_2, synopsis=test_synopsis_2
            )
            print(f"Synopsis Elaborations (2nd Example):\n{elaborations_2}")

            print("\n--- Testing Advanced CoT Stage: Character Profiles (2nd Example) ---")
            char_profiles_2 = await cot_engine.get_character_profiles(
                theme=test_theme_2, genre=test_genre_2, pokemon_names=test_pokemon_2, synopsis=test_synopsis_2, story_plan=generated_plan_2
            )
            print(f"Character Profiles (2nd Example):\n{char_profiles_2}")
            
        else:
            print("Skipping full story and advanced CoT tests for 2nd example due to empty plan.")

    except StoryGenerationError as e:
        print(f"Story Generation Error: {e}")
    except OpenAIConfigError as e:
        print(f"OpenAI Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CoT Engine test: {e}")

if __name__ == "__main__":
    import asyncio
    # To run this test: python -m core.cot_engine (from project root)
    asyncio.run(main_test_cot()) 