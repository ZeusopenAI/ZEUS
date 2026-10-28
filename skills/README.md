# Quang Quy AI / Zeus — Skills Directory

This directory contains reusable, domain-specific skills for the Zeus / Hermes Agent platform.

## Available Skills

### 1. qai-developer-manager

**Purpose**: Principal engineering manager and senior developer for complex software-engineering tasks.

**When to use**:
- Repository-level debugging and multi-file code modifications
- Fixing provider, auth, or model-routing failures
- Android / Termux / Colab environment validation
- Ensuring test coverage, CI verification, and safe rollback mechanisms

Full guide: [skills/qai-developer-manager/SKILL.md](qai-developer-manager/SKILL.md)

---

### 2. hermes-project-analyst-code-manager

**Purpose**: Persistent project management and code analysis for the Hermes Agent runtime.

**When to use**:
- Diagnosing Hermes provider/auth switching issues
- Planning minimal code/config fixes while preserving architecture
- Implementing and validating changes across environments
- Managing Git history, clean commits, and GitHub repository synchronizations

Full guide: [skills/hermes-project-analyst-code-manager/SKILL.md](hermes-project-analyst-code-manager/SKILL.md)

---

### 3. second-brain

**Purpose**: Capture, organize, and recall everything exchanged with ChatGPT, Claude.ai, Gemini, and Hermes into one searchable memory.

**When to use**:
- Ingesting chat exports (`conversations.json`, Claude zip export, Gemini Takeout).
- Recalling past discussions across AI assistants.
- Handing shared memory (`USER.md` / `MEMORY.md`) to external AIs so they continue threads seamlessly.
- Multi-model routing (ChatGPT: strategy, Claude: code, Gemini: research).

Full guide: [docs/second-brain.md](../docs/second-brain.md) & [skills/second-brain/SKILL.md](second-brain/SKILL.md)

---

### 4. flowkit-ai-filmmaker

**Purpose**: Plan, operate, and maintain the standalone FlowKit AI video application (FastAPI/SQLite agent, Chrome MV3 bridge, React dashboard, and FFmpeg post-processing).

**When to use**:
- Running the documented video-production workflow for Shorts, Reels, YouTube, or commercial content.
- Creating and reviewing projects, reference images, scene images, clips, narration, and final exports.
- Diagnosing Google Flow, extension, or pipeline issues; modifying FlowKit code under `flowkit/`.

Character references can improve visual continuity but do not guarantee identical outputs; supported chaining depends on the selected model and current Flow API.

Implementation: [flowkit/](../flowkit/) — standalone FlowKit agent, extension, dashboard, tests, and workflow guides. Start here: [docs/FLOWKIT_INTEGRATION.md](../docs/FLOWKIT_INTEGRATION.md).

Full guide: [skills/flowkit-ai-filmmaker/SKILL.md](flowkit-ai-filmmaker/SKILL.md) & [memory/flowkit-ai-filmmaking.md](../memory/flowkit-ai-filmmaking.md)

---

### 5. edit-anh

**Purpose**: Danh mục 10 quy trình chỉnh sửa ảnh (4K, làm đẹp da, GTA, Minecraft, headshot, studio trắng, LEGO, dòng chảy, selfie nhóm, anime).

**When to use**: Người dùng nói "edit ảnh" hoặc chọn số 1–10 trong menu.

Full guide: [skills/edit-anh/SKILL.md](edit-anh/SKILL.md) & [skills/edit-anh/prompts.md](edit-anh/prompts.md)

---

### 6. hermes-github-access

**Purpose**: Quy trình để Hermes dùng GitHub token đã cấu hình — commit, push, mở PR, sửa workflow — kèm ranh giới an toàn.

**When to use**: Khi Hermes được yêu cầu sửa/push code, mở PR, đổi file CI, hoặc xử lý ảnh/video trên máy.

Full guide: [skills/hermes-github-access/SKILL.md](hermes-github-access/SKILL.md) & [docs/HERMES_GITHUB_TOKEN.md](../docs/HERMES_GITHUB_TOKEN.md)

---

### 7. hermes-media-tools

**Purpose**: Xử lý ảnh/video hàng loạt (Pillow + ffmpeg) và đọc bài viết web thành văn bản sạch — offline, không tốn credit.

**When to use**: Khi cần resize/crop/nén ảnh, cắt/nén video, xuất thumbnail, đóng watermark của chính mình, hoặc đọc/tóm tắt một bài viết từ URL.

Full guide: [skills/hermes-media-tools/SKILL.md](hermes-media-tools/SKILL.md) & [docs/HERMES_FULL_CAPABILITY.md](../docs/HERMES_FULL_CAPABILITY.md)

---

### 8. hermes-owner

**Purpose**: Kênh cố vấn **TÙY CHỌN** — soạn gợi ý cho phiên agent, đọc báo cáo
`OUTBOX.md`, kiểm tra seal/hạn gợi ý. Hermes **không phải chủ**; thiếu gợi ý không chặn phiên.

**When to use**: Khi Operator muốn Hermes góp ý qua `.ai/handoff/INBOX.md`, hoặc khi cần
chẩn đoán vì sao không có gợi ý. Bỏ qua hoàn toàn cũng đúng luật.

Full guide: [skills/hermes-owner/SKILL.md](hermes-owner/SKILL.md),
[docs/HERMES_OWNER_PROTOCOL.md](../docs/HERMES_OWNER_PROTOCOL.md) &
[docs/HERMES_SESSION_ERROR_RCA.md](../docs/HERMES_SESSION_ERROR_RCA.md).

---

## Đồng bộ sang Hermes

Mọi skill trong thư mục này được đẩy vào runtime Hermes bằng:

```bash
bash scripts/hermes-sync.sh          # hoặc --with-memory
```

Script còn sinh thêm skill **`zeus-context`** (tự động, đừng sửa tay) chứa trạng thái
repo mới nhất: Status, TODO, Roadmap, quy tắc AGENTS, danh sách docs/skills.

- Codespace: tự chạy mỗi lần mở (`.devcontainer/`).
- VPS: systemd timer 15 phút (`deploy/vps/hermes-repo-sync.timer`).
- CI: `.github/workflows/hermes-skill-sync.yml` validate + đóng gói.

Chi tiết: [docs/HERMES_AUTO_SYNC.md](../docs/HERMES_AUTO_SYNC.md)

---

## Skill Development Guidelines

Each skill should:
- Have a clear, single responsibility
- Include distinct workflow phases
- Specify when and when-not to use it
- Provide safety guardrails and stop conditions
- Define what "done" means
- Support validation and reproducibility
