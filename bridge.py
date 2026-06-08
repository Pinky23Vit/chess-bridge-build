import subprocess
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class ChessHandler(BaseHTTPRequestHandler):
    
    # Разрешаем запросы из локального HTML файла (обход CORS)
    def do_OPTIONS(self):
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
        
        # Читаем данные от HTML-страницы
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        fen = data.get('fen', 'startpos')
        depth = data.get('depth', 15)
        elo = data.get('elo', 3000)
        
        # Проверяем, запущен ли движок. Если нет или он упал — запускаем заново.
        if not hasattr(self.server, 'sf') or self.server.sf.poll() is not None:
            self.start_stockfish()
        
        sf = self.server.sf
        
        # 1. УСТАНАВЛИВАЕМ УРОВЕНЬ СЛОЖНОСТИ (Ключевое исправление!)
        sf.stdin.write("setoption name UCI_LimitStrength value true\n")
        sf.stdin.write(f"setoption name UCI_Elo value {elo}\n")
        
        # 2. Передаем текущую позицию
        sf.stdin.write(f"position fen {fen}\n")
        
        # 3. Запускаем расчет. 
        # Используем И глубину, И время, чтобы бот не зависал навечно на высоких настройках.
        sf.stdin.write(f"go depth {depth} movetime 3000\n")
        sf.stdin.flush()
        
        # 4. Читаем ответ от движка
        best_move = "a1a1" # Запасной ход на случай сбоя
        while True:
            line = sf.stdout.readline()
            if line.startswith("bestmove"):
                best_move = line.split()[1]
                break
                
        # 5. Отправляем ответ обратно в браузер
        response = json.dumps({"move": best_move})
        self.wfile.write(response.encode('utf-8'))

    def start_stockfish(self):
        print("  🔄 Запуск движка Stockfish...")
        # CREATE_NO_WINDOW скрывает консольное окно самого stockfish.exe
        self.server.sf = subprocess.Popen(
            ['stockfish.exe'], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            text=True, 
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Инициализация UCI протокола
        self.server.sf.stdin.write("uci\n")
        self.server.sf.stdin.write("isready\n")
        self.server.sf.stdin.flush()
        
        # Ждем, пока движок скажет, что готов
        while True:
            line = self.server.sf.stdout.readline()
            if "readyok" in line:
                print("  ✅ Движок готов к игре!")
                break

    def log_message(self, format, *args):
        pass # Отключаем спам логами HTTP-запросов в консоль

if __name__ == '__main__':
    print("=" * 50)
    print("  ♚ Шахматный мост (Bridge) запущен!")
    print("  Не закрывайте это окно во время игры.")
    print("  Для корректного закрытия используйте stop.bat")
    print("=" * 50)
    
    server = HTTPServer(('localhost', 8080), ChessHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Остановка моста...")
        if hasattr(server, 'sf') and server.sf.poll() is None:
            server.sf.terminate()
        server.server_close()
        print("✅ Все процессы завершены.")
