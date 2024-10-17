import React, { useState, useEffect } from 'react';

function ChatRoom({ token }) {  // Loại bỏ roomId ở đây
    const [messages, setMessages] = useState([]);
    const [message, setMessage] = useState("");
    const [ws, setWs] = useState(null);
    const [roomId, setRoomId] = useState("");  // Tạo state mới để lưu roomId từ backend

    useEffect(() => {
        // Kết nối WebSocket với token để xác thực
        const websocket = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
        setWs(websocket);

        websocket.onopen = () => {
            console.log("WebSocket connected");
        };

        websocket.onmessage = (event) => {
            const newMessage = JSON.parse(event.data);

            // Nếu backend gửi roomId khi kết nối thành công
            if (newMessage.roomId) {
                setRoomId(newMessage.roomId);  // Cập nhật roomId từ backend
            } else {
                // Thêm tin nhắn vào danh sách
                setMessages((prevMessages) => [...prevMessages, newMessage]);
            }
        };

        websocket.onclose = () => {
            console.log("WebSocket disconnected");
        };

        return () => websocket.close();
    }, [token]);

    const sendMessage = () => {
        if (ws && message.trim() !== "") {
            const messageData = JSON.stringify({
                message,
                timestamp: new Date().toISOString()
            });
            ws.send(messageData);
            setMessage("");
        }
    };

    return (
        <div>
            <h2>Room: {roomId || "Connecting..."}</h2>  {/* Hiển thị roomId nếu đã nhận được */}
            <div style={{ border: "1px solid #ccc", padding: "10px", height: "300px", overflowY: "scroll" }}>
                {messages.map((msg, index) => (
                    <p key={index}>
                        <strong>{msg.sender}</strong>: {msg.message}
                    </p>
                ))}
            </div>
            <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Enter your message"
                style={{ width: "80%" }}
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
}

export default ChatRoom;
