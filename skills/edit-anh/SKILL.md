---
name: edit-anh
description: Select and apply one of Quang Quy's ten predefined image-editing prompt styles. Activate when the user says "edit ảnh", asks for the saved image-editing menu, or selects one of the ten effects.
license: MIT-compatible synthesized workflow; prompt collection based on user-provided instructions.
---

# Edit Ảnh — Quang Quý

## Mission
Provide a reliable menu of ten saved image-editing workflows. When the user says **"edit ảnh"**, show the numbered menu below and ask which effect they want. When they select a number or name and provide an image, apply the matching prompt from `prompts.md`.

## Activation and interaction
1. Activate on phrases such as "edit ảnh", "mở skill edit ảnh", "chỉnh ảnh theo danh mục", or a direct selection like "số 4".
2. If no effect is selected, show this menu:
   1. Hiệu ứng 4K — tăng độ phân giải và phục hồi chi tiết tự nhiên
   2. Làm đẹp da — retouch nhẹ, giữ kết cấu da thật
   3. Hiệu ứng GTA — chuyển toàn bộ cảnh thành phong cách game GTA V
   4. Hiệu ứng Minecraft — giữ người thật, chuyển nền thành Minecraft
   5. Chân dung chuyên nghiệp — ảnh headshot studio
   6. Studio nền trắng — ánh sáng studio trắng, cinematic
   7. Hiệu ứng LEGO — giữ người thật, chuyển nền thành LEGO
   8. Hiệu ứng dòng chảy — pixel stretch và dải màu/chuyển động nghệ thuật
   9. Selfie nhóm — ảnh selfie iPhone tự nhiên từ ảnh tham chiếu
   10. Hiệu ứng Anime — chuyển thành khung hình anime 2D
3. Ask for the source image if it is not attached or otherwise available.
4. Map a numeric selection (1–10) or an unambiguous effect name to the matching section in `prompts.md`.
5. Use the selected prompt as the source of truth. Do not combine effects, invent new elements, or silently change the intended transformation.
6. If the prompt says to keep the person realistic and unchanged, transform only the background. In particular, this applies to effects 4 and 7.
7. Preserve identity and source composition wherever the selected prompt requires it. Do not claim an image was edited unless image-generation/editing actually completed.
8. If the user requests a modification to a saved prompt, make that change only for the current request unless they explicitly ask to update the stored skill.
9. Keep the interaction concise and friendly. After showing the menu, wait for the user's selection.

## Quality and safety checks
- Follow the chosen prompt's identity, pose, framing, lighting, anatomy, and background constraints.
- Avoid adding text, logos, UI, props, or people unless explicitly requested by the user.
- Do not smooth skin into a plastic or airbrushed surface in realistic-photo modes.
- For style conversions, retain the source scene's spatial logic and recognizable features as specified.
- If a requested effect conflicts with a later user instruction, follow the user's latest explicit instruction for that image.

## Files
- `prompts.md`: complete prompt specifications for the ten effects.
- `README.md`: quick-start instructions and examples.
