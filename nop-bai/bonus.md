# Cấu hình và bằng chứng bonus

Code của cả 5 bonus đã được bổ sung. Bonus 1 cần tài khoản/Secrets DagsHub;
bonus 4 cần quyền IAM đọc report trước khi chạy pipeline mới.

## 1. DagsHub: bạn tự cấu hình

1. Vào https://dagshub.com, đăng ký/đăng nhập bằng GitHub.
2. Chọn tạo repository và **Connect a repository**, chọn repo GitHub bài lab.
   Nếu giao diện yêu cầu quyền GitHub, cấp quyền cho repo bài này.
3. Trong repo DagsHub, mở **Remote → MLflow**, sao chép tracking URI dạng
   `https://dagshub.com/<DAGSHUB_USERNAME>/<REPO_NAME>.mlflow`.
   Dùng username/repo thực tế trên DagsHub, không mặc định username là `Liber72`.
4. Trong cài đặt tài khoản DagsHub, mở **Access Tokens** và tạo token.
5. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**,
   thêm đủ ba Secrets:

| Secret | Nhập giá trị |
|---|---|
| `MLFLOW_TRACKING_URI` | URI MLflow vừa sao chép |
| `MLFLOW_TRACKING_USERNAME` | Username tài khoản DagsHub |
| `MLFLOW_TRACKING_PASSWORD` | Token DagsHub |

Token chỉ nhập vào GitHub Secrets. Không đưa token vào file, ảnh hoặc chat.
Không cần đổi `STORAGE_CREDENTIALS`: S3 vẫn dùng AWS credentials riêng.

Khi đủ Secrets, job Train gửi metrics/model/report lên DagsHub. Nếu chưa có URI,
workflow dùng SQLite cục bộ; điều này chưa chứng minh Bonus 1 đã hoàn tất.
Server DagsHub tự chọn artifact location, không sử dụng thư mục local của runner.
Nguồn: [Hướng dẫn MLflow của DagsHub](https://dagshub.com/docs/integration_guide/mlflow_tracking/).

## 2. IAM cho Bonus 4: bạn tự cấu hình

Vào **AWS → IAM → Users → income-day21-ci → Permissions → Add permissions →
Create inline policy**. Chọn tab JSON, dán toàn bộ nội dung
[ci-read-report-policy.json](../deploy/aws/ci-read-report-policy.json).
Đặt tên `Day21IncomeCIReadReport` và lưu.

`Day21IncomeCIReadReport` là tên policy mới bạn tự tạo; không tìm tên này trong
**Attach policies directly**. Inline policy tự gắn vào user sau khi tạo.
Nguồn: [AWS: tạo inline policy cho user](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html).

Đây là quyền đọc riêng `artifacts/current/report.json` để so sánh F1 trước Release.
Giữ cả hai policy `Day21IncomeCI` và `Day21IncomeCISSH` hiện có.
Không cần thêm quyền cho EC2 role và không cần tạo access key mới.
Nếu đọc report bị AccessDenied, pipeline sẽ dừng thay vì bỏ qua bảo vệ.

Policy được thu hẹp từ baseline Autopilot, chỉ giữ GetObject cho report này.
Lệnh tái tạo baseline (PowerShell, tại thư mục gốc repo):

```powershell
uvx iam-policy-autopilot@latest generate-policies `
  (Join-Path $PWD 'src/publish_model.py') `
  --region us-east-1 --account 972243443873 --service-hints s3 --pretty
```

Không áp dụng trực tiếp baseline vì nó bao gồm các quyền tùy chọn không dùng trong lab.

## 3. Các bonus đã có trong code

| Bonus | Hành vi và bằng chứng |
|---|---|
| 2: Ngưỡng quyết định | Quét 0.10–0.90, bước 0.05; ghi `threshold_sweep`, `best_threshold`, `best_f1_score`, `f1_score_default` vào report và log MLflow. Ngưỡng nằm trong model joblib; `/score` dùng đúng ngưỡng đã chọn. |
| 3: Precision/recall | `outputs/detail.txt` chứa confusion matrix và precision/recall riêng mỗi lớp; artifact `report` lưu cùng report JSON và drift JSON. |
| 4: Chặn giảm F1 | Release đọc report S3; chỉ deploy nếu F1 mới ≥ F1 cũ. Khi giảm, bỏ qua mở SSH/upload/restart; artifact `release-decision` ghi quyết định. Đây là chặn trước triển khai theo lab, không phải khôi phục sau khi API gặp lỗi. |
| 5: Drift | Kiểm tra trước khi fit; lệch hơn 5 điểm phần trăm so với 24.8% thì in cảnh báo. Report và MLflow ghi tỷ lệ lớp dương. Cảnh báo không tự chặn huấn luyện. |

Ngưỡng Bonus 2 được chọn trên holdout theo yêu cầu lab; F1 tối ưu chưa phải
ước lượng trên một tập test độc lập. `f1_score`/`accuracy` mới ứng với ngưỡng đã chọn;
`f1_score_default` giúp đối chiếu với Bước 2/3 dùng ngưỡng 0.5.

Về chi phí sai lầm: nếu dùng dự đoán để ưu tiên tiếp cận khách hàng thu nhập cao,
bỏ sót lớp dương có thể làm mất cơ hội (recall thấp); gán nhầm lớp dương làm lãng phí
chi phí tiếp cận (precision thấp). Lab chưa quy định chi phí nên không thể kết luận
một loại lỗi luôn tốn kém hơn; F1 cân bằng cả hai.

## 4. Chạy và chụp bằng chứng

Sau khi code đã lên GitHub và hoàn tất hai cấu hình trên, vào **Actions → Income Model
CI/CD v2 → Run workflow → main**. Không chạy lại `append_batch.py`.

- `06-dagshub-mlflow.png`: DagsHub MLflow thấy run, metrics, threshold và URL.
- `07-bonus-threshold-report.png`: log Train hoặc report hiển thị ngưỡng tốt nhất,
  F1 ngưỡng 0.5 và F1 tối ưu.
- `08-bonus-detail.png`: artifact `report`, file `detail.txt` có confusion matrix
  và precision/recall cả hai lớp.
- `09-bonus-regression-guard.png`: log bước Compare candidate F1 và artifact
  `release-decision` thấy F1 mới/cũ cùng quyết định ALLOW/BLOCK.
- `10-bonus-drift.png`: log bước kiểm tra phân phối thấy tỷ lệ thực tế và tham chiếu.

Để kiểm chứng nhánh cảnh báo drift và chặn regression mà không thay dữ liệu/model
đang chạy, chạy bộ test có các trường hợp lệch >5 điểm và model giảm F1:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_bonus.py -v
```

Ảnh lưu trong `nop-bai/anh-chup-man-hinh/`, dưới 1 MB/ảnh, hiện URL nếu từ trình duyệt.
Chỉ đánh dấu Bonus 1/4 hoàn tất sau khi cấu hình và có log chạy thật xác nhận.

## 5. Kết quả local đã kiểm chứng

Huấn luyện bonus dùng đủ 44.722 mẫu và giữ nguyên holdout 500 mẫu cùng siêu tham số.

| Kết quả | Giá trị |
|---|---|
| Ngưỡng tốt nhất trong 17 ngưỡng | 0.30 |
| F1 tại ngưỡng 0.50 | 0.7354260090 |
| F1 tại ngưỡng 0.30 | 0.7537313433 |
| Accuracy tại ngưỡng 0.30 | 0.868 |
| Tỷ lệ lớp dương | 0.2478422253 (24.78%) |
| Drift | Không; lệch khoảng 0.0158 điểm phần trăm |
| Confusion matrix (hàng thực tế, cột dự đoán) | `[[333,43],[23,101]]` |
| Precision / recall lớp thu nhập cao | 0.7014 / 0.8145 |

Model joblib đã tải được qua API local và dùng đúng ngưỡng 0.30. Bộ test có
**50 tests đạt**, gồm cả cảnh báo drift và chặn giảm F1, lỗi AccessDenied,
đóng S3 streaming body, kiểm tra artifact location của remote tracking.

Kiểm chứng chỉ đọc report S3 bằng AWS credentials local: candidate F1 0.753731
so với current 0.735426 được ALLOW; mô phỏng candidate F1 0.700000 bị BLOCK.
Không upload model hoặc restart EC2 trong lần kiểm chứng này. Đây chưa phải bằng
chứng user CI có quyền mới hoặc Bonus 1 tracking DagsHub đã hoạt động.

Model/report/detail local nằm trong `.local/bonus/`; không commit model vào Git.
