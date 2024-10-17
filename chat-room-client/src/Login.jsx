// src/Login.js
import React, { useState } from 'react';
import axios from 'axios';

function Login({ setToken }) {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [isLogin, setIsLogin] = useState(true);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (isLogin) {
                const response = await axios.post("http://localhost:8000/token", new URLSearchParams({
                    username,
                    password
                }), { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
                setToken(response.data.access_token);
            } else {
                await axios.post("http://localhost:8000/register", { username, password });
                alert("User registered successfully! Please log in.");
                setIsLogin(true);
            }
        } catch (error) {
            console.error("Error:", error);
            alert("Error during login/register.");
        }
    };

    return (
        <div>
            <h2>{isLogin ? "Login" : "Register"}</h2>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                />
                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
                <button type="submit">{isLogin ? "Login" : "Register"}</button>
            </form>
            <button onClick={() => setIsLogin(!isLogin)}>
                {isLogin ? "Switch to Register" : "Switch to Login"}
            </button>
        </div>
    );
}

export default Login;
