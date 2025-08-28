## Technologies

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **PostgreSQL** - Database
- **Poetry** - Dependency management

## Team

- **Toàn Từ**
- **Khải Trần**
- **Khang Bùi** 
- **Khoa Lý**

Microservice quản lý lịch khám cho hệ thống bệnh viện.

## Tổng quan

Microservice này cung cấp API cho 4 use case chính:

1. **Đặt lịch khám** - Bệnh nhân đặt lịch khám với bác sĩ
2. **Xác nhận lịch khám** - Bác sĩ xác nhận hoặc từ chối lịch khám
3. **Cập nhật lịch khám** - Thay đổi thông tin lịch khám đã đặt
4. **Hủy lịch khám** - Hủy lịch khám đã đặt

## Kiến trúc

```
src/
├── controllers/        # API Controllers (Endpoints)
├── services/          # Business Logic Layer  
├── repositories/      # Data Access Layer
├── models/           # SQLAlchemy Models
├── dto/              # Request/Response DTOs
└── main.py           # Application Entry Point

config/               # Database & Settings Configuration
resources/            # SQL Scripts & Database Setup
tests/               # HTTP Test Files
```

## Cơ sở dữ liệu

Sử dụng PostgreSQL với schema `appointment_mgmt`:

- `departments` - Danh sách khoa khám
- `doctors` - Thông tin bác sĩ
- `doctor_available_slots` - Lịch trống của bác sĩ
- `patients` - Thông tin bệnh nhân
- `appointments` - Lịch khám chính

## Setup

### Yêu cầu
- Python >= 3.11, < 4.0
- PostgreSQL
- Docker & Docker Compose (optional)

### Cài đặt

1. **Install poetry**
```bash
python -m pip install poetry==2.1.3
```

2. **Install dependencies**
```bash 
poetry install
```

3. **Thiết lập cơ sở dữ liệu**

Tạo file `.env`:
```env
# Database Configuration
DATABASE__URL=postgresql://postgres:postgres@localhost:5432/postgres
DATABASE__POOL_SIZE=10
DATABASE__MAX_OVERFLOW=20
DATABASE__ECHO=true

# App Configuration  
APP__DEBUG=true
APP__HOST=127.0.0.1
APP__PORT=8005
```
4. **Start server**
```bash
poetry run task start

## API Endpoints

### Supporting Endpoints
- `GET /appointments/departments` - Lấy danh sách khoa
- `GET /appointments/departments/{id}/doctors` - Lấy bác sĩ theo khoa
- `GET /appointments/available-slots` - Lấy lịch trống

### Use Case 1: Đặt lịch khám
- `POST /appointments/` - Đặt lịch khám (patient_id từ microservice khác)

### Use Case 2: Xác nhận lịch khám
- `GET /appointments/doctor/{id}/pending` - Lấy lịch chờ xác nhận
- `PUT /appointments/{id}/confirm` - Xác nhận/từ chối lịch

### Use Case 3: Cập nhật lịch khám
- `PUT /appointments/{id}` - Cập nhật lịch khám

### Use Case 4: Hủy lịch khám
- `DELETE /appointments/{id}/cancel` - Hủy lịch khám

### Query Endpoints
- `GET /appointments/` - Lấy danh sách lịch khám (có phân trang)
- `GET /appointments/{id}` - Chi tiết lịch khám
- `GET /appointments/patient/{id}` - Lịch khám của bệnh nhân

## Testing

Sử dụng file `tests/test_appointment.http` để test các API endpoints.

### Flow Testing

**Lưu ý**: Bệnh nhân phải được tạo trước ở Patient Management microservice.

1. **Xem danh sách khoa**
```http
GET /appointments/departments
```

2. **Xem bác sĩ trong khoa**
```http  
GET /appointments/departments/1/doctors
```

3. **Xem lịch trống**
```http
GET /appointments/available-slots?doctor_id=1
```

4. **Đặt lịch khám** (với patient_id đã tồn tại)
```http
POST /appointments/
{
  "patient_id": 1,
  "doctor_id": 1,
  "department_id": 1, 
  "slot_id": 1,
  "reason": "Khám tổng quát"
}
```
### Key Features

- **Triggers tự động** book/release slots khi tạo/hủy lịch
- **Views** tối ưu cho các use case
- **Constraints** đảm bảo tính toàn vẹn dữ liệu
- **Indexes** cho performance

## Tích hợp với Microservices khác

### Patient Management Microservice
- **Dependency**: Microservice này cần Patient Management để validate patient_id
- **Integration**: Patients phải được tạo trước ở Patient Management microservice
- **Validation**: API sẽ kiểm tra patient_id tồn tại trước khi tạo appointment

### Notification Microservice
- **Integration Point**: Sau khi confirm/cancel appointment
- **Events**: Có thể publish events để notification service gửi thông báo

### Doctor Management Microservice
- **Future Enhancement**: Doctors có thể được quản lý ở microservice riêng
- **Current**: Doctors được quản lý trong appointment service