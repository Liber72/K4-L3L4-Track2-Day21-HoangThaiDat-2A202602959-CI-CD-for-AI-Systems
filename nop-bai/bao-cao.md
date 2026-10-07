# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Hoàng Thái Đạt |
| MSSV | 2A202602959 |
| Lớp / Khóa | K4 |
| Repo GitHub | [Repo Day 21](https://github.com/Liber72/K4-L3L4-Track2-Day21-HoangThaiDat-2A202602959-CI-CD-for-AI-Systems) |
| Ngày nộp | 07/10/2026 |

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.8780 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.8460 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.8740 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Lần 3 có F1 cao nhất. Lần 1 có accuracy cao nhất nhưng F1 thấp hơn, nên chọn theo accuracy sẽ chọn bộ khác. Lần 2 giảm đồng thời số cây, learning rate và độ sâu, cho chất lượng thấp hơn. Learning rate nhỏ thường cần nhiều cây hơn, đổi lấy thời gian huấn luyện. Các tham số cùng thay đổi; chưa tách được tác động riêng.

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Holdout có 124 mẫu dương trên 500 mẫu (24,8%). Luôn dự đoán thu nhập thấp vẫn đạt accuracy 75,2% nhưng bỏ sót toàn bộ lớp dương. F1 cân bằng precision và recall; tôi dùng `average="binary"`, `pos_label=1` để đo riêng lớp thu nhập cao. Weighted chịu ảnh hưởng lớp đa số; macro tổng hợp hai lớp, không trực tiếp đo lớp dương. Quality Gate yêu cầu F1 ≥ 0.65.

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Release lỗi AccessDenied. | User CI thiếu quyền mở SSH. | Gắn policy SSH vào user CI. |
| DVC lỗi tương thích. | Phiên bản pathspec không phù hợp. | Cố định pathspec 0.11.2 trong requirements. |
| Bị lỗi action không thể kill run cũ. | GitHub từ chối hủy và xóa. | Tạo workflow v2 với concurrency riêng; run cũ vẫn kẹt. |

## 4. So Sánh Bước 2 và Bước 3

| Giai đoạn | f1_score | accuracy |
|---|---|---|
| Bước 2: 22.361 mẫu | 0.7149 | 0.8740 |
| Bước 3: 44.722 mẫu | 0.7354 | 0.8820 |

**Nhận xét:** Cùng siêu tham số và holdout, F1 tăng 0,0205, accuracy tăng 0,008; thêm dữ liệu không bảo đảm luôn cải thiện chất lượng. Commit `d473ac9` chỉ đổi con trỏ DVC, tự chạy bốn jobs và triển khai model lên EC2.

## 5. Phần Bonus Đã Thực Hiện

- [x] Bonus 1 - Tracking MLflow từ xa với DagsHub: Truyền URI và token qua GitHub Secrets.
- [x] Bonus 2 - Điều chỉnh ngưỡng quyết định: Quét 0,1–0,9, chọn F1 cao nhất.
- [x] Bonus 3 - Báo cáo precision / recall tự động: Xuất confusion matrix và báo cáo vào artifact.
- [x] Bonus 4 - Hoàn trả về phiên bản trước: So F1 với report S3 trước Release.
- [x] Bonus 5 - Cảnh báo lệch lạc dữ liệu: Drift: Cảnh báo tỷ lệ dương lệch hơn 5 điểm phần trăm.
