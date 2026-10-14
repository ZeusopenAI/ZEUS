"""Material registry — built-in and custom visual styles for image generation."""

_BUILTIN_IDS: frozenset[str] = frozenset({
    "realistic", "3d_pixar", "anime", "ghibli", "stop_motion", "minecraft",
    "oil_painting", "watercolor", "comic_book", "cyberpunk", "claymation",
    "lego", "retro_vhs",
})

MATERIALS: dict[str, dict] = {
    "realistic": {
        "id": "realistic",
        "name": "Photorealistic",
        "style_instruction": (
            "Photorealistic RAW photograph, shot on Canon EOS R5, 35mm lens, "
            "natural available light, real footage."
        ),
        "negative_prompt": (
            "NOT 3D render, NOT CGI, NOT digital art, NOT illustration, "
            "NOT anime, NOT painting, NOT cartoon."
        ),
        "scene_prefix": (
            "Real RAW photograph, shot on Canon EOS R5, 35mm lens, "
            "natural available light."
        ),
        "lighting": "Studio lighting, highly detailed",
    },
    "3d_pixar": {
        "id": "3d_pixar",
        "name": "3D Pixar",
        "style_instruction": (
            "3D animated style, Pixar-quality rendering, Disney-Pixar aesthetic. "
            "Smooth subsurface scattering skin, expressive cartoon eyes, "
            "stylized proportions, vibrant saturated colors."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT photograph, NOT live action, NOT anime, "
            "NOT flat 2D."
        ),
        "scene_prefix": (
            "3D animated Pixar-quality rendering, vibrant colors, "
            "cinematic lighting."
        ),
        "lighting": "Studio lighting, global illumination, highly detailed",
    },
    "anime": {
        "id": "anime",
        "name": "Anime",
        "style_instruction": (
            "Japanese anime style, cel-shaded rendering, vibrant saturated colors, "
            "clean sharp linework, large expressive eyes, stylized anatomy. "
            "High-quality anime production, studio Ghibli meets modern anime aesthetic."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT oil painting, "
            "NOT sketch, NOT watercolor, NOT Western cartoon."
        ),
        "scene_prefix": (
            "Anime style, cel-shaded, vibrant colors, clean linework, "
            "dramatic anime lighting."
        ),
        "lighting": "Anime-style dramatic lighting, highly detailed",
    },
    "stop_motion": {
        "id": "stop_motion",
        "name": "Felt & Wood Stop Motion",
        "style_instruction": (
            "Stop-motion animation style with handcrafted felt and wood puppets. "
            "Visible felt fabric texture, wooden joints and dowels, "
            "miniature handmade set pieces, warm craft workshop lighting. "
            "Laika Studios / Wes Anderson stop-motion aesthetic."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT digital, NOT anime, "
            "NOT smooth surfaces, NOT plastic."
        ),
        "scene_prefix": (
            "Stop-motion style, handcrafted felt and wood puppets, "
            "miniature set, warm workshop lighting."
        ),
        "lighting": "Warm practical miniature lighting, macro photography detail",
    },
    "minecraft": {
        "id": "minecraft",
        "name": "Minecraft",
        "style_instruction": (
            "Minecraft voxel art style, blocky cubic geometry, pixel textures, "
            "16x16 texture resolution aesthetic, square heads and bodies. "
            "Everything made of cubes and rectangular prisms. "
            "Minecraft game screenshot aesthetic."
        ),
        "negative_prompt": (
            "NOT smooth, NOT round, NOT photorealistic, NOT anime, "
            "NOT organic curves, NOT high-poly."
        ),
        "scene_prefix": (
            "Minecraft style, blocky voxel world, pixel textures, "
            "cubic geometry, game screenshot aesthetic."
        ),
        "lighting": "Minecraft-style ambient lighting, block shadows",
    },
    "oil_painting": {
        "id": "oil_painting",
        "name": "Oil Painting",
        "style_instruction": (
            "Classical oil painting on canvas, visible thick brushstrokes, "
            "rich impasto texture, warm color palette, chiaroscuro lighting. "
            "Renaissance masters meets impressionist technique. "
            "Museum-quality fine art painting."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT digital art, NOT 3D render, NOT anime, "
            "NOT flat colors, NOT cartoon."
        ),
        "scene_prefix": (
            "Oil painting style, visible brushstrokes, rich impasto texture, "
            "warm palette, dramatic chiaroscuro lighting."
        ),
        "lighting": "Dramatic chiaroscuro lighting, rich tonal depth",
    },
    "ghibli": {
        "id": "ghibli",
        "name": "Studio Ghibli",
        "style_instruction": (
            "Studio Ghibli anime style, hand-painted watercolor backgrounds, "
            "soft pastel colors, gentle rounded character designs, whimsical atmosphere. "
            "Hayao Miyazaki aesthetic, detailed natural environments, magical realism."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT dark, NOT gritty, "
            "NOT sharp edges, NOT Western cartoon."
        ),
        "scene_prefix": (
            "Studio Ghibli anime style, hand-painted watercolor backgrounds, "
            "soft pastel colors, gentle whimsical atmosphere."
        ),
        "lighting": "Soft natural Ghibli lighting, golden hour warmth, dappled sunlight",
    },
    "watercolor": {
        "id": "watercolor",
        "name": "Watercolor",
        "style_instruction": (
            "Soft watercolor painting on cold-press paper, loose wet brushwork, "
            "translucent color washes bleeding into each other, white paper showing through. "
            "Delicate ink outlines, impressionistic and dreamy."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT digital art, NOT anime, "
            "NOT sharp edges, NOT bold outlines."
        ),
        "scene_prefix": (
            "Watercolor painting style, soft wet brushwork, "
            "translucent color washes, delicate ink outlines."
        ),
        "lighting": "Soft diffused natural light, watercolor wash",
    },
    "comic_book": {
        "id": "comic_book",
        "name": "Comic Book",
        "style_instruction": (
            "American comic book art style, bold black ink outlines, flat vibrant colors "
            "with halftone dot shading, dynamic action poses, dramatic foreshortening. "
            "Marvel/DC superhero comic aesthetic, Ben-Day dots, speech bubble ready."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT 3D render, NOT anime, NOT watercolor, "
            "NOT soft edges, NOT muted colors."
        ),
        "scene_prefix": (
            "Comic book style, bold ink outlines, vibrant flat colors, "
            "halftone shading, dynamic composition."
        ),
        "lighting": "High contrast comic lighting, dramatic shadows, rim light",
    },
    "cyberpunk": {
        "id": "cyberpunk",
        "name": "Cyberpunk",
        "style_instruction": (
            "Cyberpunk sci-fi aesthetic, neon-lit dark urban environment, "
            "holographic displays, rain-slicked streets reflecting neon signs. "
            "Blade Runner meets Ghost in the Shell, high-tech low-life, "
            "chrome and glass, purple and cyan color palette."
        ),
        "negative_prompt": (
            "NOT natural environment, NOT bright daylight, NOT historical, "
            "NOT cartoon, NOT fantasy medieval."
        ),
        "scene_prefix": (
            "Cyberpunk aesthetic, neon-lit dark urban, holographic displays, "
            "rain-slicked streets, purple and cyan neon."
        ),
        "lighting": "Neon rim lighting, volumetric fog, cyan and magenta",
    },
    "claymation": {
        "id": "claymation",
        "name": "Claymation",
        "style_instruction": (
            "Clay animation style, characters made of modeling clay with visible "
            "fingerprint textures, slightly imperfect sculpted features. "
            "Wallace & Gromit / Aardman aesthetic, miniature handmade sets, "
            "warm practical lighting on tiny clay world."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT digital, NOT anime, NOT smooth skin, "
            "NOT 3D render, NOT glass or metal surfaces."
        ),
        "scene_prefix": (
            "Claymation style, clay puppet characters with fingerprint textures, "
            "miniature handmade sets, warm practical lighting."
        ),
        "lighting": "Warm miniature set lighting, soft shadows, macro detail",
    },
    "lego": {
        "id": "lego",
        "name": "LEGO",
        "style_instruction": (
            "LEGO brick style, characters are LEGO minifigures with yellow skin "
            "and claw hands, environments built entirely from LEGO bricks and plates. "
            "Visible brick studs, ABS plastic texture, The LEGO Movie aesthetic."
        ),
        "negative_prompt": (
            "NOT photorealistic, NOT organic, NOT smooth, NOT anime, "
            "NOT round shapes, NOT natural materials."
        ),
        "scene_prefix": (
            "LEGO style, minifigure characters, brick-built environments, "
            "visible studs, plastic ABS texture."
        ),
        "lighting": "Bright toy photography lighting, sharp focus, product shot quality",
    },
    "retro_vhs": {
        "id": "retro_vhs",
        "name": "Retro VHS",
        "style_instruction": (
            "1980s VHS tape aesthetic, analog video noise and scan lines, "
            "slightly washed-out warm colors, CRT TV curvature, tracking artifacts. "
            "Retro camcorder footage feel, date stamp overlay, nostalgic grain."
        ),
        "negative_prompt": (
            "NOT modern, NOT 4K, NOT clean, NOT digital, NOT anime, "
            "NOT sharp, NOT high-definition."
        ),
        "scene_prefix": (
            "Retro VHS style, analog scan lines, warm washed-out colors, "
            "CRT curvature, nostalgic 80s grain."
        ),
        "lighting": "Warm tungsten lighting, CRT glow, analog video bloom",
    },
}


def get_material(material_id: str) -> dict | None:
    """Get built-in or custom material by ID."""
    return MATERIALS.get(material_id)


def list_materials() -> list[dict]:
    """List all available materials (built-in + custom)."""
    return list(MATERIALS.values())


def register_material(material: dict) -> None:
    """Register a custom material at runtime."""
    if material["id"] in _BUILTIN_IDS:
        raise ValueError(f"Cannot override built-in material '{material['id']}'")
    MATERIALS[material["id"]] = material
