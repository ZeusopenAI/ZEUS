
## 9. Luật riêng — bulk-grading

- `judge_model` **phải khác** executor đã làm ra nội dung được chấm. Nếu Executor là Gemini Flash
  thì judge không được là Gemini Flash. Ghi rõ trong `measured_by` / `judge_model`.
- `rubric_version` bắt buộc: đổi rubric mà không đổi version thì điểm cũ và mới không so được.
- `score = 0` là điểm **hợp lệ**, nhưng phải có `measured_by` và `evidence` trỏ tới dòng log có thật.
  Không có bằng chứng ⇒ `checks.py` coi là **0 giả** và fail.
- `score = null` chỉ khi có `reason` (vd: "bài quá ngắn để chấm", "rubric không phủ trường hợp này").
  Không được ghi 0 thay cho "không chấm được" — 0 kéo tụt mọi trung bình phía sau.
- Không chấm lại bài của chính mình trong cùng một phiên. Verifier chạy lại `checks.py` trên output,
  không chấm điểm lần hai bằng cảm tính.
- Phân bố điểm phải được kiểm: nếu 100% record cùng một điểm (vd toàn 85) ⇒ `duplicates` sẽ fail
  vì trùng lặp nội dung; nếu điểm dồn bất thường, ghi vào `reports/` để Human xem.
