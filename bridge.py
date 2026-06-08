import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class ChessHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Разрешаем запросы из локального HTML файла (CORS)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        fen = data.get('fen')
        depth = data.get('depth', 15)
        
        # Запускаем Stockfish, если он еще не запущен или закрылся
        if not hasattr(self.server, 'sf') or self.server.sf.poll() is not None:
            self.server.sf = subprocess.Popen(
                ['stockfish.exe'], 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                text=True, 
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW # Скрываем черное окно консоли
            )
            self.server.sf.stdin.write("uci\nisready\n")
            self.server.sf.stdin.flush()
            # Ждем, пока движок скажет, что готов
            while True:
                if "readyok" in self.server.sf.stdout.readline():
                    break
        
        # Отправляем позицию и просим найти ход
        self.server.sf.stdin.write(f"position fen {fen}\ngo depth {depth}\n")
        self.server.sf.stdin.flush()
        
        best_move = "a1a1" # Запасной ход на всякий случай
        while True:
            line = self.server.sf.stdout.readline()
            if line.startswith("bestmove"):
                best_move = line.split()[1]
                break
                
        response = json.dumps({"move": best_move})
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        pass # Отключаем спам логами в консоль

if __name__ == '__main__':
    print("✅ Мост запущен! Теперь откройте chess.html в браузере.")
    print("Чтобы закрыть движок, просто закройте это окно или нажмите Ctrl+C.")
    server = HTTPServer(('localhost', 8080), ChessHandler)
    server.serve_forever()