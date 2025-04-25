"""
storybook_pipeline.py
Create a fully illustrated storybook with GPT-4o + gpt-image-1.

Prereqs
-------
pip install --upgrade openai python-dotenv aiofiles Pillow
Put OPENAI_API_KEY="sk-…" in a .env file or export it.

Folder layout after a run
-------------------------
Barnaby_s_Big_Flight/
├── story.json              # textual structure from GPT-4o
├── refs/                   # baseline character images
│   ├── Barnaby.png
│   └── Rosie.png
├── cover.png
├── pages/
│   ├── page_01.png
│   ├── page_02.png
│   └── …
└── book.pdf                # (optional) stitched final PDF
"""
from __future__ import annotations

import asyncio, base64, json, pathlib, textwrap
from typing import Dict, List

import aiofiles
from dotenv import load_dotenv
from openai import AsyncOpenAI                           # async = massive speed-up

###############################################################################
# 0.  CONFIGURATION
###############################################################################
load_dotenv()
client = AsyncOpenAI()                                   # uses env var OPENAI_API_KEY
IMG_MODEL = "gpt-image-1"
IMG_SIZE = "1536x1024"
IMG_QUALITY = "medium"
ROOT = pathlib.Path().resolve()

###############################################################################
# 1.  UTILS
###############################################################################
def b64_to_file(b64: str, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(b64))

async def async_write(path: pathlib.Path, data: bytes) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)

###############################################################################
# 2.  GPT-4o:  STORY STRUCTURE
###############################################################################
GPT4_TEMPLATE = textwrap.dedent("""
    You are StorySmith 9000, the world’s finest children’s-book author.

    Goal → output **one JSON object** with exactly these keys, no more, no less:  
    • "title"    string  
    • "characters" object where each key = character name and the value has one key
        • "appearance" detailed visual description of that character  
    • "cover_description" landscape-oriented prompt for the cover image  
    • "pages" array of length {num_pages}; each element is an object with:
        • "page" integer page number starting at 1  
        • "text" 2–3 lively sentences of narration  
        • "image_description" concise, vivid prompt for that page’s illustration  
        (≤ 3 on-model characters, no text inside the picture, interesting pose / angle (switch it up so \
            every page looks unique here, not every page needs to be a close-up of the character, make them do stuff!))

    Constraints
    -----------  
    * Output **only the JSON**—no markdown, no back-ticks, no commentary.  
    * Use straight double quotes `"`, never fancy quotes.  
    * No trailing commas anywhere.  
    * Every character that appears in any page must already exist in "characters".
    * Only ever have 1 to 3 main characters per story! - keep it simple!!  
    * Do **not** invent new keys or change their spelling.

    User request
    ------------  
    Topic : {topic}  
    Style : {style}  
    Pages : {num_pages}

    Produce the JSON now.
""").strip()

async def generate_story(topic:str, style:str, n_pages:int) -> Dict:
    prompt = (
        f"{GPT4_TEMPLATE}\n\n"
        f"USER INPUT:\n"
        f"topic = {topic}\nstyle = {style}\npages = {n_pages}"
    )
    rsp = await client.chat.completions.create(
        model="gpt-4.1",
        response_format={"type":"json_object"},
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
    )
    story = json.loads(rsp.choices[0].message.content)
    return story

###############################################################################
# 3.  gpt-image-1 HELPERS
###############################################################################
async def gen_image(prompt:str, out_path:pathlib.Path):
    img_rsp = await client.images.generate(
        model=IMG_MODEL,
        prompt=prompt,
        n=1,
        size=IMG_SIZE,
        quality=IMG_QUALITY,    # "low", "medium", "high"
    )
    await async_write(out_path, base64.b64decode(img_rsp.data[0].b64_json))

async def edit_image(prompt:str, ref_paths:List[pathlib.Path], out_path:pathlib.Path):
    # open files in binary mode for the SDK
    refs = [open(p, "rb") for p in ref_paths]
    img_rsp = await client.images.edit(
        model=IMG_MODEL,
        image=refs,
        prompt=prompt,
        n=1,
        size=IMG_SIZE,
        quality=IMG_QUALITY,    # "low", "medium", "high"
    )
    await async_write(out_path, base64.b64decode(img_rsp.data[0].b64_json))
    for f in refs: f.close()

###############################################################################
# 4.  MAIN PIPELINE
###############################################################################
async def build_book(topic:str, style:str, n_pages:int):
    print("📚 Starting book generation...")
    # 4.1  TEXT
    print("🖋️ Generating story text...")
    story = await generate_story(topic, style, n_pages)
    print(f"✅ Story text generated: {story['title']}")
    title_sanitised = story["title"].replace(" ", "_")
    stories_dir = ROOT / "stories"
    stories_dir.mkdir(exist_ok=True)
    book_dir = stories_dir / title_sanitised
    (book_dir / "refs").mkdir(parents=True, exist_ok=True)
    (book_dir / "pages").mkdir(exist_ok=True)

    # save JSON
    (book_dir / "story.json").write_text(json.dumps(story, indent=2))

    # 4.2  CHARACTER REFERENCE IMAGES  (images.generate)  — in parallel
    print("🎨 Generating character reference images...")
    char_tasks = []
    char_paths = {}
    for name, meta in story["characters"].items():
        prompt = f"{meta['appearance']} — {style}"
        out = book_dir / "refs" / f"{name}.png"
        char_paths[name] = out
        char_tasks.append(gen_image(prompt, out))
    await asyncio.gather(*char_tasks)
    print("✅ Character reference images generated.")

    # 4.3  COVER IMAGE  (images.edit)
    print("🖼️ Generating cover image...")
    cover_prompt = f"{story['cover_description']} — {style}"
    cover_out = book_dir / "cover.png"
    await edit_image(cover_prompt, list(char_paths.values()), cover_out)
    print("✅ Cover image generated.")

    # 4.4  PAGE IMAGES  (images.edit)  — also parallel
    print("📖 Generating page images...")
    # --- inside build_book() just before page loop -----------------
    async def make_page(pg: Dict):
        idx = pg["page"]
        out = book_dir / "pages" / f"page_{idx:02}.png"
        page_prompt = f"{pg['image_description']} — {style}"
        await edit_image(page_prompt, [cover_out, *char_paths.values()], out)


    await asyncio.gather(*(make_page(p) for p in story["pages"]))
    print("✅ Page images generated.")

    print(f"✅  Finished!  Book stored at {book_dir}")

###############################################################################
# 5.  CLI ENTRY-POINT
###############################################################################
if __name__ == "__main__":
    # ---- quick smoke test ----
    topic = "Tiny magical communities living in secret corners of a big city"
    style = "studio ghibli animation style, vibrant anime colors, pastel color palette, gentle rounded shapes, expressive characters and nature"
    asyncio.run(
        build_book(
            topic=topic,
            style=style,
            n_pages=6,
        )
    )
