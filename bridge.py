import subprocess
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class ChessHandler(BaseHTTPRequestHandler):
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
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        fen = data.get('fen', 'startpos')
        depth = data.get('depth', 15)
        elo = data.get('elo', 3000)
        movetime = data.get('movetime', 1000) # <-- Теперь время приходит из HTML!
        
        if not hasattr(self.server, 'sf') or self.server.sf.poll() is not None:
            self.start_stockfish()
        
        sf = self.server.sf
        
        # Устанавливаем силу и лимит времени
        sf.stdin.write("setoption name UCI_LimitStrength value true\n")
        sf.stdin.write(f"setoption name UCI_Elo value {elo}\n")
        sf.stdin.write(f"position fen {fen}\n")
        sf.stdin.write(f"go depth {depth} movetime {movetime}\n") # <-- Используем переданное время
        sf.stdin.flush()
        
        best_move = "a1a1"
        while True:
            line = sf.stdout.readline()
            if line.startswith("bestmove"):
                best_move = line.split()[1]
                break
                
        response = json.dumps({"move": best_move})
        self.wfile.write(response.encode('utf-8'))

    def start_stockfish(self):
        print("  🔄 Запуск движка Stockfish...")
        self.server.sf = subprocess.Popen(
            ['stockfish.exe'], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            text=True, 
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        self.server.sf.stdin.write("uci\nisready\n")
        self.server.sf.stdin.flush()
        
        while True:
            line = self.server.sf.stdout.readline()
            if "readyok" in line:
                print("  ✅ Движок готов к игре!")
                break

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    print("=" * 50)
    print("  ♚ Шахматный мост (Bridge) запущен!")
    print("  Не закрывайте это окно во время игры.")
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
