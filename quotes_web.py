#!/usr/bin/env python3
"""
Quote Explorer - Web Interface
Run with: python3 quote_web.py
"""

import os
import json
import random
import webbrowser
import threading
import sys
import subprocess
import errno
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
from collections import defaultdict


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


class QuoteHandler(BaseHTTPRequestHandler):
    quotes = []
    tags_index = defaultdict(list)
    author_index = defaultdict(list)
    server_instance = None
    shutdown_requested = threading.Event()
    app_base_path = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(app_base_path, 'logs', 'quotes_web')

    @classmethod
    def ensure_log_dir(cls):
        """Ensure log directory exists"""
        os.makedirs(cls.logs_path, exist_ok=True)

    @classmethod
    def load_quotes(cls):
        """Load quotes from assets/quotes/quotes.json"""
        quote_file = os.path.join(cls.app_base_path, 'assets', 'quotes', 'quotes.json')
        try:
            with open(quote_file, 'r', encoding='utf-8') as f:
                all_quotes = json.load(f)

            cls.quotes = [q for q in all_quotes if q.get('text')]
            cls.tags_index = defaultdict(list)
            cls.author_index = defaultdict(list)

            for q in cls.quotes:
                for tag in q.get('tags', []):
                    cls.tags_index[tag.lower()].append(q)

                author = (q.get('author') or '').lower()
                if author:
                    cls.author_index[author].append(q)

            print(f"Loaded {len(cls.quotes)} quotes from {quote_file}")
        except Exception as e:
            print(f"Error loading quotes: {e}")
            cls.quotes = []
            cls.tags_index = defaultdict(list)
            cls.author_index = defaultdict(list)

    @classmethod
    def log_activity(cls, activity, details=""):
        """Log activity to file"""
        cls.ensure_log_dir()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = os.path.join(cls.logs_path, 'web_activity.log')
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {activity}: {details}\n")
        except Exception as e:
            print(f"Could not write to log: {e}")

    def send_html(self, content):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        self.load_quotes()

        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/':
            self.send_html(self.get_html())

        elif path == '/api/random':
            if not self.quotes:
                self.send_json({'error': 'No quotes loaded'})
                return

            quote = random.choice(self.quotes)
            self.send_json(quote)
            self.log_activity(
                "Random Quote",
                f"ID: {quote.get('id', '')} - {quote.get('author', quote.get('speaker', ''))}"
            )

        elif path == '/api/tags':
            tags = [{'name': tag, 'count': len(quotes)} for tag, quotes in sorted(self.tags_index.items())]
            self.send_json(tags)

        elif path == '/api/authors':
            authors = [{'name': author, 'count': len(quotes)} for author, quotes in sorted(self.author_index.items())]
            self.send_json(authors[:50])

        elif path == '/api/stats':
            stats = {
                'total_quotes': len(self.quotes),
                'total_tags': len(self.tags_index),
                'total_authors': len(self.author_index)
            }
            self.send_json(stats)

        elif path == '/api/shutdown':
            self.send_json({'status': 'shutting down'})
            self.log_activity("Server Shutdown", "Request received")
            threading.Thread(target=self.shutdown_server, daemon=True).start()

        elif path == '/api/open-quote-file':
            self.open_quote_file()
            self.send_json({'status': 'opened'})
            self.log_activity("Open Quote File", "User opened quotes.json")

        elif path == '/api/open-app-folder':
            self.open_app_folder()
            self.send_json({'status': 'opened'})
            self.log_activity("Open App Folder", "User opened app directory")

        elif path == '/api/search':
            query = parse_qs(parsed.query)
            term = query.get('term', [''])[0].lower()

            results = []
            if term:
                for q in self.quotes:
                    if term in q['text'].lower():
                        results.append(q)
                    elif q.get('author') and term in q['author'].lower():
                        results.append(q)
                    elif q.get('speaker') and term in q['speaker'].lower():
                        results.append(q)
                    elif q.get('source') and term in q['source'].lower():
                        results.append(q)
                    elif any(term in tag.lower() for tag in q.get('tags', [])):
                        results.append(q)

            self.send_json(results[:20])
            self.log_activity("Search", f"Term: '{term}', Results: {len(results)}")

        else:
            self.send_error(404)

    def open_quote_file(self):
        """Open assets/quotes/quotes.json in the default application"""
        quote_file = os.path.join(self.app_base_path, 'assets', 'quotes', 'quotes.json')
        if os.path.exists(quote_file):
            if sys.platform == 'darwin':
                subprocess.run(['open', quote_file])
            elif sys.platform == 'win32':
                os.startfile(quote_file)
            else:
                subprocess.run(['xdg-open', quote_file])

    def open_app_folder(self):
        """Open the app folder in the default file explorer"""
        if sys.platform == 'darwin':
            subprocess.run(['open', self.app_base_path])
        elif sys.platform == 'win32':
            os.startfile(self.app_base_path)
        else:
            subprocess.run(['xdg-open', self.app_base_path])

    def shutdown_server(self):
        if self.server_instance:
            self.log_activity("Server Shutdown", "Executing shutdown")
            self.shutdown_requested.set()
            self.server_instance.shutdown()

    def get_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quote of the Day</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica', 'Arial', sans-serif;
            transition: background 0.3s ease, color 0.3s ease;
            min-height: 100vh;
            padding: 20px;
        }

        body.light-mode {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        body.light-mode .quote-card {
            background: white;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        body.light-mode .quote-text {
            color: #2d3748;
        }

        body.light-mode .quote-author {
            color: #718096;
        }

        body.light-mode .search-section {
            background: white;
        }

        body.light-mode .result-item {
            background: #f7fafc;
        }

        body.light-mode .result-item:hover {
            background: #edf2f7;
        }

        body.light-mode .stats,
        body.light-mode h1 {
            color: white;
        }

        body.light-mode .favorite-star {
            color: #cbd5e0;
        }

        body.light-mode .favorite-star:hover,
        body.light-mode .favorite-star.active {
            color: #f59e0b;
        }

        .copy-button {
            position: absolute;
            bottom: 27px;
            right: 60px;
            font-size: 33px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: transparent;
            border: none;
            padding: 5px;
            line-height: 1;
            border-radius: 8px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #cbd5e0;
        }

        body.dark-mode .copy-button {
            color: #718096;
        }

        .copy-button:hover {
            transform: scale(1.1);
            background-color: rgba(0, 0, 0, 0.05);
        }

        body.dark-mode .copy-button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        body.light-mode .tag {
            background: #e8f0fe;
            color: #1e6fdf;
            border: 1px solid #d0e0fc;
        }

        body.light-mode .result-favorite-star {
            color: #cbd5e0;
        }

        body.light-mode .result-favorite-star.favorited,
        body.light-mode .result-favorite-star:hover {
            color: #f59e0b;
        }

        body.dark-mode {
            background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
        }

        body.dark-mode .quote-card {
            background: #2d3748;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }

        body.dark-mode .quote-text {
            color: #e2e8f0;
        }

        body.dark-mode .quote-author {
            color: #a0aec0;
        }

        body.dark-mode .quote-source {
            color: #90cdf4;
        }

        body.dark-mode .quote-tags {
            color: #9ae6b4;
        }

        body.dark-mode .tag {
            background: #4a5568;
            color: #e2e8f0;
        }

        body.dark-mode .search-section {
            background: #2d3748;
        }

        body.dark-mode .search-input {
            background: #4a5568;
            border-color: #718096;
            color: #e2e8f0;
        }

        body.dark-mode .search-input::placeholder {
            color: #a0aec0;
        }

        body.dark-mode .result-item {
            background: #4a5568;
            color: #e2e8f0;
        }

        body.dark-mode .result-item:hover {
            background: #718096;
        }

        body.dark-mode .stats,
        body.dark-mode h1 {
            color: #e2e8f0;
        }

        body.dark-mode .favorite-star,
        body.dark-mode .result-favorite-star {
            color: #718096;
        }

        body.dark-mode .favorite-star:hover,
        body.dark-mode .favorite-star.active,
        body.dark-mode .result-favorite-star.favorited,
        body.dark-mode .result-favorite-star:hover {
            color: #f59e0b;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            position: relative;
        }

        .dark-mode-toggle {
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 1000;
        }

        .dev-mode-toggle {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }

        .toggle-button {
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        body.light-mode .toggle-button {
            background: rgba(0, 0, 0, 0.2);
            color: white;
        }

        body.dark-mode .toggle-button {
            background: rgba(255, 255, 255, 0.2);
            color: #e2e8f0;
        }

        .toggle-button:hover {
            transform: scale(1.05);
        }

        .quote-card {
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            position: relative;
        }

        .quote-card:hover {
            transform: translateY(-5px);
        }

        .quote-text {
            font-size: 24px;
            line-height: 1.4;
            margin-bottom: 20px;
            font-weight: 500;
        }

        .quote-author {
            font-size: 18px;
            font-style: italic;
            margin-bottom: 10px;
        }

        .quote-source {
            font-size: 14px;
            margin-bottom: 10px;
            line-height: 1.5;
        }

        .quote-tags {
            font-size: 12px;
            margin-top: 15px;
        }

        .tag {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            margin-right: 8px;
            font-size: 11px;
        }

        .favorite-star {
            position: absolute;
            bottom: 20px;
            right: 20px;
            font-size: 28px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: transparent;
            border: none;
            padding: 5px;
        }

        .favorite-star:hover {
            transform: scale(1.1);
        }

        .button {
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 5px;
            font-weight: 500;
        }

        .button:hover {
            transform: translateY(-2px);
        }

        .button:active {
            transform: translateY(0);
        }

        .button-primary {
            background: #667eea;
            color: white;
        }

        .button-primary:hover {
            background: #5a67d8;
        }

        .button-secondary {
            background: #48bb78;
            color: white;
        }

        .button-secondary:hover {
            background: #38a169;
        }

        .button-warning {
            background: #f59e0b;
            color: white;
        }

        .button-warning:hover {
            background: #d97706;
        }

        .button-danger {
            background: #e53e3e;
            color: white;
        }

        .button-danger:hover {
            background: #c53030;
        }

        .button-info {
            background: #4299e1;
            color: white;
        }

        .button-info:hover {
            background: #3182ce;
        }

        body.dark-mode .button-primary {
            background: #5a67d8;
        }

        body.dark-mode .button-secondary {
            background: #38a169;
        }

        body.dark-mode .button-warning {
            background: #d97706;
        }

        body.dark-mode .button-danger {
            background: #c53030;
        }

        body.dark-mode .button-info {
            background: #3182ce;
        }

        .search-section {
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            transition: background 0.3s ease;
        }

        .favorites-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }

        .favorites-header h3 {
            margin: 0;
        }

        .favorites-search-toggle {
            background: transparent;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            padding: 4px 0;
            color: #2d3748;
        }

        .favorites-search-toggle:hover {
            text-decoration: underline;
        }

        body.dark-mode .favorites-search-toggle {
            color: #e2e8f0;
        }

        .favorites-search-box {
            display: none;
        }

        .search-input {
            width: 100%;
            padding: 12px;
            border: 2px solid;
            border-radius: 10px;
            font-size: 16px;
            margin: 10px 0;
            transition: all 0.3s ease;
        }

        .search-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .results {
            margin-top: 20px;
        }

        .result-item {
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
        }

        .result-favorite-star {
            position: absolute;
            bottom: 10px;
            right: 10px;
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: transparent;
            border: none;
            padding: 5px;
            z-index: 10;
        }

        .result-favorite-star:hover {
            transform: scale(1.1);
        }

        .loading {
            text-align: center;
            font-size: 18px;
            margin-top: 20px;
        }

        .stats {
            text-align: center;
            margin-top: 20px;
            font-size: 14px;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .fade-in {
            animation: fadeIn 0.5s ease;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .toast {
            position: fixed;
            bottom: 80px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            animation: slideIn 0.3s ease;
            z-index: 2000;
            font-size: 14px;
        }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 36px;
            font-weight: normal;
            transition: color 0.3s ease;
        }

        .button-group {
            text-align: center;
            margin: 20px 0;
        }

        .search-stats {
            font-size: 12px;
            color: #718096;
            margin-top: 5px;
            text-align: right;
        }

        body.dark-mode .search-stats {
            color: #a0aec0;
        }
        
        .tag {
            cursor: pointer;
            transition: background 0.2s;
            }
        
        .tag:hover {
            background: #cbd5e0;
            transform: scale(1.02);
            }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 20px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            animation: fadeIn 0.3s ease;
        }

        body.dark-mode .modal-content {
            background: #2d3748;
            color: #e2e8f0;
        }

        .modal-content h2 {
            margin-bottom: 20px;
            font-size: 28px;
        }

        .modal-content .button {
            display: inline-block;
            margin: 10px;
            min-width: 150px;
        }

        .close-modal {
            margin-top: 20px;
            background: #718096;
        }

        .close-modal:hover {
            background: #4a5568;
        }
    </style>
</head>
<body class="light-mode">
    <div class="dark-mode-toggle">
        <button class="toggle-button" onclick="toggleDarkMode()">◯ Dark Mode</button>
    </div>

    <div class="dev-mode-toggle">
        <button class="toggle-button" onclick="openDevMode()">⚙️ Dev Mode</button>
    </div>

    <div class="container">
        <h1>Quote of the Day</h1>

        <div class="quote-card fade-in" id="quoteCard">
            <div class="quote-text" id="quoteText">Loading...</div>
            <div class="quote-author" id="quoteAuthor"></div>
            <div class="quote-source" id="quoteSource"></div>
            <div class="quote-tags" id="quoteTags"></div>
            <button class="copy-button" onclick="copyCurrentQuote(event)" title="Copy quote">⧉</button>
            <button class="favorite-star" onclick="toggleFavorite(currentQuote, event)">☆</button>
        </div>

        <div class="button-group">
            <button class="button button-primary" onclick="loadRandomQuote()">🎲 Random Quote</button>
            <button class="button button-warning" onclick="toggleFavorites()">⭐ Favorites</button>
            <button class="button button-secondary" onclick="toggleSearch()">🔍 Search</button>
            <button class="button button-danger" onclick="stopServer()">🅇 Stop Server</button>
        </div>

        <div id="searchSection" style="display: none;">
            <div class="search-section">
                <h3>Search Quotes</h3>
                <input type="text" id="searchTerm" class="search-input" placeholder="Type to search (min. 2 characters)..." oninput="handleLiveSearch()">
                <div id="searchResults" class="results"></div>
                <div id="searchStats" class="search-stats"></div>
            </div>
        </div>

        <div id="favoritesSection" style="display: none;">
            <div class="search-section">
                <div class="favorites-header">
                    <h3>⭐ Favorites</h3>
                    <button id="favoritesSearchToggle" class="favorites-search-toggle" onclick="toggleFavoritesSearch()">🔎 Search Favorites (0)</button>
                </div>
                <div id="favoritesSearchBox" class="favorites-search-box">
                    <input type="text" id="favoritesSearchTerm" class="search-input" placeholder="Type to search favorites (min. 2 characters)..." oninput="handleFavoritesSearch()">
                </div>
                <div id="favoritesResults" class="results"></div>
                <div id="favoritesSearchStats" class="search-stats"></div>
            </div>
        </div>

        <div class="stats" id="stats"></div>
    </div>

    <div id="devModal" class="modal">
        <div class="modal-content">
            <h2>Developer Mode</h2>
            <button class="button button-info" onclick="openQuoteFile()">Edit quotes.json</button>
            <button class="button button-info" onclick="openAppFolder()">Show Code</button>
            <button class="button close-modal" onclick="closeDevMode()">Close</button>
        </div>
    </div>

    <script>
        let currentQuote = null;
        let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');

        let searchTimeout = null;
        let abortController = null;
        let searchCache = new Map();

        function setDarkMode(isDark) {
            if (isDark) {
                document.body.classList.remove('light-mode');
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'enabled');
                document.querySelector('.dark-mode-toggle .toggle-button').innerHTML = '◑ Light Mode';
            } else {
                document.body.classList.remove('dark-mode');
                document.body.classList.add('light-mode');
                localStorage.setItem('darkMode', 'disabled');
                document.querySelector('.dark-mode-toggle .toggle-button').innerHTML = '◯ Dark Mode';
            }
        }

        function toggleDarkMode() {
            const isDark = document.body.classList.contains('dark-mode');
            setDarkMode(!isDark);
        }

        function getSystemTheme() {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        }

        function loadThemePreference() {
            const savedMode = localStorage.getItem('darkMode');
            if (savedMode === 'enabled') {
                setDarkMode(true);
            } else if (savedMode === 'disabled') {
                setDarkMode(false);
            } else {
                setDarkMode(getSystemTheme());
            }
        }

        function openDevMode() {
            document.getElementById('devModal').classList.add('active');
        }

        function closeDevMode() {
            document.getElementById('devModal').classList.remove('active');
        }

        async function openQuoteFile() {
            try {
                await fetch('/api/open-quote-file');
                showToast('Opening quotes.json...');
                closeDevMode();
            } catch (error) {
                console.error('Error opening file:', error);
                showToast('Error opening file');
            }
        }

        async function openAppFolder() {
            try {
                await fetch('/api/open-app-folder');
                showToast('Opening app folder...');
                closeDevMode();
            } catch (error) {
                console.error('Error opening folder:', error);
                showToast('Error opening folder');
            }
        }

        function showToast(message) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
        }

        function formatNameList(nameStr) {
            if (!nameStr || nameStr.trim() === '') return '';

            const names = nameStr
                .split(',')
                .map(s => s.trim())
                .filter(Boolean);

            if (names.length === 0) return '';
            if (names.length === 1) return names[0];

            const last = names.pop();
            return `${names.join(', ')} and ${last}`;
        }

        function getAttribution(quote) {
            let primary = '';
            let secondary = [];

            const speaker = quote.speaker ? quote.speaker.trim() : '';
            const author = quote.author ? quote.author.trim() : '';
            const source = quote.source ? quote.source.trim() : '';

            if (speaker) {
                primary = formatNameList(speaker);

                if (author && author !== speaker) {
                    if (source) {
                        secondary = [`from ${source}`, `by ${formatNameList(author)}`];
                    } else {
                        secondary = [`from ${formatNameList(author)}`];
                    }
                } else if (source) {
                    secondary = [`from ${source}`];
                }
            } else if (author) {
                primary = formatNameList(author);

                if (source) {
                    secondary = [`from ${source}`];
                }
            } else if (source) {
                primary = source;
            } else {
                primary = 'Unknown';
            }

            return { primary, secondary };
        }

        function copyCurrentQuote(event) {
            if (event) event.stopPropagation();

            if (!currentQuote) {
                showToast('No quote to copy');
                return;
            }

            const { primary, secondary } = getAttribution(currentQuote);
            let textToCopy = `Quote of the day\\n\\n"${currentQuote.text}"\\n\\n– ${primary}`;

            if (secondary.length) {
                textToCopy += `\\n${secondary.join('\\n')}`;
            }

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(textToCopy)
                    .then(() => showToast('Copied to clipboard'))
                    .catch(err => {
                        console.error('Clipboard write failed:', err);
                        fallbackCopy(textToCopy);
                    });
            } else {
                fallbackCopy(textToCopy);
            }
        }

        function fallbackCopy(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.top = '-9999px';
            textarea.style.left = '-9999px';

            document.body.appendChild(textarea);
            textarea.select();
            textarea.setSelectionRange(0, text.length);

            let success = false;
            try {
                success = document.execCommand('copy');
            } catch (err) {
                console.error('Fallback copy failed:', err);
            }

            document.body.removeChild(textarea);

            if (success) {
                showToast('⧉ Copied to clipboard!');
            } else {
                showToast('Could not copy. Please copy manually.');
            }
        }

        function saveFavorites() {
            localStorage.setItem('favorites', JSON.stringify(favorites));
            updateFavoritesSearchToggle();
        }

        function isFavorite(quote) {
            return favorites.some(f => f.id === quote.id);
        }

        function addToFavorites(quote) {
            if (!isFavorite(quote)) {
                favorites.push(quote);
                saveFavorites();
                updateFavoriteStars(quote);
                showToast('Added to favorites');

                if (document.getElementById('favoritesSection').style.display === 'block') {
                    displayFavorites();
                }
            }
        }

        function removeFromFavorites(quote) {
            favorites = favorites.filter(f => f.id !== quote.id);
            saveFavorites();
            updateFavoriteStars(quote);
            showToast('Removed from favorites');

            if (document.getElementById('favoritesSection').style.display === 'block') {
                displayFavorites();
            }
        }

        function toggleFavorite(quote, event) {
            if (event) event.stopPropagation();
            if (!quote) return;

            if (isFavorite(quote)) {
                removeFromFavorites(quote);
            } else {
                addToFavorites(quote);
            }
        }

        function updateFavoriteStars(quote) {
            const mainStar = document.querySelector('#quoteCard .favorite-star');

            if (mainStar && currentQuote && quote.id === currentQuote.id) {
                mainStar.textContent = isFavorite(quote) ? '★' : '☆';
                mainStar.classList.toggle('active', isFavorite(quote));
            }

            document.querySelectorAll('.result-item').forEach(item => {
                const itemQuote = item.quoteData;

                if (itemQuote && itemQuote.id === quote.id) {
                    const star = item.querySelector('.result-favorite-star');

                    if (star) {
                        star.textContent = isFavorite(quote) ? '★' : '☆';
                        star.classList.toggle('favorited', isFavorite(quote));
                    }
                }
            });
        }

        async function loadRandomQuote() {
            try {
                const response = await fetch('/api/random');
                currentQuote = await response.json();

                if (currentQuote.error) {
                    document.getElementById('quoteText').textContent = currentQuote.error;
                    return;
                }

                displayQuote(currentQuote);
            } catch (error) {
                console.error('Error loading quote:', error);
                document.getElementById('quoteText').textContent = 'Error loading quote. Please refresh.';
            }
        }

        function displayQuote(quote) {
            const card = document.getElementById('quoteCard');
            card.classList.remove('fade-in');
            void card.offsetWidth;
            card.classList.add('fade-in');

            document.getElementById('quoteText').textContent = quote.text;

            const { primary, secondary } = getAttribution(quote);
            document.getElementById('quoteAuthor').textContent = `— ${primary}`;

            const sourceEl = document.getElementById('quoteSource');
            if (secondary.length) {
                sourceEl.innerHTML = secondary
                    .map(line => `<div>${escapeHtml(line)}</div>`)
                    .join('');
                sourceEl.style.display = 'block';
            } else {
                sourceEl.innerHTML = '';
                sourceEl.style.display = 'none';
            }

            const tagsEl = document.getElementById('quoteTags');
            if (quote.tags && quote.tags.length > 0) {
                const tagsHtml = quote.tags
                    .map(tag => `<span class="tag">${escapeHtml(tag)}</span>`)
                    .join('');
                tagsEl.innerHTML = `tags: ${tagsHtml}`;
                tagsEl.style.display = 'block';

                // Add click handlers to each tag
                document.querySelectorAll('#quoteTags .tag').forEach(tagSpan => {
                    tagSpan.style.cursor = 'pointer';
                    tagSpan.addEventListener('click', (e) => {
                        e.stopPropagation();
                        searchByTag(tagSpan.textContent);
                    });
                });
            } else {
                tagsEl.innerHTML = '';
                tagsEl.style.display = 'none';
            }

            const star = document.querySelector('#quoteCard .favorite-star');
            star.textContent = isFavorite(quote) ? '★' : '☆';
            star.classList.toggle('active', isFavorite(quote));
        }
        
        function searchByTag(tag) {
            // Set search input value
            const searchInput = document.getElementById('searchTerm');
            searchInput.value = tag;

            // Show search section, hide favorites
            const searchSection = document.getElementById('searchSection');
            const favoritesSection = document.getElementById('favoritesSection');
            searchSection.style.display = 'block';
            favoritesSection.style.display = 'none';

            // Trigger the search (re-use existing live search)
            if (typeof handleLiveSearch === 'function') {
                handleLiveSearch();
            } else {
                // fallback: direct call
                performLiveSearch(tag);
            }

            // Optional: scroll to search results
            searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function searchFavoritesByTag(tag) {
            const favoritesSection = document.getElementById('favoritesSection');
            const searchSection = document.getElementById('searchSection');
            const favoritesSearchBox = document.getElementById('favoritesSearchBox');
            const favoritesSearchInput = document.getElementById('favoritesSearchTerm');

            favoritesSection.style.display = 'block';
            searchSection.style.display = 'none';
            favoritesSearchBox.style.display = 'block';
            favoritesSearchInput.value = tag;
            handleFavoritesSearch();
            favoritesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        

        function toggleSearch() {
            const searchSection = document.getElementById('searchSection');
            const favoritesSection = document.getElementById('favoritesSection');

            if (searchSection.style.display === 'none') {
                searchSection.style.display = 'block';
                favoritesSection.style.display = 'none';
                document.getElementById('searchTerm').focus();
            } else {
                searchSection.style.display = 'none';
                clearSearchResults();
            }
        }

        function toggleFavorites() {
            const favoritesSection = document.getElementById('favoritesSection');
            const searchSection = document.getElementById('searchSection');

            if (favoritesSection.style.display === 'none') {
                favoritesSection.style.display = 'block';
                searchSection.style.display = 'none';
                displayFavorites();
            } else {
                favoritesSection.style.display = 'none';
            }
        }

        function updateFavoritesSearchToggle() {
            const toggle = document.getElementById('favoritesSearchToggle');

            if (toggle) {
                toggle.textContent = `🔎 Search Favorites (${favorites.length})`;
            }
        }

        function toggleFavoritesSearch() {
            const searchBox = document.getElementById('favoritesSearchBox');
            const searchInput = document.getElementById('favoritesSearchTerm');
            const searchStats = document.getElementById('favoritesSearchStats');
            const shouldShow = searchBox.style.display !== 'block';

            searchBox.style.display = shouldShow ? 'block' : 'none';

            if (shouldShow) {
                searchInput.focus();
                handleFavoritesSearch();
            } else {
                searchInput.value = '';
                searchStats.innerHTML = '';
                displayFavorites();
            }
        }

        function quoteMatchesTerm(quote, term) {
            const lowerTerm = term.toLowerCase();
            const searchableValues = [
                quote.text,
                quote.author,
                quote.speaker,
                quote.source,
                ...(quote.tags || [])
            ];

            return searchableValues.some(value =>
                String(value || '').toLowerCase().includes(lowerTerm)
            );
        }

        function searchFavorites(term) {
            return favorites.filter(quote => quoteMatchesTerm(quote, term));
        }

        function handleFavoritesSearch() {
            const term = document.getElementById('favoritesSearchTerm').value.trim();
            const searchStats = document.getElementById('favoritesSearchStats');

            updateFavoritesSearchToggle();

            if (!term || term.length < 2) {
                searchStats.innerHTML = '';
                displayFavorites();
                return;
            }

            displayFavoriteSearchResults(searchFavorites(term), term);
        }

        function displayFavoriteSearchResults(results, term) {
            const favoritesDiv = document.getElementById('favoritesResults');
            const searchStats = document.getElementById('favoritesSearchStats');

            favoritesDiv.innerHTML = '';

            if (results.length === 0) {
                favoritesDiv.innerHTML = '<p>No quotes found.</p>';
            } else {
                results.forEach(quote => {
                    const quoteDiv = createResultItem(quote, 'favorites');
                    favoritesDiv.appendChild(quoteDiv);
                });
            }

            searchStats.innerHTML = `Found ${results.length} quote(s) for "${escapeHtml(term)}"`;
        }

        function displayFavorites() {
            const favoritesDiv = document.getElementById('favoritesResults');
            const searchBox = document.getElementById('favoritesSearchBox');
            const searchInput = document.getElementById('favoritesSearchTerm');

            updateFavoritesSearchToggle();

            if (favorites.length === 0) {
                favoritesDiv.innerHTML = '<p>No favorites yet. Click the ☆ on any quote to add it!</p>';
                document.getElementById('favoritesSearchStats').innerHTML = '';
                return;
            }

            if (searchBox.style.display === 'block' && searchInput.value.trim().length >= 2) {
                handleFavoritesSearch();
                return;
            }

            document.getElementById('favoritesSearchStats').innerHTML = '';
            favoritesDiv.innerHTML = '';
            favorites.forEach(quote => {
                const quoteDiv = createResultItem(quote, 'favorites');
                favoritesDiv.appendChild(quoteDiv);
            });
        }

        function createResultItem(quote, source) {
            const quoteDiv = document.createElement('div');
            quoteDiv.className = 'result-item';
            quoteDiv.quoteData = quote;
            quoteDiv.onclick = () => selectQuote(quote, source);

            const isFav = isFavorite(quote);
            const { primary, secondary } = getAttribution(quote);

            let attributionLine = `— ${primary}`;
            if (secondary.length) {
                attributionLine += ` (${secondary.join('; ')})`;
            }


            let tagsHtml = '';
            if (quote.tags && quote.tags.length > 0) {
                const clickableTags = quote.tags.slice(0, 3).map(tag => 
                    `<span class="tag" style="cursor:pointer">${escapeHtml(tag)}</span>`
                ).join(', ');
                tagsHtml = `<br><small>tags: ${clickableTags}</small>`;
            }


            quoteDiv.innerHTML = `
                <strong>${escapeHtml(quote.text.substring(0, 100))}${quote.text.length > 100 ? '...' : ''}</strong><br>
                <small>${escapeHtml(attributionLine)}</small>
                ${tagsHtml}
                <button class="result-favorite-star ${isFav ? 'favorited' : ''}">${isFav ? '★' : '☆'}</button>
            `;

            quoteDiv.querySelectorAll('.tag').forEach(tagSpan => {
                tagSpan.onclick = e => {
                    e.stopPropagation();
                    const tag = tagSpan.textContent;

                    if (source === 'favorites') {
                        searchFavoritesByTag(tag);
                    } else {
                        searchByTag(tag);
                    }
                };
            });

            const starBtn = quoteDiv.querySelector('.result-favorite-star');
            starBtn.onclick = e => {
                e.stopPropagation();
                toggleFavorite(quote, e);
            };

            return quoteDiv;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text == null ? '' : String(text);
            return div.innerHTML;
        }

        function clearSearchResults() {
            document.getElementById('searchResults').innerHTML = '';
            document.getElementById('searchTerm').value = '';
            document.getElementById('searchStats').innerHTML = '';

            if (searchCache) {
                searchCache.clear();
            }
        }

        function handleLiveSearch() {
            const term = document.getElementById('searchTerm').value.trim();

            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }

            if (abortController) {
                abortController.abort();
            }

            if (!term || term.length < 2) {
                document.getElementById('searchResults').innerHTML = '';
                document.getElementById('searchStats').innerHTML = '';
                return;
            }

            if (searchCache.has(term)) {
                displaySearchResults(searchCache.get(term), term);
                return;
            }

            searchTimeout = setTimeout(() => {
                performLiveSearch(term);
            }, 300);
        }

        async function performLiveSearch(term) {
            abortController = new AbortController();

            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '<div class="loading">Searching...</div>';
            document.getElementById('searchStats').innerHTML = '';

            try {
                const response = await fetch(`/api/search?term=${encodeURIComponent(term)}`, {
                    signal: abortController.signal
                });

                const results = await response.json();

                searchCache.set(term, results);

                if (searchCache.size > 50) {
                    const firstKey = searchCache.keys().next().value;
                    searchCache.delete(firstKey);
                }

                displaySearchResults(results, term);
            } catch (error) {
                if (error.name === 'AbortError') {
                    return;
                }

                console.error('Error searching:', error);
                resultsDiv.innerHTML = '<p>Error searching. Please try again.</p>';
            }
        }

        function displaySearchResults(results, term) {
            const resultsDiv = document.getElementById('searchResults');
            const searchStats = document.getElementById('searchStats');

            if (results.length === 0) {
                resultsDiv.innerHTML = '<p>No quotes found.</p>';
                searchStats.innerHTML = '';
                return;
            }

            resultsDiv.innerHTML = '';
            results.forEach(quote => {
                const quoteDiv = createResultItem(quote, 'search');
                resultsDiv.appendChild(quoteDiv);
            });

            searchStats.innerHTML = `Found ${results.length} quote(s) for "${escapeHtml(term)}"`;
        }

        function selectQuote(quote, source) {
            currentQuote = quote;
            displayQuote(quote);

            if (source === 'search') {
                const searchSection = document.getElementById('searchSection');

                if (searchSection.style.display === 'block') {
                    const currentTerm = document.getElementById('searchTerm').value.trim();

                    if (currentTerm && currentTerm.length >= 2) {
                        if (searchCache.has(currentTerm)) {
                            displaySearchResults(searchCache.get(currentTerm), currentTerm);
                        } else {
                            performLiveSearch(currentTerm);
                        }
                    }
                }
            } else if (source === 'favorites') {
                const favoritesSection = document.getElementById('favoritesSection');

                if (favoritesSection.style.display === 'block') {
                    displayFavorites();
                }
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                const statsDiv = document.getElementById('stats');
                statsDiv.innerHTML = `${stats.total_quotes} quotes | ${stats.total_tags} tags | ${stats.total_authors} authors`;
            } catch (error) {
                console.error('Error loading stats:', error);
                document.getElementById('stats').innerHTML = 'Loading stats...';
            }
        }

        async function stopServer() {
            if (confirm('Are you sure you want to stop the server?')) {
                try {
                    await fetch('/api/shutdown');
                } catch (error) {
                    console.error('Error stopping server:', error);
                } finally {
                    document.body.innerHTML = '<div style="text-align: center; margin-top: 100px;"><h1>Server Stopped</h1><p>You can close this window now.</p></div>';
                }
            }
        }

        loadRandomQuote();
        loadStats();
        loadThemePreference();
        updateFavoritesSearchToggle();

        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('darkMode')) {
                setDarkMode(e.matches);
            }
        });

        document.getElementById('searchTerm').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleLiveSearch();
            }
        });

        window.onclick = function(event) {
            const modal = document.getElementById('devModal');

            if (event.target === modal) {
                closeDevMode();
            }
        };
    </script>
</body>
</html>"""


def open_browser(url, delay=1.5):
    """Open browser after a short delay to ensure server is running"""
    def _open():
        import time
        time.sleep(delay)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def is_address_in_use(error):
    return error.errno in (errno.EADDRINUSE, 48, 98)


def existing_quotes_server_is_running(url, timeout=1.5):
    try:
        with urlopen(f"{url}/api/stats", timeout=timeout) as response:
            if response.status != 200:
                return False

            data = json.loads(response.read().decode('utf-8'))
            return 'total_quotes' in data and 'total_tags' in data
    except (OSError, URLError, json.JSONDecodeError):
        return False


def reopen_existing_server(url):
    if existing_quotes_server_is_running(url):
        print(f"Quote of the Day is already running at {url}")
        print("Opening existing app in browser . . .")
        webbrowser.open(url)
        return 0

    print(f"Port is already in use, but {url} does not look like Quote of the Day.")
    return 1


def run_server(port=8000):
    url = f"http://localhost:{port}"
    QuoteHandler.shutdown_requested.clear()
    QuoteHandler.load_quotes()
    try:
        server = ReusableHTTPServer(('localhost', port), QuoteHandler)
    except OSError as error:
        if is_address_in_use(error):
            return reopen_existing_server(url)
        raise

    QuoteHandler.server_instance = server

    print(f"Quote of the Day running at {url}")
    print("Opening app in browser . . .")
    print("Press Ctrl+C to stop server")

    open_browser(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGoodbye!")
        server.shutdown()
    finally:
        server.server_close()
        QuoteHandler.server_instance = None
        print("Server stopped")

    return 0


if __name__ == '__main__':
    sys.exit(run_server())
