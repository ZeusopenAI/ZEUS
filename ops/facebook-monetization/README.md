# Facebook Lead & Monetization OS V1

Đây là lớp vận hành nội dung cho Quang Quý AI. Mục tiêu chính là tạo **lead đủ điều kiện cho dịch vụ AI Automation**; khả năng kiếm tiền từ nội dung Facebook là KPI phụ.

## Trạng thái đang áp dụng

| Hạng mục | Trạng thái |
| --- | --- |
| Facebook payout review | `META_REVIEW_UI_UNAVAILABLE` |
| Facebook Publish API | Chưa kết nối/xác minh |
| Facebook Insights API | Chưa kết nối/xác minh |
| Notion dashboard integration | Cần được chia sẻ cho integration |
| Chế độ chạy | `DRAFT_ONLY` |

`DRAFT_ONLY` là có chủ ý: hệ thống có thể tự lập kế hoạch, kiểm tra dữ liệu và chuẩn bị brief; nó không được đăng Facebook, thay đổi payout hoặc lặp đơn xem xét lại Meta. GitHub/Hermes không thể sửa lỗi trang xét duyệt của Meta hay mở khóa payout.

## Phân luồng kênh không được hiểu nhầm

| Đích xuất bản | Trạng thái trong V1 |
| --- | --- |
| Instagram Creator/Business | Chỉ sau OAuth và Content Publishing API chính thức |
| Facebook Page | Chỉ sau OAuth và Pages/Reels Publishing API chính thức |
| Facebook cá nhân | Chỉ thao tác tay trong ứng dụng Facebook/Instagram gốc |
| Instagram → Facebook cá nhân | Không nằm trong automation; không được đánh dấu là cross-post thành công |

Meta mô tả API đăng Reels cho **Facebook Page**, và giới hạn cross-post Reels API ở Facebook Pages; nó không phải endpoint đăng lên profile cá nhân. Xem [Reels Publishing API](https://developers.facebook.com/documentation/video-api/guides/reels-publishing) và [Pages API Posts](https://developers.facebook.com/documentation/pages-api/posts). Nếu anh chủ động bấm chia sẻ sang Facebook cá nhân trong app Instagram, đó là thao tác native thủ công, tách khỏi workflow API/Make.

## Nguồn dữ liệu

- [`state.json`](state.json): trạng thái tích hợp và các cổng an toàn.
- [`content-backlog.json`](content-backlog.json): backlog thử nghiệm nội dung đầu tiên.
- [`../../tools/facebook_monetization_os.py`](../../tools/facebook_monetization_os.py): lệnh tạo daily brief và xác thực dữ liệu.

## Cách chạy an toàn

Từ thư mục gốc của repo:

```bash
python tools/facebook_monetization_os.py validate
python tools/facebook_monetization_os.py daily-brief --date 2026-07-26
python -m unittest discover -s tests -p 'test_*.py'
```

Muốn lưu một daily brief cục bộ để đưa vào Drive/Notion sau khi kết nối chính thức:

```bash
python tools/facebook_monetization_os.py daily-brief --date 2026-07-26 --output runs/daily-brief-2026-07-26.md
```

Thư mục `runs/` bị Git bỏ qua. Không lưu token, cookie, mật khẩu, OTP, giấy tờ thuế hay ảnh căn cước vào repo hoặc output.

## Chu trình mỗi ngày

1. Hermes chạy `validate` và tạo một `daily-brief`.
2. Gemini/Claude/ChatGPT tạo bản nháp theo brief; video phải có demo, giọng nói hoặc khuôn mặt thật của chủ kênh.
3. File gốc được lưu Drive sau khi kết nối chính thức; record nội dung nhận ID, giả thuyết, link file và KPI cần đo.
4. Chỉ khi cổng `official_publishing_connection_verified` được đánh dấu thật, connector API chính thức mới được bật để đăng.
5. Sau 24 giờ và 72 giờ, connector Insights lấy số liệu về Notion; AI chỉ cập nhật playbook khi một nhóm nội dung vượt baseline có ý nghĩa.

## Dữ liệu tối thiểu cho từng bài

| Trường | Lý do |
| --- | --- |
| `content_id` + giả thuyết | Biết chính xác điều gì đang được thử nghiệm |
| Hook, format, CTA, giờ đăng | So sánh được các biến thể |
| Link file Drive + link bài đăng | Truy vết được nguồn và kết quả |
| Reach/plays, watch time, share/save | Đo phân phối và giữ chân |
| Inbox đủ điều kiện, click web | Đo đúng mục tiêu lead |
| Policy/originality check | Tránh đánh đổi monetization lấy video rủi ro |

## Khi nào được đổi khỏi Draft-only

Chỉ sửa `execution_mode` sau khi tất cả điều kiện này có bằng chứng:

1. Kết nối Facebook Publish API chính thức chạy thử thành công trên một asset test.
2. Quyền Insights được xác minh và số liệu được ghi về đúng database Notion.
3. Cơ chế lưu asset Drive, quyền nhạc/hình, và kiểm tra tính nguyên bản đã có checklist.
4. Payout vẫn được xem là quy trình Meta tách biệt; không dùng automation để đổi thông tin thanh toán hoặc né cơ chế xét duyệt.
