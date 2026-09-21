import os

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Debug mode chỉ bật khi khai báo rõ qua biến môi trường (VD: chạy thử
    # cục bộ `set FLASK_DEBUG=1` trước khi chạy) - không hardcode True để
    # tránh vô tình bật Werkzeug interactive debugger (rủi ro bảo mật) khi
    # chạy trong môi trường không phải máy phát triển cá nhân.
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug)
