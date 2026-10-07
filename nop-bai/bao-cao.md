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

**Lý do:** Ba thí nghiệm Gradient Boosting trong MLflow dùng cùng dữ liệu huấn luyện và holdout. Lần 3 có F1 lớp dương cao nhất, đạt ngưỡng 0.65. Lần 1 có accuracy cao nhất nhưng F1 thấp hơn; chọn theo accuracy sẽ dẫn đến bộ tham số khác. Lần 2 giảm đồng thời số cây, learning rate và độ sâu nên chất lượng thấp hơn. Learning rate nhỏ thường cần nhiều cây để bù lại, đổi lấy thời gian huấn luyện; số cây ít có thể chưa học đủ. Các tham số thay đổi cùng lúc nên chưa tách được tác động riêng.

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Lớp thu nhập trên 50K chiếm khoảng 24,8% dữ liệu; holdout có 124 mẫu dương trên 500 mẫu. Mô hình luôn dự đoán thu nhập thấp vẫn đạt accuracy 75,2%, dù bỏ sót toàn bộ lớp dương. F1 lớp dương là trung bình điều hòa của precision và recall, phản ánh cả dự đoán dương sai lẫn bỏ sót người thu nhập cao. Tôi dùng `f1_score` với `average="binary"`, `pos_label=1`. Trung bình weighted chịu ảnh hưởng lớn của lớp đa số; macro tổng hợp cả hai lớp nên không đo trực tiếp chất lượng lớp dương. Quality Gate chỉ cho phép Release khi F1 đạt ít nhất 0.65.

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Release lỗi AccessDenied. | User CI thiếu quyền mở SSH. | Gắn policy SSH vào user CI. |
| Re-run kẹt queued. | GitHub từ chối hủy và xóa. | Tạo workflow v2 với concurrency riêng; run cũ vẫn kẹt. |
| DVC lỗi tương thích. | Phiên bản pathspec không phù hợp. | Cố định pathspec 0.11.2 trong requirements. |
|Bị lỗi action không thể kill run cũ. | GitHub từ chối hủy và xóa. | Tạo workflow v2 với concurrency riêng; run cũ vẫn kẹt. |

## 4. So Sánh Bước 2 và Bước 3

| Giai đoạn | f1_score | accuracy |
|---|---|---|
| Bước 2: 22.361 mẫu | 0.7149 | 0.8740 |
| Bước 3: 44.722 mẫu | 0.7354 | 0.8820 |

**Nhận xét:** Giữ nguyên siêu tham số và holdout, F1 tăng khoảng 0,0205, accuracy tăng 0,008; dữ liệu bổ sung giúp trong lần đánh giá này nhưng không bảo đảm luôn cải thiện chất lượng. Commit `d473ac9` chỉ đổi con trỏ DVC, sau khi dữ liệu đã lên S3, và tự kích hoạt đủ bốn jobs. Model mới được triển khai lên EC2, khớp artifact CI; API trả kết quả hợp lệ.
