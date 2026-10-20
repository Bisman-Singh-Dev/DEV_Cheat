import urllib.parse
import webbrowser
from typing import Optional, List
import pyperclip

def open_question_in_chatgpt(question_text: str, options: Optional[List[str]] = None, title: str = "") -> str:
    """
    Constructs a clear, rigorous prompt asking ChatGPT to solve the question step by step,
    copies the prompt directly to the Windows clipboard, and opens ChatGPT in the default browser
    with the prompt pre-filled in the query!
    """
    options_formatted = ""
    if options and len(options) > 0:
        clean_opts = [opt.strip() for opt in options if opt.strip()]
        if clean_opts:
            options_formatted = "\n\nOptions:\n" + "\n".join(clean_opts)

    prompt = f"""Please solve this question step by step with 100% mathematical and conceptual rigor:

{question_text.strip()}{options_formatted}

Please provide:
1. Direct final answer / correct option.
2. Step-by-step numbered derivation."""

    # 1. Copy to clipboard so user can paste immediately (Ctrl+V) if needed
    try:
        pyperclip.copy(prompt)
        print("[ChatGPT Service] Prompt copied to clipboard!")
    except Exception as e:
        print(f"[ChatGPT Service] Clipboard copy error: {e}")

    # 2. Open ChatGPT in browser with query parameter pre-filled
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        chatgpt_url = f"https://chatgpt.com/?q={encoded_prompt}"
        webbrowser.open(chatgpt_url)
        print(f"[ChatGPT Service] Opened ChatGPT in browser with pre-filled question prompt!")
    except Exception as e:
        print(f"[ChatGPT Service] Browser open error: {e}")
        try:
            webbrowser.open("https://chatgpt.com/")
        except Exception:
            pass

    return prompt
