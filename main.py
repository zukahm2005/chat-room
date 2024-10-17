from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from pydantic import BaseModel
import sqlite3
import os
import json
import datetime
from firebase_admin import credentials, firestore, initialize_app
from typing import Dict, List

# Tải các biến từ file .env
load_dotenv()

# Cấu hình Firebase từ file .env
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL').replace('@', '%40')}"
})

# Khởi tạo Firebase và Firestore
initialize_app(cred)
db = firestore.client()

# Khởi tạo FastAPI
app = FastAPI()

# Cấu hình CORS để cho phép frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Cho phép React frontend trên localhost:3000 truy cập
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả các phương thức (GET, POST, PUT, DELETE, v.v.)
    allow_headers=["*"],  # Cho phép tất cả các header
)

# Các cài đặt OAuth2 và JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mô phỏng lưu người dùng (sử dụng cơ sở dữ liệu thật trong thực tế)
users_db = {}

# Khởi tạo SQLite
conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, room TEXT, sender TEXT, message TEXT, timestamp TEXT)")

# Quản lý các phòng chat
rooms: Dict[str, List[WebSocket]] = {}

# Định nghĩa Model cho đăng ký người dùng
class UserCreate(BaseModel):
    username: str
    password: str

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# API Đăng ký
@app.post("/register")
async def register(user: UserCreate):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="User already registered")
    
    # Lưu người dùng vào bộ nhớ tạm `users_db` (bạn có thể bỏ dòng này nếu không cần)
    users_db[user.username] = get_password_hash(user.password)
    
    # Lưu người dùng vào Firestore
    try:
        db.collection("users").document(user.username).set({
            "username": user.username,
            "password_hash": get_password_hash(user.password)  # Lưu mật khẩu đã băm
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save user to Firestore: {e}")
    
    return {"msg": "User registered successfully"}

# API Đăng nhập (trả về JWT token)
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Lấy thông tin người dùng từ Firestore
        user_doc = db.collection("users").document(form_data.username).get()
        
        # Kiểm tra nếu người dùng không tồn tại
        if not user_doc.exists:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Lấy `password_hash` từ dữ liệu người dùng trong Firestore
        user_data = user_doc.to_dict()
        user_password_hash = user_data["password_hash"]

        # Xác thực mật khẩu
        if not verify_password(form_data.password, user_password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Tạo và trả về access token
        access_token = create_access_token(data={"sub": form_data.username})
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to authenticate: {str(e)}")

# WebSocket chat room
# WebSocket chat room
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Xác thực token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Tìm phòng phù hợp cho người dùng
    room_id = None
    for room, users in rooms.items():
        if len(users) < 2:
            room_id = room
            break
    if not room_id:
        room_id = f"room{len(rooms) + 1}"  # Tạo phòng mới nếu không có phòng trống
        rooms[room_id] = []

    rooms[room_id].append(websocket)
    await websocket.accept()

    # Gửi roomId về frontend
    await websocket.send_text(json.dumps({"roomId": room_id}))

    # Lấy lịch sử tin nhắn từ SQLite
    cursor.execute("SELECT sender, message, timestamp FROM messages WHERE room = ?", (room_id,))
    previous_messages = cursor.fetchall()
    for sender, message, timestamp in previous_messages:
        await websocket.send_text(json.dumps({"sender": sender, "message": message, "timestamp": timestamp}))

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message = message_data["message"]
            timestamp = message_data["timestamp"]

            # Lưu vào SQLite và Firestore
            cursor.execute("INSERT INTO messages (room, sender, message, timestamp) VALUES (?, ?, ?, ?)", (room_id, username, message, timestamp))
            conn.commit()
            db.collection("messages").document(room_id).collection("chats").add({
                "sender": username,
                "message": message,
                "timestamp": timestamp
            })

            # Gửi tin nhắn cho các người dùng trong cùng phòng
            for user in rooms[room_id]:
                await user.send_text(json.dumps({"sender": username, "message": message, "timestamp": timestamp}))

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Xóa kết nối khi client ngắt
        rooms[room_id].remove(websocket)
        if not rooms[room_id]:  # Xóa phòng nếu không còn ai
            del rooms[room_id]
