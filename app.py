"""Gradio UI: text and/or image in -> Gemma 4 -> structured JSON out."""

import gradio as gr

import gemma
import prompts
from utils import format_error, parse_model_json


def analyze(text, image):
    """Generator, so the UI can show a loading state before the model answers.

    Yields (status, result, raw_response, button_update).
    """
    text = (text or "").strip()
    if not text and image is None:
        yield "Error: enter some text, upload an image, or both.", None, "", gr.update()
        return

    mode = "text + image" if text and image is not None else "image" if image is not None else "text"
    yield f"Working... asking Gemma ({mode})", None, "", gr.update(interactive=False)

    raw = ""
    try:
        user_prompt = prompts.build_user_prompt(text, has_image=image is not None)
        if image is not None:
            raw = gemma.generate_multimodal(user_prompt, image, prompts.SYSTEM_PROMPT)
        else:
            raw = gemma.generate_text(user_prompt, prompts.SYSTEM_PROMPT)
        result = parse_model_json(raw)
    except (gemma.GemmaError, ValueError) as e:
        # `raw` is still shown so a bad-JSON response can be inspected.
        yield f"Error: {format_error(e)}", None, raw, gr.update(interactive=True)
        return

    yield "Done.", result, raw, gr.update(interactive=True)


with gr.Blocks(title="Gemma 4 Hackathon Starter") as demo:
    gr.Markdown("# Gemma 4 Hackathon Starter\nEnter text, upload an image, or both.")
    with gr.Row():
        with gr.Column():
            text_in = gr.Textbox(label="Text", lines=5, placeholder="Describe the situation or ask a question...")
            image_in = gr.Image(label="Image (optional)", type="pil")
            submit = gr.Button("Analyze", variant="primary")
        with gr.Column():
            status = gr.Textbox(label="Status", interactive=False)
            result_out = gr.JSON(label="Result")
            with gr.Accordion("Raw model response", open=False):
                raw_out = gr.Textbox(show_label=False, lines=8, interactive=False)

    submit.click(
        analyze,
        inputs=[text_in, image_in],
        outputs=[status, result_out, raw_out, submit],
    )


if __name__ == "__main__":
    try:
        gemma.get_client()  # fail fast, with a clear message, if the API key is missing
    except gemma.GemmaError as e:
        raise SystemExit(f"Configuration error: {e}")
    demo.launch()
