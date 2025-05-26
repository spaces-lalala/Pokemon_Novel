from openai import OpenAI
from typing import Optional, Dict, Any, AsyncIterator
import asyncio

from config.settings import settings # Assuming your settings.py is in a config folder

class OpenAIConfigError(Exception):
    """Custom exception for OpenAI configuration errors."""
    pass

class LLMService:
    """
    A service class to interact with Large Language Models, currently OpenAI.

    This class handles the initialization of the LLM client and provides
    methods for generating text completions, potentially with streaming.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-4-turbo") -> None:
        """
        Initializes the LLMService.

        Args:
            api_key: The OpenAI API key. If None, it will be fetched from settings.
            model_name: The name of the OpenAI model to use.

        Raises:
            OpenAIConfigError: If the API key is not provided and not found in settings.
        """
        resolved_api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not resolved_api_key:
            raise OpenAIConfigError(
                "OpenAI API key not provided and not found in environment settings. "
                "Please set OPENAI_API_KEY in your .env file or pass it directly."
            )
        
        self.client = OpenAI(api_key=resolved_api_key)
        self.model_name = model_name

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs: Any
    ) -> str: # Change to AsyncIterator[str] if stream=True and implemented
        """
        Generates text using the OpenAI API based on the provided prompt.

        Args:
            prompt: The prompt to send to the LLM.
            max_tokens: The maximum number of tokens to generate.
            temperature: Controls randomness. Lower is more deterministic.
            stream: Whether to stream the response token by token.
            **kwargs: Additional keyword arguments to pass to the OpenAI API.

        Returns:
            The generated text as a string.
            If stream is True, this would ideally return an AsyncIterator[str].
            For simplicity in this initial version, streaming is not fully implemented
            for the return type but the parameter is present for future extension.
        """
        if stream:
            # Streaming implementation would go here.
            # For now, let's keep it simple and return the full string even if stream=True
            # or raise a NotImplementedError.
            # For a true async streaming generator, the method signature would be:
            # async def generate_text_stream(...) -> AsyncIterator[str]:
            #     async for chunk in ...:
            #         yield chunk
            # For this initial pass, we'll simulate by just calling non-stream endpoint.
            pass # Placeholder for actual streaming logic

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream, # Pass stream to API, even if we don't handle it fully yet
                **kwargs
            )

            if stream:
                # This part needs to be properly implemented for streaming
                # For now, it will likely not work as expected with client.chat.completions.create
                # when stream=True without an event loop for handling chunks.
                # Let's assume for now, if stream is True, we'd iterate over `response`
                # and collect content. This is a simplification.
                full_response_content = ""
                # The actual streaming response object needs to be iterated differently.
                # This is a placeholder for a more complex handling or a different API call.
                # if hasattr(response, '__aiter__'): # This check is not quite right for OpenAI's sync client in thread
                #    async for chunk in response:
                #        if chunk.choices[0].delta.content:
                #            full_response_content += chunk.choices[0].delta.content
                #    return full_response_content
                # else: # Fallback for non-streaming or mis-handled stream
                # This block is problematic for actual streaming with the sync client in a thread.
                # It will likely return the generator object itself or error.
                # For now, if stream=True, we'll just return an empty string or error, 
                # as proper async streaming from a sync client in a thread is more complex.
                # A better approach for true async streaming would use an AsyncOpenAI client.
                print("Warning: Streaming requested but not fully implemented in this version. Returning full response if available, or empty.")
                # Fallback to trying to get content if not a stream iterator
                if hasattr(response, 'choices') and response.choices:
                     return response.choices[0].message.content or ""
                return "[Streaming response not fully processed]"
            else:
                return response.choices[0].message.content or ""
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during OpenAI API call: {e}")
            # Consider re-raising a custom exception or returning a specific error message
            raise OpenAIConfigError(f"OpenAI API call failed: {e}")

# Example Usage (for testing this module directly)
async def main_test() -> None:
    print("Testing LLMService...")
    try:
        # Ensure you have a .env file with OPENAI_API_KEY set
        # or pass the key directly: LLMService(api_key="your_key")
        llm_service = LLMService(model_name="gpt-3.5-turbo") # Using a cheaper model for testing
        
        prompt_text = "Translate the following English text to French: 'Hello, world!'"
        print(f"Sending prompt: {prompt_text}")
        
        # Test non-streaming generation
        generated_text_non_stream = await llm_service.generate_text(prompt_text, max_tokens=50)
        print(f"Generated text (non-streaming):\n{generated_text_non_stream}")

        # Test streaming (partially implemented - will show warning)
        # print("\nTesting streaming (expect a warning and potentially not true streaming behavior yet):")
        # async for chunk in llm_service.generate_text(prompt_text, max_tokens=50, stream=True):
        # print(chunk, end="")
        # print()
        # For now, the stream=True call will use the simplified handling:
        generated_text_stream = await llm_service.generate_text(prompt_text, max_tokens=50, stream=True)
        print(f"Generated text (simulated streaming call):\n{generated_text_stream}")

    except OpenAIConfigError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # To run this test, you would typically do: python -m core.llm_services
    # Make sure your .env file is in the root of the project for settings to load.
    # If you are in the 'core' directory, you might need to adjust Python path or run from root.
    # Example: PYTHONPATH=. python core/llm_services.py (from project root)
    
    # Running an async function from a synchronous context
    # For Python 3.7+
    asyncio.run(main_test()) 