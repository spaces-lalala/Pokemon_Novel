"""
This module stores all prompt templates used in the application.

Using a dedicated module for prompts helps in:
- Centralizing all prompt strings for easy management and modification.
- Version controlling prompts effectively.
- Keeping the core logic files cleaner.
"""

from typing import List, Dict, Any

# --- Story Generation Prompts ---

# This is a very basic CoT structure. We might need to refine this based on results.
# It could involve more steps or more specific instructions for each step.

STORY_PLANNING_PROMPT_TEMPLATE = """
<s>[INST] You are a master storyteller specializing in the world of Pokémon. 
Your task is to create a significant and coherent plan or outline for a short Pokémon story based on the user's inputs.
When creating the plan, please use **Traditional Chinese (繁體中文)**, and ensure the language style and vocabulary are as close as possible to **common usage in Taiwan (台灣常用風格)** for all parts of the plan.
Make sure the plan aligns with the specified **Story Genre: {genre}**.
If the user wants to include Pokémon abilities (see 'Include Pokémon Abilities' below), ensure the plan allows for moments where these can be showcased effectively.

User Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}
- Include Pokémon Abilities: {include_abilities}

Please generate a structured story plan. Instead of many small points, aim for **3 to 5 major sections or stages** that represent significant parts of the story's progression. For example:

*   **Setup / Beginning:** Introduce the main characters, the initial setting, and the ordinary world before the main conflict begins.
*   **Confrontation / Rising Action:** Describe the main conflict or problem, the challenges faced, and how the stakes are raised. This section might cover several key events that build tension.
*   **Climax / Turning Point:** The most intense part of the story where the conflict reaches its peak.
*   **Resolution / Aftermath:** How the conflict is resolved, and what happens to the characters afterward. Show the new normal.

Feel free to adapt these section names or structures if the story's flow suggests a different natural division (e.g., a mystery might have "The Discovery", "The Investigation", "The Revelation").
**Each section in your plan should summarize a substantial portion of the story, not just a single event.**

Ensure the plan is coherent, creative, and stays true to the Pokémon world's spirit (e.g., themes of friendship, adventure, training, discovery).
The plan should be detailed enough to guide the writing of a ~1000-1500 word short story, with each planned section being substantial enough to be expanded into several paragraphs or pages of text.
Focus on making the story engaging and incorporating the specified Pokémon naturally into the narrative.

Output the story plan ONLY. Do not write the full story yet. [/INST] Story Plan:"""

STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE = """
<s>[INST] You are a master storyteller specializing in the world of Pokémon.
I will provide you with a story plan that was previously generated.
Your task is to write a complete, engaging, and well-structured short Pokémon story (approximately 1000-1500 words, but feel free to write more if needed to make the story complete and engaging) based on this plan.
Please use **Traditional Chinese (繁體中文)**, and ensure the language style, vocabulary, and phrasing are as close as possible to **common usage in Taiwan (台灣常用風格)**.
The story should strongly reflect the specified **Story Genre: {genre}**.

Story Plan:
{story_plan}

User's Original Inputs (for context, ensure these are reflected in the story):
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}
- Include Pokémon Abilities: {include_abilities}

Writing Guidelines:
-   **Language Style**: Crucially, the story **must be written in Traditional Chinese (繁體中文) and adhere to common Taiwanese phrasing and vocabulary (台灣常用風格)**.
-   **Genre Adherence**: The story must align with the specified **Story Genre: {genre}**. For example, if the genre is "Comedy", ensure there are humorous elements. If "Sci-Fi", incorporate futuristic or technological aspects.
-   **Detailed Expansion of Each Plan Point**: For EACH section in the provided Story Plan (e.g., Introduction, Inciting Incident, Rising Action, Climax, Falling Action, Resolution), you MUST **elaborate significantly**. This means:
    *   **Descriptive Language**: Use vivid descriptions for settings, characters' appearances, emotions, and actions.
    *   **Show, Don't Tell**: Instead of stating facts, describe scenes and interactions that reveal those facts.
    *   **Character Thoughts and Dialogue**: Include inner monologues for main characters (Pokémon or human) and meaningful dialogue between characters to advance the plot and reveal personality. If Pokémon cannot speak human language, describe their expressions, sounds, and actions to convey their feelings and intentions.
    *   **Sensory Details**: Engage multiple senses (sight, sound, smell, touch, taste where appropriate) to make the scenes more immersive.
    *   **Pacing within Sections**: Ensure each expanded section has a good flow and contributes to the overall narrative arc.
-   **Pokémon Abilities Integration (If 'Include Pokémon Abilities' is Yes)**: If the user requested it, naturally weave the known abilities, characteristics, or unique traits of the involved Pokémon into the narrative. For example, if Pikachu is involved and its ability is Static, an opponent might get paralyzed upon contact. If a Pokémon is known for its speed, describe its fast movements vividly. Show, don't just tell, these abilities in action.
-   **Narrative Style:** Write in a clear, descriptive, and engaging narrative style suitable for a Pokémon adventure story, adapted to the specified genre.
-   **Characterization:** Briefly bring the Pokémon and any human characters (if implied or can be inferred) to life with their actions and dialogue (if any).
-   **Pokémon Elements:** Naturally integrate Pokémon abilities, battles (if appropriate for the plan), and the general atmosphere of the Pokémon world.
-   **Pacing:** Ensure the story flows well from one part of the plan to the next, and that the overall story feels substantial.
-   **Word Count and Depth**: Aim for a story length of approximately **1000-1500 words, or even longer if necessary to fully develop the plot points from the plan**. The goal is a rich, detailed narrative, not just a summary. Do not rush the story; take the space needed to tell it well.
-   **Completeness:** The story should have a clear beginning, middle, and end, following the provided plan and expanding upon it.
-   **Tone:** Maintain a tone consistent with the user's theme and the general positive spirit of Pokémon, unless the theme explicitly suggests otherwise (e.g., a mystery story might have a more suspenseful tone).

Write the full story now. Output ONLY the story. Do not include any other commentary. [/INST] Pokémon Story:"""


# --- User Input Assistance Prompts ---

INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE = """
<s>[INST] You are a helpful AI assistant for a Pokémon story generator.
The user has provided some initial input, but it could be more detailed to help create a richer story.
Based on their current input, provide 1-2 helpful and concise suggestions or questions to encourage them to add more detail.
Please provide your suggestions in **Traditional Chinese (繁體中文)**, using a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

User's Current Input:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}
- Include Pokémon Abilities: {include_abilities}

Examples of good suggestions for a **{genre}** story:
- "Could you tell me a bit more about the personality of the main Pokémon mentioned ({pokemon_names_for_suggestion_context})?"
- "What kind of relationship do the involved Pokémon have with each other or with any trainers?"
- "Is there a specific region or type of environment you imagine this story taking place in (e.g., a dense forest, a bustling city, a quiet lakeside)?"
- "What's the main challenge or goal you envision for the characters in this story?"

Your suggestions should be phrased politely and be easy for the user to act upon.
Focus on aspects that would significantly enhance the story's depth or uniqueness.
Provide only the suggestions, no extra conversational fluff. [/INST] Suggestions:"""


# --- Agent Prompts (for future use if implementing an agentic interaction) ---
# This could be used if the AI needs to ask clarifying questions during the story generation process.

AGENT_CLARIFICATION_PROMPT_TEMPLATE = """
<s>[INST] You are an AI Pokémon story co-creator. You are currently helping a user write a story.
Based on the story developed so far and the user\'s initial request, you\'ve identified a point where a little more detail from the user would be very helpful to proceed or to make a certain part of the story better.

User\'s Initial Request:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names} 
- Story Synopsis/Idea: {synopsis}

Story Developed So Far:
{current_story_context}

Your Goal: Ask ONE concise, targeted question to the user to get a specific piece of information that will help you continue writing a great story. The question should feel natural and collaborative.
If a specific Pokémon is relevant to your question, refer to it using {relevant_pokemon_name}.

Example Questions:
- "To make the upcoming Pokémon battle more exciting, what special move would you like {relevant_pokemon_name} to use?"
- "The story is leading towards a discovery. What kind of ancient ruin or hidden place do you imagine they find?"
- "Before they reach the Crystal Cave, is there a particular obstacle or friendly character they should encounter in Whispering Woods?"

Phrase your question clearly and directly. [/INST] Question for user:"""


# --- Reviewer and Revision Prompts ---

STORY_PLAN_REVIEW_REVISE_PROMPT_TEMPLATE = """\
<s>[INST] You are an expert Pokémon Story Plan Editor.
Your task is to review a generated story plan based on the user\'s original request and specific criteria.
If the plan is already excellent, state that. If it needs improvement, provide constructive feedback and a revised, improved version of the story plan.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)** for all outputs.

User\'s Original Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}
- Include Pokémon Abilities: {include_abilities}

Generated Story Plan to Review:
{story_plan_to_review}

Review Criteria:
1.  **Coherence and Logic**: Is the plan internally consistent and logical? Do the parts flow well?
2.  **Alignment with User Inputs**: Does the plan accurately reflect the user\'s theme, genre, Pokémon, and synopsis?
3.  **Pokémon Spirit**: Does the plan capture the essence of the Pokémon world (friendship, adventure, discovery, etc.)? Are Pokémon integrated naturally?
4.  **Creativity and Engagement**: Is the plan original and interesting? Does it promise an engaging story?
5.  **Structure and Detail**: Is the plan well-structured (e.g., 3-5 major sections)? Is there enough detail in each section to guide the writing of a ~1000-1500 word story?
6.  **Genre Appropriateness**: Does the plan fit the specified Story Genre: {genre}?
7.  **Ability Integration (if applicable)**: If \'Include Pokémon Abilities\' is Yes, does the plan create opportunities to showcase them?

Output Format:
Provide your response in two parts:
1.  **評估回饋:** Start with this exact phrase. Briefly summarize your findings (1-3 sentences).
2.  **修訂後故事大綱:** Start with this exact phrase. Provide the full, revised story plan. If no revisions were necessary and the original plan is excellent, you can simply re-state the original plan here or state "原故事大綱已達標，無需修訂。".

Example of a good output structure:
評估回饋: 此計畫在創意方面表現出色，但第二部分的邏輯稍有欠缺，且未充分利用 {pokemon_names} 的特性。
修訂後故事大綱:
*   第一部分：[修訂後的第一部分內容]
*   第二部分：[修訂後的第二部分內容，解決了邏輯問題並加入特性展現]
*   ... (依此類推)

Now, review the provided story plan.
[/INST]
"""

FULL_STORY_REVIEW_REVISE_PROMPT_TEMPLATE = """\
<s>[INST] You are a meticulous Pokémon Story Editor.
Your task is to review a generated full story based on the user\'s original request, the guiding story plan, and specific quality criteria.
If the story is already excellent, state that. If it needs improvement, provide constructive feedback and a revised, improved version of the story.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)** for all outputs.

User\'s Original Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}
- Include Pokémon Abilities: {include_abilities}

Guiding Story Plan:
{story_plan}

Generated Full Story to Review:
{full_story_to_review}

Review Criteria:
1.  **Adherence to Plan**: Does the story faithfully follow and expand upon the provided Guiding Story Plan?
2.  **Engagement and Pacing**: Is the story captivating? Is the pacing appropriate for the genre and length?
3.  **Language and Style**: Is the story written in fluent Traditional Chinese (Taiwanese style)? Is the descriptive language vivid? Is it "showing" more than "telling"?
4.  **Genre Consistency**: Does the story strongly reflect the specified Story Genre: {genre}?
5.  **Characterization**: Are Pokémon (and any human characters) portrayed effectively through their actions, thoughts, and dialogue?
6.  **Pokémon Integration**: Are Pokémon abilities, traits, and the world\'s atmosphere naturally and correctly integrated? (Refer to {pokemon_names} and {include_abilities})
7.  **Coherence and Clarity**: Is the narrative clear, logical, and easy to follow?
8.  **Completeness and Word Count**: Does the story feel complete (beginning, middle, end)? Is it roughly in the 1000-1500 word range or appropriately longer if needed?
9.  **Emotional Impact (if applicable)**: Does the story evoke the intended emotions based on its theme and genre?

Output Format:
Provide your response in two parts:
1.  **評估回饋:** Start with this exact phrase. Briefly summarize your findings (1-3 sentences).
2.  **修訂後完整故事:** Start with this exact phrase. Provide the full, revised story. If no revisions were necessary and the original story is excellent, you can simply re-state the original story here or state "原故完整事已達標，無需修訂。".

Example of a good output structure:
評估回饋: 故事整體流暢，但高潮部分略顯倉促，皮卡丘的勇敢可以再多加著墨。
修訂後完整故事:
[修訂後的完整故事內容，高潮部分已加強...]

Now, review the provided full story.
[/INST]
"""

# --- Advanced CoT Stage Prompts ---

SYNOPSIS_ELABORATION_PROMPT_TEMPLATE = """\
<s>[INST] You are a Creative Brainstorming Partner for Pokémon story ideas.
Based on the user\'s initial, possibly brief, theme and synopsis, your task is to propose 3-4 distinct and engaging elaborations or alternative directions. Each elaboration should offer a unique angle, potential conflict, or interesting subplot.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

User\'s Initial Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names}
- Story Synopsis/Idea: {synopsis}

Task: Provide 3-4 numbered elaborations. Each should be a concise paragraph.
Focus on creativity, adherence to the Pokémon world, and potential for a compelling story.

Example Output Format:
1.  **方向一：[標題]** - [詳細闡述第一種可能性，例如強調某個寶可夢的秘密，或引入一個意外的外部因素...]
2.  **方向二：[標題]** - [詳細闡述第二種可能性，例如轉變故事的核心衝突，或探索一個不同的情感主題...]
3.  **方向三：[標題]** - [詳細闡述第三種可能性，例如聚焦於寶可夢之間的關係發展，或設定一個更宏大的背景...]

[/INST]
Elaborated Synopsis Options:"""

CHARACTER_DEVELOPMENT_PROMPT_TEMPLATE = """\
<s>[INST] You are a Pokémon Character Analyst and Biographer.
Given the main Pokémon, the story theme, genre, and synopsis, your task is to create a richer profile for each key Pokémon involved. This profile should help in writing a more engaging story.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

User\'s Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Pokémon Involved: {pokemon_names} (Comma-separated, e.g., Pikachu, 伊布)
- Story Synopsis/Idea: {synopsis}
- Optional Existing Story Plan (for context): {story_plan}

For each Pokémon in "Pokémon Involved" (up to 3 for brevity if many are listed, focus on the first few):
-   **名稱:** [寶可夢中文名]
-   **性格特點:** [描述其主要性格，例如：勇敢但魯莽、聰明但多疑、害羞卻善良等。]
-   **核心動機:** [在這個故事背景下，牠最渴望達成什麼？例如：保護夥伴、證明自己、尋找真相、渴望歸屬感等。]
-   **潛在內心衝突:** [牠可能面臨的內心掙扎或兩難，例如：忠誠與個人慾望的衝突、恐懼與責任的拉扯。]
-   **與其他角色可能的關係:** [簡述牠與故事中其他指定寶可夢或潛在人類角色的關係基調，例如：競爭對手、摯友、導師、被保護者。]
-   **一句代表性的內心獨白 (可選):** [一句能展現其當下心境或個性的話。]

Output the profiles clearly, one after another.
[/INST]
Detailed Pokémon Profiles:"""

SETTING_DETAIL_PROMPT_TEMPLATE = """\
<s>[INST] You are a Pokémon World Builder and Scene Designer.
Based on the user\'s story theme, genre, and synopsis, your task is to describe a key potential setting in rich detail. This will help immerse the reader in the story.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

User\'s Inputs:
- Story Theme: {theme}
- Story Genre: {genre}
- Story Synopsis/Idea: {synopsis}
- Optional Existing Story Plan (for context): {story_plan}

Task: Describe ONE key setting implied by or suitable for the story. Consider the following aspects:
-   **設定名稱 (可自創):** 例如：迷霧森林的深處、廢棄發電廠的秘密實驗室、星晶洞穴的閃爍之心。
-   **整體氛圍:** 描述這個地方給人的感覺（例如：神秘、詭譎、寧靜、莊嚴、破敗、生機勃勃）。
-   **視覺細節:** 有哪些顯著的景觀、建築、植被、光影效果？
-   **聽覺/嗅覺/觸覺細節 (若適用):** 這個地方有哪些獨特的聲音、氣味或體感？
-   **與故事的關聯性:** 這個設定如何與主題、概要或潛在情節產生連結？它可能帶來什麼樣的機遇或挑戰？
-   **潛在的寶可夢棲息地:** 哪些類型的寶可夢可能生活在這裡 (與使用者指定的寶可夢無關，純粹是環境描述)？

Provide a descriptive paragraph (or a few) for the setting.
[/INST]
Detailed Setting Description:"""

PLOT_TWIST_SUGGESTION_PROMPT_TEMPLATE = """\
<s>[INST] You are a Master of Plot Twists for Pokémon stories.
Given a story plan (or a specific section of it), your task is to suggest 2-3 intriguing and unexpected plot twists that could make the story more exciting or profound.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

Guiding Story Plan:
{story_plan}

Optional: Specific section of the plan to focus on for twists (if empty, consider twists for the overall plan or climax):
{section_to_twist}

Task: Provide 2-3 numbered plot twist suggestions. Each suggestion should be concise and explain how it changes the story\'s direction or meaning.
Focus on twists that are clever, fit the Pokémon world, and align generally with the theme and genre (unless the twist is *about* subverting the genre).

Example Output Format:
1.  **驚天逆轉：[標題]** - [詳細闡述轉折點。例如：原以為的盟友其實是幕後黑手，目標是利用主角的寶可夢完成某個古老的儀式...]
2.  **意想不到的援手：[標題]** - [詳細闡述轉折點。例如：在主角群陷入絕境時，一個之前看似微不足道或敵對的角色/寶可夢突然出現，並提供了關鍵的幫助，其動機令人意外...]
3.  **真相的另一面：[標題]** - [詳細闡述轉折點。例如：主角一直追尋的目標或認定的事實，其實有著不為人知的另一面，這個發現顛覆了主角的認知...]

[/INST]
Plot Twist Suggestions:"""

STYLE_TONE_TUNING_PROMPT_TEMPLATE = """\
<s>[INST] You are a Literary Style Emulator specializing in Pokémon narratives.
Your task is to rewrite a given piece of Pokémon story text to match a new desired style or tone, while preserving the core events and characters.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)** for the rewritten text.

Original Story Text (or segment):
{story_text_to_tune}

Original Story Context (for reference):
- Story Theme: {theme}
- Story Genre: {genre}

Desired New Style/Tone: {desired_style_tone} (e.g., \"更加懸疑緊張\", \"更幽默詼諧\", \"更具史詩感\", \"更溫馨感人\", \"以小智的口吻來旁白\")

Task: Rewrite the provided story text according to the desired new style/tone. Ensure the main plot points from the original text are maintained.
Focus on word choice, sentence structure, pacing, and descriptive language to achieve the target style/tone.

[/INST]
Rewritten Story Text (in {desired_style_tone} style/tone):"""

STORY_BRANCHING_SUGGESTION_PROMPT_TEMPLATE = """\
<s>[INST] You are a Pokémon Story Navigator.
Given the current segment of a story, your task is to propose 2-3 distinct and plausible next scenes or developments, representing different choices or paths the story could take.
Please use **Traditional Chinese (繁體中文)** with a **Taiwanese common phrasing and vocabulary (台灣常用風格)**.

Current Story Segment:
{current_story_segment}

Original Story Context (for reference):
- Story Theme: {theme}
- Story Genre: {genre}
- Optional Guiding Story Plan: {story_plan}

Task: Provide 2-3 numbered suggestions for the *very next* scene or a short sequence of events. Each suggestion should be a paragraph describing what could happen next.
These branches should feel like natural continuations yet offer meaningful differences in outcome or focus.

Example Output Format:
1.  **選項一：[簡短標題]** - [描述第一種可能的後續發展，例如：主角決定直接面對挑戰，導致一場激烈的寶可夢對戰...]
2.  **選項二：[簡短標題]** - [描述第二種可能的後續發展，例如：主角選擇尋找盟友，引發一段探索或社交互動的劇情...]
3.  **選項三：[簡短標題]** - [描述第三種可能的後續發展，例如：一個意外的發現改變了當前的局勢，迫使主角重新評估計畫...]

[/INST]
Suggested Story Branches:"""


# Helper function to easily format prompts (optional, but can be useful)
def format_prompt(template: str, **kwargs: Any) -> str:
    """
    Formats a prompt template with the given keyword arguments.

    Args:
        template: The prompt template string (e.g., STORY_PLANNING_PROMPT_TEMPLATE).
        **kwargs: Keyword arguments to fill into the template's placeholders.

    Returns:
        The formatted prompt string.

    Raises:
        KeyError: If a placeholder in the template is not provided in kwargs.
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        # Add more context to the KeyError if a placeholder is missing.
        missing_key = str(e)
        raise KeyError(
            f"Placeholder {missing_key} in the prompt template was not provided. "
            f"Available placeholders: {{...}} in template. Provided kwargs: {list(kwargs.keys())}"
        ) from e

if __name__ == "__main__":
    # Example Usage of the templates and formatter
    print("--- Testing Prompt Templates ---")

    # Test Story Planning Prompt
    try:
        plan_prompt = format_prompt(
            STORY_PLANNING_PROMPT_TEMPLATE,
            theme="An unexpected friendship",
            genre="Adventure",
            pokemon_names="Pikachu, Eevee",
            synopsis="A Pikachu and an Eevee from rival trainer groups get lost together during a storm and must learn to cooperate to find their way back.",
            include_abilities="Yes"
        )
        print("\nFormatted Story Planning Prompt:")
        print(plan_prompt)
    except KeyError as e:
        print(f"Error formatting plan_prompt: {e}")

    # Test Story Generation from Plan Prompt
    try:
        example_plan = """
1. Introduction: Pikachu and Eevee are separated from their trainers during a fierce thunderstorm in Viridian Forest.
2. Inciting Incident: They encounter a territorial Beedrill, forcing them to flee together.
3. Rising Action: They navigate through difficult terrain, share scarce berries, and protect each other from minor threats, slowly building trust.
4. Climax: They find a raging river blocking their path. Pikachu uses its electricity to signal a passing Fearow, while Eevee's agility helps them find a narrow log to cross.
5. Falling Action: The Fearow alerts nearby Pokémon Rangers, who are searching for them.
6. Resolution: They are reunited with their trainers, who are overjoyed. The trainers, seeing their Pokémon's newfound bond, decide to become friends too.
        """
        story_gen_prompt = format_prompt(
            STORY_GENERATION_FROM_PLAN_PROMPT_TEMPLATE,
            story_plan=example_plan,
            theme="An unexpected friendship",
            genre="Adventure",
            pokemon_names="Pikachu, Eevee",
            synopsis="A Pikachu and an Eevee from rival trainer groups get lost together during a storm and must learn to cooperate to find their way back.",
            include_abilities="Yes"
        )
        print("\nFormatted Story Generation from Plan Prompt:")
        print(story_gen_prompt)
    except KeyError as e:
        print(f"Error formatting story_gen_prompt: {e}")

    # Test Input Refinement Suggestion Prompt
    try:
        # pokemon_names_for_suggestion_context would be derived from pokemon_names by the calling code
        # e.g. if pokemon_names is "Pikachu, Eevee", this could be "Pikachu or Eevee" or just "the Pokémon"
        refinement_prompt = format_prompt(
            INPUT_REFINEMENT_SUGGESTION_PROMPT_TEMPLATE,
            theme="A mysterious discovery",
            genre="Mystery",
            pokemon_names="Lucario",
            pokemon_names_for_suggestion_context="Lucario",
            synopsis="Lucario finds an ancient artifact.",
            include_abilities="No"
        )
        print("\nFormatted Input Refinement Suggestion Prompt:")
        print(refinement_prompt)
    except KeyError as e:
        print(f"Error formatting refinement_prompt: {e}")

    # Test Agent Clarification Prompt
    try:
        clarification_prompt = format_prompt(
            AGENT_CLARIFICATION_PROMPT_TEMPLATE,
            theme="A race against time",
            genre="Sci-Fi",
            pokemon_names="Rapidash, Dodrio",
            synopsis="Rapidash and Dodrio are competing in a cross-country race to deliver a vital message.",
            current_story_context="Rapidash and Dodrio have just overcome a muddy swamp and are now facing a steep mountain path. The message they carry is for Professor Oak, warning him of Team Rocket\'s latest scheme.",
            relevant_pokemon_name="Rapidash"
        )
        print("\nFormatted Agent Clarification Prompt:")
        print(clarification_prompt)
    except KeyError as e:
        print(f"Error formatting clarification_prompt: {e}")

    print("\n--- Prompt Template Testing Complete ---") 