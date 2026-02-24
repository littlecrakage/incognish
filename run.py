import webbrowser
import threading
from app import create_app

app = create_app()

def open_browser():
    webbrowser.open("http://localhost:5000")

if __name__ == "__main__":
    # Open browser after a short delay to let Flask start
    timer = threading.Timer(1.2, open_browser)
    timer.start()
    print("Starting Incognish...")
    print("Opening http://localhost:5000")
    print("Press Ctrl+C to stop.\n")
    app.run(debug=False, threaded=True, port=5000)
