# Tài nguyên AWS đang dùng cho Day 21

Ngày cấu hình/kiểm chứng: 07/10/2026.
Account: `972243443873`; user thao tác: `ai-lab-user`, profile `default`.
Region người dùng chọn: **us-east-1**.

## Tài nguyên đã tạo

| Tài nguyên | Giá trị |
|---|---|
| S3 bucket | `income-day21-972243443873-use1` |
| EC2 instance | `i-0c3cb0e2d3bcf7975`, Name `income-api`, `t3.small` |
| Public IP | `100.63.200.231` |
| Public DNS | `ec2-100-63-200-231.compute-1.amazonaws.com` |
| AMI | `ami-062944a84867f2386`, Ubuntu 22.04 x86_64 |
| Root EBS | gp3, 16 GiB, mã hóa, DeleteOnTermination |
| VPC / subnet | `vpc-04804f842d4e76faf` / `subnet-02e82ce306b6f1fb5` |
| Security group | `sg-046a641836fa05b95` |
| EC2 role / instance profile | `income-api-day21-ec2-role` |
| EC2 key pair | `income-day21-deploy` |
| SSH user | `ubuntu` |
| SSH key local | `.local/aws/income-day21.pem` (Git bỏ qua) |
| API service | `income-api`, thư mục `/home/ubuntu/income-app` |

S3 bật toàn bộ Block Public Access, BucketOwnerEnforced (ACL disabled), SSE-S3.
EC2 dùng IMDSv2 required, CPU credits Standard. Security group chỉ mở TCP 22 và 8080
từ **116.96.45.254/32**, là IP internet của máy cấu hình tại thời điểm tạo.

## IAM đã áp dụng

- User `ai-lab-user` vốn nhận quyền EC2/IAM/VPC/ELB từ group `AI-Lab-Group`.
- Sau khi người dùng đồng ý, inline policy `Day21IncomeS3Access` được gắn riêng vào user.
  Nội dung ở `provisioner-s3-policy.json`: tạo/cấu hình đúng bucket này, đọc/ghi object
  dưới `dvc/` và `artifacts/current/`, giới hạn region `us-east-1`.
- EC2 role có inline policy `Day21ReadModel`, chỉ `s3:GetObject` cho
  `artifacts/current/model.joblib`. Trust principal là `ec2.amazonaws.com`.
- `ec2-policy-baseline.json` lưu kết quả phân tích của IAM Policy Autopilot để tham
  khảo. Tệp đã thu hẹp và thực sự gắn vào role là `ec2-read-model-policy.json`.
  Các quyền KMS, Object Lambda, metadata/versioning và liệt kê bucket trong baseline
  không được gắn vào role này.

Không thay đổi các policy đã có của group hoặc tạo access key mới cho user.

## Kiểm chứng AWS ban đầu bằng model local

- DVC remote `labstore` đã trỏ tới `s3://income-day21-972243443873-use1/dvc`.
- `dvc push` thành công cho cả ba datasets. Số mẫu vẫn là 22.361 / 500 / 22.361;
  chưa ghép batch 2.
- Model local có F1 `0.7149321266968326`, accuracy `0.874` được upload vào
  `artifacts/current/model.joblib`; report nằm cạnh model.
- EC2 instance/system status đều `ok`; service `income-api` ở trạng thái `active`.
- API tải model qua instance role, không cần access key đặt trên EC2.
- Kiểm chứng bằng SDK trên EC2: đọc metadata model thành công; truy cập một object DVC
  đang tồn tại bị HTTP 403 như dự kiến.
- Model trên EC2 và local cùng SHA-256:
  `db70dfe156d41efad2539f07a5963da79120493369431a7f1c2a5663c838a712`.

Kết quả gọi API từ máy người dùng:

| Request | Response |
|---|---|
| GET `http://100.63.200.231:8080/healthz` | `{"status":"ok"}` |
| POST /score với `[60,2,5,2,4,0,1,0,0,45]` | `{"prediction":0,"label":"thu_nhap_thap"}` |
| POST /score với `[28,2,14,2,11,0,1,0,0,45]` | `{"prediction":1,"label":"thu_nhap_cao"}` |

Đây là xác nhận cấu hình AWS và serving bằng model local. Chưa dùng lần triển khai này
làm bằng chứng cho GitHub Actions Bước 2 hoặc tự động hóa Bước 3.

## GitHub Actions Bước 2 đã thành công

[Workflow 37653235373](https://github.com/Liber72/K4-L3L4-Track2-Day21-HoangThaiDat-2A202602959-CI-CD-for-AI-Systems/actions/runs/37653235373)
trên commit `6d0fa2d` hoàn thành cả bốn jobs Unit Test, Train, Quality Gate và Release.
Lần chạy dùng `workflow_dispatch`; chưa dùng lần này làm bằng chứng cho trigger commit dữ liệu ở Bước 3.

- Report CI: F1 `0.7149321266968326`, accuracy `0.874`, train 22.361 mẫu, holdout 500 mẫu.
- Model trên EC2 khớp SHA-256 của artifact `candidate-model` trong lần chạy này:
  `0b4678d0fc940bee246dc72325fb937f384e2c8cf3dbe58565ea13ce9ae7a124`.
- Service `income-api` active; gọi từ máy người dùng: `/healthz` trả `ok`,
  `/score` với mẫu `[28,2,14,2,11,0,1,0,0,45]` trả `thu_nhap_cao`.
- Security group sau Release chỉ còn các rule IP máy người dùng trên cổng 22/8080;
  rule SSH tạm của runner đã được thu hồi.

Lần re-run cũ `37651485149` vẫn hiển thị queued và GitHub từ chối cả cancel/force-cancel
với lỗi re-run chưa được đưa vào hàng đợi nội bộ. Kiểm tra và dừng lần cũ này trước khi
triển khai batch 2 để tránh một lần chạy muộn ghi đè model. Dùng link lần thành công
ở trên để chụp `02-actions-buoc-2.png`. Batch 2 chưa được ghép.

## Các giá trị cần nhập vào GitHub

Hướng dẫn tự tạo IAM user CI và Secret `STORAGE_CREDENTIALS`:
[IAM cho GitHub Actions](../../docs/iam-github-actions.md).
User CI `income-day21-ci` đã có cả `Day21IncomeCI` và `Day21IncomeCISSH`.

Repo:
`Liber72/K4-L3L4-Track2-Day21-HoangThaiDat-2A202602959-CI-CD-for-AI-Systems`.

Settings → Secrets and variables → Actions:

| Loại | Tên | Giá trị |
|---|---|---|
| Variable | `AWS_REGION` | `us-east-1` |
| Variable | `EC2_SECURITY_GROUP_ID` | `sg-046a641836fa05b95` |
| Secret | `ARTIFACT_BUCKET` | `income-day21-972243443873-use1` |
| Secret | `SERVER_HOST` | `100.63.200.231` |
| Secret | `SERVER_USER` | `ubuntu` |
| Secret | `SERVER_SSH_KEY` | Nội dung private key trong `.local/aws/income-day21.pem`; không commit hoặc gửi vào chat |
| Secret | `STORAGE_CREDENTIALS` | Credentials JSON của `income-day21-ci`, người dùng đã nhập vào GitHub |

CI đã dùng danh tính riêng `income-day21-ci`; không dùng credentials của `ai-lab-user`.
EC2 vẫn dùng instance role để tải model.

Workflow đã thêm mở tạm SSH cho IP /32 của runner và thu hồi sau Release.
Policy `ci-ssh-policy.json` đã được người dùng gắn vào user CI và variable
`EC2_SECURITY_GROUP_ID` đã được nhập. Nếu runner bị tắt đột ngột hoặc cleanup thất bại,
cần xóa rule của lần chạy theo Description `income-day21-actions-<run-id>-<attempt>`.

## Truy cập và vận hành

PowerShell, từ thư mục gốc repo:

```powershell
& 'C:\Windows\System32\OpenSSH\ssh.exe' -i '.local/aws/income-day21.pem' ubuntu@100.63.200.231
Invoke-RestMethod -Uri 'http://100.63.200.231:8080/healthz'
```

API documentation: http://100.63.200.231:8080/docs.

S3 Console:
https://us-east-1.console.aws.amazon.com/s3/buckets/income-day21-972243443873-use1?region=us-east-1&tab=objects

EC2 Console:
https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#InstanceDetails:instanceId=i-0c3cb0e2d3bcf7975

Nếu IP internet của máy bạn thay đổi, cần cập nhật CIDR của security group.
Nếu EC2 stop/start và public IP thay đổi, cập nhật `SERVER_HOST` và URL API.
SSH host key đã được lưu riêng tại `.local/aws/known_hosts`.

EC2 đang chạy và có thể phát sinh phí compute/EBS/public IPv4 theo tài khoản.
Khi muốn dừng compute, thực hiện trong EC2 Console hoặc:

```powershell
aws ec2 stop-instances --instance-ids i-0c3cb0e2d3bcf7975 --region us-east-1
```

Stop instance vẫn giữ ổ EBS; không tự xóa bucket, role, security group hay SSH key.
Việc dọn/xóa tài nguyên cần được quyết định riêng.
