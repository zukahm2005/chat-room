// src/App.js
import React, { useState } from 'react';
import Login from './Login';
import ChatRoom from './ChatRoom';

function App() {
    const [token, setToken] = useState(null);
    const roomId = "room1"; // Đặt ID phòng cố định, bạn có thể tùy chỉnh nếu cần

    return (
        <div>
            <h1>Welcome to the Chat Room</h1>
            {token ? (
                <ChatRoom roomId={roomId} token={token} />
            ) : (
                <Login setToken={setToken} />
            )}
        </div>
    );
}

export default App;
