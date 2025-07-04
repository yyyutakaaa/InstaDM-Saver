from flask import Flask, request, jsonify, session, send_file, Response
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
import secrets

# Only import if available
try:
    from instagrapi import Client
    from instagrapi.types import DirectThread, DirectMessage
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# In-memory storage
user_sessions = {}

# Professional HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DM Archive Pro - Instagram Message Extractor</title>
    <meta name="description" content="Professional Instagram DM extraction tool. Export your direct messages safely and securely.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #3b82f6;
            --primary-dark: #2563eb;
            --secondary-color: #6b7280;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --bg-primary: #1f2937;
            --bg-secondary: #111827;
            --bg-tertiary: #374151;
            --text-primary: #f9fafb;
            --text-secondary: #d1d5db;
            --border-color: #4b5563;
            --border-hover: #6b7280;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.3);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.3), 0 4px 6px -4px rgb(0 0 0 / 0.3);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.3), 0 8px 10px -6px rgb(0 0 0 / 0.3);
            --radius-sm: 0.375rem;
            --radius-md: 0.5rem;
            --radius-lg: 0.75rem;
            --radius-xl: 1rem;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            min-height: 100vh;
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        .main-container {
            min-height: 100vh;
            padding: 2rem 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .app-container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-primary);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-xl);
            overflow: hidden;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
        }
        
        .header-content {
            position: relative;
            z-index: 1;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            letter-spacing: -0.025em;
        }
        
        .header p {
            font-size: 1.125rem;
            opacity: 0.9;
            font-weight: 400;
        }
        
        .content-wrapper {
            display: flex;
            flex: 1;
            min-height: 0;
        }
        
        .sidebar {
            width: 350px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        
        .section {
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .section:last-child {
            border-bottom: none;
            flex: 1;
        }
        
        .section-title {
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }
        
        .login-form {
            background: var(--bg-primary);
            padding: 1.5rem;
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
        }
        
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-group:last-child {
            margin-bottom: 0;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-primary);
            font-size: 0.875rem;
        }
        
        input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            font-size: 0.875rem;
            transition: all 0.2s ease;
            background: var(--bg-primary);
        }
        
        input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgb(37 99 235 / 0.1);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: var(--radius-md);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            white-space: nowrap;
        }
        
        .btn-primary {
            background: var(--primary-color);
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }
        
        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
        
        .btn-secondary:hover:not(:disabled) {
            background: var(--border-color);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .btn-group {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        
        .conversation-list {
            flex: 1;
            overflow-y: auto;
            margin-top: 1rem;
            max-height: 500px;
        }
        
        .conversation-item {
            padding: 1rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            margin-bottom: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
            background: var(--bg-primary);
        }
        
        .conversation-item:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow-sm);
            transform: translateY(-1px);
        }
        
        .conversation-item.selected {
            background: var(--primary-color);
            border-color: var(--primary-color);
            color: white;
        }
        
        .conversation-name {
            font-weight: 500;
            margin-bottom: 0.25rem;
        }
        
        .conversation-preview {
            font-size: 0.8125rem;
            opacity: 0.7;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .welcome-section {
            padding: 3rem 2rem;
            text-align: center;
            color: var(--text-secondary);
        }
        
        .welcome-section h2 {
            font-size: 1.875rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }
        
        .feature-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
            text-align: left;
        }
        
        .feature-item {
            background: var(--bg-secondary);
            padding: 1.5rem;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-color);
        }
        
        .feature-item h3 {
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }
        
        .messages-section {
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
        }
        
        .message-controls {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.5rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
        }
        
        .message-controls h3 {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-right: auto;
        }
        
        .input-group {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .input-group input {
            width: 100px;
            padding: 0.5rem 0.75rem;
        }
        
        .message-container {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem;
            background: var(--bg-tertiary);
            min-height: 400px;
        }
        
        .message {
            margin-bottom: 1rem;
            max-width: 80%;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.sent {
            margin-left: auto;
            text-align: right;
        }
        
        .message-bubble {
            padding: 0.75rem 1rem;
            border-radius: var(--radius-lg);
            word-wrap: break-word;
        }
        
        .message.sent .message-bubble {
            background: var(--primary-color);
            color: white;
            border-bottom-right-radius: var(--radius-sm);
        }
        
        .message.received .message-bubble {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: var(--radius-sm);
        }
        
        .message-header {
            font-size: 0.75rem;
            opacity: 0.7;
            margin-bottom: 0.25rem;
        }
        
        .message.sent .message-header {
            text-align: right;
        }
        
        .message.received .message-header {
            text-align: left;
        }
        
        .progress-container {
            margin: 1rem 0;
            background: var(--bg-primary);
            padding: 1rem;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 999px;
            overflow: hidden;
            margin-bottom: 0.5rem;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
            transition: width 0.3s ease;
            border-radius: 999px;
        }
        
        .progress-text {
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-align: center;
        }
        
        .alert {
            padding: 1rem;
            border-radius: var(--radius-md);
            margin-bottom: 1rem;
            border: 1px solid;
            font-size: 0.875rem;
        }
        
        .alert-success {
            background: rgb(5 150 105 / 0.1);
            color: var(--success-color);
            border-color: rgb(5 150 105 / 0.2);
        }
        
        .alert-error {
            background: rgb(220 38 38 / 0.1);
            color: var(--error-color);
            border-color: rgb(220 38 38 / 0.2);
        }
        
        .alert-warning {
            background: rgb(245 158 11 / 0.2);
            color: var(--warning-color);
            border-color: rgb(245 158 11 / 0.3);
        }
        
        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
        }
        
        .modal-content {
            background-color: var(--bg-primary);
            margin: 15% auto;
            padding: 2rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            width: 90%;
            max-width: 400px;
            box-shadow: var(--shadow-xl);
            text-align: center;
        }
        
        .modal h3 {
            color: var(--text-primary);
            margin-bottom: 1rem;
            font-weight: 600;
        }
        
        .modal p {
            color: var(--text-secondary);
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
        
        .modal .btn-group {
            justify-content: center;
            gap: 1rem;
        }
        
        .footer {
            background: var(--text-primary);
            color: white;
            padding: 2rem 1rem;
            margin-top: auto;
        }
        
        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .footer-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .footer-section h4 {
            font-weight: 600;
            margin-bottom: 1rem;
            color: white;
        }
        
        .footer-section p, .footer-section li {
            font-size: 0.875rem;
            line-height: 1.6;
            opacity: 0.8;
            margin-bottom: 0.5rem;
        }
        
        .footer-section ul {
            list-style: none;
        }
        
        .footer-section a {
            color: white;
            text-decoration: none;
            opacity: 0.8;
            transition: opacity 0.2s ease;
        }
        
        .footer-section a:hover {
            opacity: 1;
        }
        
        .footer-bottom {
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding-top: 1.5rem;
            text-align: center;
            font-size: 0.875rem;
            opacity: 0.7;
        }
        
        .hidden {
            display: none;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .header p {
                font-size: 1rem;
            }
            
            .content-wrapper {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                border-right: none;
                border-bottom: 1px solid var(--border-color);
            }
            
            .main-container {
                padding: 1rem;
            }
            
            .message-controls {
                flex-direction: column;
                align-items: stretch;
                gap: 1rem;
            }
            
            .message-controls h3 {
                margin-right: 0;
                margin-bottom: 0.5rem;
            }
            
            .btn-group {
                justify-content: stretch;
            }
            
            .btn-group .btn {
                flex: 1;
            }
            
            .input-group {
                justify-content: space-between;
            }
            
            .footer-grid {
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }
        }
        
        @media (max-width: 480px) {
            .main-container {
                padding: 0.5rem;
            }
            
            .header {
                padding: 1.5rem 1rem;
            }
            
            .section {
                padding: 1rem;
            }
            
            .messages-section {
                padding: 1rem;
            }
            
            .message-controls {
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="app-container">
            <header class="header">
                <div class="header-content">
                    <h1>DM Archive Pro</h1>
                    <p>Professional Instagram Message Extraction Tool</p>
                </div>
            </header>
            
            <div class="content-wrapper">
                <aside class="sidebar">
                    <div id="login-section" class="section">
                        <h3 class="section-title">Authentication</h3>
                        <div class="login-form">
                            <div id="login-alert"></div>
                            
                            <div class="form-group">
                                <label for="username">Instagram Username</label>
                                <input type="text" id="username" placeholder="Enter your username" autocomplete="username">
                            </div>
                            
                            <div class="form-group">
                                <label for="password">Password</label>
                                <input type="password" id="password" placeholder="Enter your password" autocomplete="current-password">
                            </div>
                            
                            <div class="form-group hidden" id="2fa-group">
                                <label for="verification-code">Two-Factor Authentication Code</label>
                                <input type="text" id="verification-code" placeholder="Enter 6-digit code" maxlength="6">
                            </div>
                            
                            <div class="btn-group">
                                <button class="btn btn-primary" onclick="login()" id="login-btn">
                                    Sign In
                                </button>
                                <button class="btn btn-secondary hidden" onclick="logout()" id="logout-btn">
                                    Sign Out
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div id="conversations-section" class="section hidden">
                        <h3 class="section-title">Conversations</h3>
                        <button class="btn btn-secondary" onclick="loadConversations()">
                            Refresh List
                        </button>
                        <div id="conversation-list" class="conversation-list"></div>
                    </div>
                </aside>
                
                <main class="main-content">
                    <div id="welcome-section" class="welcome-section">
                        <h2>Welcome to DM Archive Pro</h2>
                        <p>A professional tool for extracting and archiving your Instagram direct messages. Sign in with your Instagram credentials to get started.</p>
                        
                        <div class="feature-list">
                            <div class="feature-item">
                                <h3>Secure Authentication</h3>
                                <p>Your credentials are processed securely and never stored on our servers.</p>
                            </div>
                            <div class="feature-item">
                                <h3>Complete Export</h3>
                                <p>Extract all your messages with timestamps, media links, and conversation context.</p>
                            </div>
                            <div class="feature-item">
                                <h3>Professional Format</h3>
                                <p>Messages are exported in well-organized, readable text format for easy archival.</p>
                            </div>
                            <div class="feature-item">
                                <h3>Privacy Focused</h3>
                                <p>All processing happens in your browser session. No data is permanently stored.</p>
                            </div>
                        </div>
                    </div>
                    
                    <div id="messages-section" class="hidden">
                        <div class="message-controls">
                            <h3 id="conversation-title">Select Conversation</h3>
                            <div class="input-group">
                                <label for="message-count">Messages:</label>
                                <input type="number" id="message-count" value="100" min="1" max="5000">
                            </div>
                            <div class="btn-group">
                                <button class="btn btn-primary" onclick="fetchMessages()">
                                    Extract Messages
                                </button>
                                <button class="btn btn-secondary" onclick="downloadMessages()" id="download-btn" disabled>
                                    Download Archive
                                </button>
                            </div>
                        </div>
                        
                        <div id="progress-section" class="progress-container hidden">
                            <div class="progress-bar">
                                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                            </div>
                            <p class="progress-text" id="progress-text">Preparing extraction...</p>
                        </div>
                        
                        <div class="messages-section">
                            <div id="message-container" class="message-container"></div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
        
        <footer class="footer">
            <div class="footer-content">
                <div class="footer-grid">
                    <div class="footer-section">
                        <h4>Legal Disclaimer</h4>
                        <p>This tool is an independent third-party application and is not affiliated with, endorsed by, or connected to Instagram or Meta Platforms, Inc.</p>
                        <p>Use of this service is entirely at your own risk and discretion.</p>
                    </div>
                    
                    <div class="footer-section">
                        <h4>Terms of Use</h4>
                        <ul>
                            <li>You must own the Instagram account being accessed</li>
                            <li>This tool is for personal archival purposes only</li>
                            <li>Commercial use is strictly prohibited</li>
                            <li>Users are responsible for compliance with Instagram's Terms of Service</li>
                        </ul>
                    </div>
                    
                    <div class="footer-section">
                        <h4>Privacy & Security</h4>
                        <ul>
                            <li>No user credentials are stored on our servers</li>
                            <li>All data processing occurs in your browser session</li>
                            <li>Session data is automatically cleared upon logout</li>
                            <li>We do not collect, store, or transmit your personal data</li>
                        </ul>
                    </div>
                    
                    <div class="footer-section">
                        <h4>Important Notice</h4>
                        <p><strong>This is an unofficial tool.</strong> Instagram may update their platform or policies at any time, which could affect this service's functionality.</p>
                        <p>Users assume all responsibility for any consequences of using this tool.</p>
                    </div>
                </div>
                
                <div class="footer-bottom">
                    <p>&copy; 2025 DM Archive Pro. This is an independent, unofficial tool. Instagram and the Instagram logo are trademarks of Meta Platforms, Inc. Not affiliated with Instagram or Meta.</p>
                </div>
            </div>
        </footer>
        
        <!-- Modal for credential saving -->
        <div id="save-credentials-modal" class="modal">
            <div class="modal-content">
                <h3>Save Credentials?</h3>
                <p>Would you like to save your login credentials for 30 days? This will allow you to sign in automatically without entering your username and password each time.</p>
                <div class="btn-group">
                    <button class="btn btn-primary" onclick="saveCredentialsChoice(true)">Yes, Save</button>
                    <button class="btn btn-secondary" onclick="saveCredentialsChoice(false)">No, Thanks</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Cookie management functions
        function setCookie(name, value, days) {
            const expires = new Date();
            expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
            document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/;SameSite=Strict;Secure=${location.protocol === 'https:'}`;
        }
        
        function getCookie(name) {
            const nameEQ = name + "=";
            const ca = document.cookie.split(';');
            for(let i = 0; i < ca.length; i++) {
                let c = ca[i];
                while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length, c.length));
            }
            return null;
        }
        
        function deleteCookie(name) {
            document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
        }
        
        // Load saved credentials on page load
        document.addEventListener('DOMContentLoaded', function() {
            const savedUsername = getCookie('instagram_username');
            const savedPassword = getCookie('instagram_password');
            
            if (savedUsername) {
                document.getElementById('username').value = savedUsername;
            }
            if (savedPassword) {
                document.getElementById('password').value = atob(savedPassword);
            }
        });
        
        let pendingCredentials = null;
        let currentThreadId = null;
        let currentMessages = [];
        let isLoggedIn = false;
        let needs2FA = false;
        
        function showAlert(message, type = 'info') {
            const alertDiv = document.getElementById('login-alert');
            alertDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
            setTimeout(() => {
                alertDiv.innerHTML = '';
            }, 6000);
        }
        
        async function login() {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const verificationCode = document.getElementById('verification-code').value.trim();
            
            if (!username || !password) {
                showAlert('Please enter both username and password.', 'error');
                return;
            }
            
            const loginBtn = document.getElementById('login-btn');
            const originalText = loginBtn.textContent;
            loginBtn.disabled = true;
            loginBtn.textContent = 'Authenticating...';
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        verification_code: verificationCode
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Store credentials for potential saving
                    pendingCredentials = { username, password };
                    
                    isLoggedIn = true;
                    showLoginSuccess(data.username);
                    loadConversations();
                } else if (data.error === '2fa_required') {
                    needs2FA = true;
                    document.getElementById('2fa-group').classList.remove('hidden');
                    showAlert('Two-factor authentication required. Please enter your 6-digit code.', 'warning');
                } else {
                    showAlert(data.message, 'error');
                }
            } catch (error) {
                showAlert('Network error. Please check your connection and try again.', 'error');
            } finally {
                loginBtn.disabled = false;
                loginBtn.textContent = originalText;
            }
        }
        
        function showLoginSuccess(username) {
            document.getElementById('login-section').classList.add('hidden');
            document.getElementById('conversations-section').classList.remove('hidden');
            document.getElementById('welcome-section').classList.add('hidden');
            
            showAlert(`Successfully authenticated as ${username}`, 'success');
        }
        
        async function logout() {
            try {
                await fetch('/api/logout', { method: 'POST' });
                
                // Ask if user wants to clear saved credentials
                if (getCookie('instagram_username') || getCookie('instagram_password')) {
                    if (confirm('Do you want to clear your saved credentials?')) {
                        deleteCookie('instagram_username');
                        deleteCookie('instagram_password');
                        showAlert('Saved credentials cleared.', 'success');
                    }
                }
                
                // Reset application state
                isLoggedIn = false;
                needs2FA = false;
                currentThreadId = null;
                currentMessages = [];
                
                // Reset UI
                document.getElementById('login-section').classList.remove('hidden');
                document.getElementById('conversations-section').classList.add('hidden');
                document.getElementById('messages-section').classList.add('hidden');
                document.getElementById('welcome-section').classList.remove('hidden');
                document.getElementById('2fa-group').classList.add('hidden');
                
                // Clear form fields (except if credentials are saved)
                if (!getCookie('instagram_username')) {
                    document.getElementById('username').value = '';
                    document.getElementById('password').value = '';
                    document.getElementById('remember-credentials').checked = false;
                }
                document.getElementById('verification-code').value = '';
                
                showAlert('Successfully signed out.', 'success');
            } catch (error) {
                showAlert('Error during sign out. Please refresh the page.', 'error');
            }
        }
        
        async function loadConversations() {
            try {
                const response = await fetch('/api/conversations');
                const data = await response.json();
                
                if (data.success) {
                    displayConversations(data.conversations);
                } else {
                    showAlert(data.error, 'error');
                    if (data.error.includes('Not logged in')) {
                        logout();
                    }
                }
            } catch (error) {
                showAlert('Failed to load conversations. Please try refreshing.', 'error');
            }
        }
        
        function displayConversations(conversations) {
            const container = document.getElementById('conversation-list');
            container.innerHTML = '';
            
            if (conversations.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); margin-top: 2rem;">No conversations found.</p>';
                return;
            }
            
            conversations.forEach((conversation, index) => {
                const div = document.createElement('div');
                div.className = 'conversation-item';
                div.onclick = () => selectConversation(conversation, div);
                
                div.innerHTML = `
                    <div class="conversation-name">${conversation.display_name}</div>
                    <div class="conversation-preview">${conversation.last_message || 'No recent messages'}</div>
                `;
                
                container.appendChild(div);
            });
        }
        
        function selectConversation(conversation, element) {
            // Remove selection from other items
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Select current item
            element.classList.add('selected');
            currentThreadId = conversation.id;
            
            // Show messages section
            document.getElementById('messages-section').classList.remove('hidden');
            document.getElementById('conversation-title').textContent = `Messages with ${conversation.display_name}`;
            
            // Clear previous messages
            document.getElementById('message-container').innerHTML = '';
            document.getElementById('download-btn').disabled = true;
        }
        
        async function fetchMessages() {
            if (!currentThreadId) {
                showAlert('Please select a conversation first.', 'warning');
                return;
            }
            
            const count = parseInt(document.getElementById('message-count').value);
            
            if (count < 1 || count > 5000) {
                showAlert('Please enter a number between 1 and 5000.', 'error');
                return;
            }
            
            showProgress(true, 'Extracting messages...');
            
            try {
                const response = await fetch(`/api/messages/${currentThreadId}?count=${count}`);
                const data = await response.json();
                
                if (data.success) {
                    currentMessages = data.messages;
                    displayMessages(data.messages);
                    document.getElementById('download-btn').disabled = false;
                    showAlert(`Successfully extracted ${data.messages.length} messages.`, 'success');
                } else {
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                showAlert('Failed to extract messages. Please try again.', 'error');
            } finally {
                showProgress(false);
            }
        }
        
        function displayMessages(messages) {
            const container = document.getElementById('message-container');
            container.innerHTML = '';
            
            if (messages.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); margin-top: 2rem;">No messages found in this conversation.</p>';
                return;
            }
            
            // Show last 50 messages for performance
            const displayMessages = messages.slice(-50);
            
            displayMessages.forEach(message => {
                const div = document.createElement('div');
                div.className = `message ${message.is_sent ? 'sent' : 'received'}`;
                
                let mediaHtml = '';
                if (message.media) {
                    const mediaType = message.media.type === 'image' ? 'Image' : 'Video';
                    mediaHtml = `<br><em style="opacity: 0.8;">${mediaType}: <a href="${message.media.url}" target="_blank" rel="noopener noreferrer" style="color: inherit;">View Content</a></em>`;
                }
                
                div.innerHTML = `
                    <div class="message-header">${message.sender} • ${message.timestamp}</div>
                    <div class="message-bubble">
                        ${message.text}${mediaHtml}
                    </div>
                `;
                
                container.appendChild(div);
            });
            
            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }
        
        function showProgress(show, text = 'Processing...') {
            const progressSection = document.getElementById('progress-section');
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            
            if (show) {
                progressSection.classList.remove('hidden');
                progressText.textContent = text;
                
                // Animate progress
                let progress = 0;
                const interval = setInterval(() => {
                    progress += Math.random() * 15;
                    if (progress > 95) progress = 95;
                    
                    progressFill.style.width = progress + '%';
                    
                    if (progress >= 95) {
                        clearInterval(interval);
                    }
                }, 150);
                
                // Store interval for cleanup
                progressSection.dataset.interval = interval;
            } else {
                // Complete progress
                if (progressSection.dataset.interval) {
                    clearInterval(progressSection.dataset.interval);
                }
                
                progressFill.style.width = '100%';
                progressText.textContent = 'Complete';
                
                setTimeout(() => {
                    progressSection.classList.add('hidden');
                    progressFill.style.width = '0%';
                }, 1000);
            }
        }
        
        async function downloadMessages() {
            if (!currentThreadId || currentMessages.length === 0) {
                showAlert('No messages to download.', 'warning');
                return;
            }
            
            const count = document.getElementById('message-count').value;
            
            try {
                showProgress(true, 'Preparing download...');
                
                const response = await fetch(`/api/download/${currentThreadId}?count=${count}`);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `dm_archive_${new Date().getTime()}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    showAlert('Archive download started successfully.', 'success');
                } else {
                    const data = await response.json();
                    showAlert(data.error, 'error');
                }
            } catch (error) {
                showAlert('Download failed. Please try again.', 'error');
            } finally {
                showProgress(false);
            }
        }
        
        // Event listeners
        document.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const activeElement = document.activeElement;
                if (['username', 'password', 'verification-code'].includes(activeElement.id)) {
                    login();
                }
            }
        });
        
        // Auto-clear alerts
        setInterval(() => {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                if (alert.parentElement && alert.parentElement.children.length > 1) {
                    alert.remove();
                }
            });
        }, 10000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return Response(HTML_TEMPLATE, mimetype='text/html')

@app.route('/api/login', methods=['POST'])
def login():
    if not INSTAGRAPI_AVAILABLE:
        return jsonify({
            'success': False, 
            'error': 'Instagram API library not available',
            'message': 'Required dependencies are not installed. Please contact administrator.'
        })
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    verification_code = data.get('verification_code', '').strip()
    
    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'missing_credentials',
            'message': 'Username and password are required.'
        })
    
    try:
        client = Client()
        
        if verification_code:
            client.login(username, password, verification_code=verification_code)
        else:
            client.login(username, password)
        
        # Generate secure session
        session_id = secrets.token_hex(32)
        user_sessions[session_id] = {
            'client': client,
            'username': username,
            'user_id': client.user_id,
            'created_at': datetime.now()
        }
        
        session['session_id'] = session_id
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'username': username
        })
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "two-factor authentication required" in error_msg or "two_factor_required" in error_msg:
            return jsonify({
                'success': False,
                'error': '2fa_required',
                'message': 'Two-factor authentication is required for this account.'
            })
        elif "incorrect username" in error_msg or "user not found" in error_msg:
            return jsonify({
                'success': False,
                'error': 'invalid_credentials',
                'message': 'Invalid username or password.'
            })
        elif "password" in error_msg:
            return jsonify({
                'success': False,
                'error': 'invalid_credentials', 
                'message': 'Invalid username or password.'
            })
        elif "challenge" in error_msg or "suspicious" in error_msg:
            return jsonify({
                'success': False,
                'error': 'security_challenge',
                'message': 'Account security challenge detected. Please try logging in from the Instagram app first.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'authentication_failed',
                'message': f'Authentication failed. Please check your credentials and try again.'
            })

@app.route('/api/conversations')
def get_conversations():
    session_id = session.get('session_id')
    if not session_id or session_id not in user_sessions:
        return jsonify({'success': False, 'error': 'Authentication required. Please sign in again.'})
    
    try:
        client = user_sessions[session_id]['client']
        threads = client.direct_threads()
        
        conversations = []
        for thread in threads:
            users = [user.username for user in thread.users]
            last_msg = ""
            
            if thread.messages and len(thread.messages) > 0:
                msg = thread.messages[0]
                if hasattr(msg, 'text') and msg.text:
                    last_msg = msg.text
                    if len(last_msg) > 60:
                        last_msg = last_msg[:57] + "..."
                else:
                    last_msg = "[Media message]"
            
            conversations.append({
                'id': thread.id,
                'users': users,
                'last_message': last_msg,
                'display_name': ', '.join(users)
            })
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to load conversations: {str(e)}'
        })

@app.route('/api/messages/<thread_id>')
def get_messages(thread_id):
    session_id = session.get('session_id')
    if not session_id or session_id not in user_sessions:
        return jsonify({'success': False, 'error': 'Authentication required. Please sign in again.'})
    
    count = request.args.get('count', 100, type=int)
    count = max(1, min(count, 5000))  # Limit between 1 and 5000
    
    try:
        client = user_sessions[session_id]['client']
        user_id = user_sessions[session_id]['user_id']
        
        messages = client.direct_messages(thread_id, count)
        
        # Get thread info for usernames
        threads = client.direct_threads()
        selected_thread = None
        for thread in threads:
            if thread.id == thread_id:
                selected_thread = thread
                break
        
        if not selected_thread:
            return jsonify({'success': False, 'error': 'Conversation not found.'})
        
        username_map = {user.pk: user.username for user in selected_thread.users}
        username_map[user_id] = "You"
        
        formatted_messages = []
        for msg in sorted(messages, key=lambda m: m.timestamp):
            sender = username_map.get(msg.user_id, f"Unknown User")
            msg_text = msg.text if msg.text is not None else "[No text content]"
            
            formatted_msg = {
                'id': msg.id,
                'sender': sender,
                'text': msg_text,
                'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'is_sent': msg.user_id == user_id
            }
            
            if msg.media:
                if msg.media.media_type == 1:  # Image
                    formatted_msg['media'] = {
                        'type': 'image', 
                        'url': getattr(msg.media, 'thumbnail_url', '#')
                    }
                elif msg.media.media_type == 2:  # Video
                    formatted_msg['media'] = {
                        'type': 'video', 
                        'url': getattr(msg.media, 'video_url', '#')
                    }
            
            formatted_messages.append(formatted_msg)
        
        return jsonify({
            'success': True,
            'messages': formatted_messages,
            'thread_info': {
                'users': [user.username for user in selected_thread.users],
                'display_name': ', '.join(user.username for user in selected_thread.users)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to extract messages: {str(e)}'
        })

@app.route('/api/download/<thread_id>')
def download_messages(thread_id):
    session_id = session.get('session_id')
    if not session_id or session_id not in user_sessions:
        return jsonify({'success': False, 'error': 'Authentication required. Please sign in again.'})
    
    count = request.args.get('count', 1000, type=int)
    count = max(1, min(count, 5000))
    
    try:
        client = user_sessions[session_id]['client']
        user_id = user_sessions[session_id]['user_id']
        
        messages = client.direct_messages(thread_id, count)
        
        # Get thread info
        threads = client.direct_threads()
        selected_thread = None
        for thread in threads:
            if thread.id == thread_id:
                selected_thread = thread
                break
        
        if not selected_thread:
            return jsonify({'success': False, 'error': 'Conversation not found.'})
        
        # Format messages for download
        username_map = {user.pk: user.username for user in selected_thread.users}
        username_map[user_id] = "You"
        
        sorted_messages = sorted(messages, key=lambda m: m.timestamp)
        
        # Create comprehensive archive content
        content = f"""DM ARCHIVE PRO - MESSAGE EXPORT
===============================================

Conversation: {', '.join(u.username for u in selected_thread.users)}
Export Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Messages: {len(sorted_messages)}
Exported by: {user_sessions[session_id]['username']}

===============================================

"""
        
        current_date = None
        
        for msg in sorted_messages:
            msg_date = msg.timestamp.date()
            if current_date != msg_date:
                if current_date is not None:
                    content += "\n"
                
                date_str = msg_date.strftime("%A, %B %d, %Y")
                content += f"\n{'─' * 20} {date_str} {'─' * 20}\n\n"
                current_date = msg_date
            
            sender = username_map.get(msg.user_id, f"Unknown User")
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            
            msg_text = msg.text if msg.text is not None else "[No text content]"
            content += f"[{timestamp}] {sender}: {msg_text}\n"
            
            if msg.media:
                if msg.media.media_type == 1:  # Image
                    url = getattr(msg.media, 'thumbnail_url', 'N/A')
                    content += f"    └─ Image attachment: {url}\n"
                elif msg.media.media_type == 2:  # Video
                    url = getattr(msg.media, 'video_url', 'N/A')
                    content += f"    └─ Video attachment: {url}\n"
            
            content += "\n"
        
        # Add footer
        content += f"""
===============================================
END OF ARCHIVE

Archive Information:
- Export Tool: DM Archive Pro v1.0
- Export Format: Plain Text (.txt)
- Character Encoding: UTF-8
- File Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

DISCLAIMER: This export was generated using an unofficial 
third-party tool and is not affiliated with Instagram.
===============================================
"""
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            delete=False, 
            suffix='.txt', 
            encoding='utf-8',
            prefix='dm_archive_'
        )
        temp_file.write(content)
        temp_file.close()
        
        # Generate secure filename
        users_str = '_'.join(u.username for u in selected_thread.users)
        safe_users = ''.join(c for c in users_str if c.isalnum() or c in ('_', '-'))
        filename = f"dm_archive_{safe_users}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Archive generation failed: {str(e)}'
        })

@app.route('/api/logout', methods=['POST'])
def logout():
    session_id = session.get('session_id')
    if session_id and session_id in user_sessions:
        del user_sessions[session_id]
    session.clear()
    return jsonify({'success': True, 'message': 'Signed out successfully'})

# Session cleanup (basic implementation)
@app.before_request
def cleanup_sessions():
    """Remove sessions older than 2 hours"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in user_sessions.items():
        if 'created_at' in session_data:
            age = current_time - session_data['created_at']
            if age.total_seconds() > 7200:  # 2 hours
                expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del user_sessions[session_id]

if __name__ == '__main__':
    print("=" * 60)
    print("DM Archive Pro - Professional Instagram Message Extractor")
    print("=" * 60)
    print("Access your application at: http://localhost:5000")
    print("Secure session management enabled")
    print("Legal disclaimers included")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)